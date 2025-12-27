import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from flask_login import UserMixin

db = SQLAlchemy()

def init_app(app):
    db.init_app(app)
    # La création des tables se fait via reset_db.py

# ============================================================
# 1. MODÈLES DE BASE (Etablissement & Utilisateur)
# ============================================================

class Etablissement(db.Model):
    __tablename__ = 'etablissements'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    code_invitation = db.Column(db.String(20), unique=True)
    
    # Relations complètes (Bidirectionnelles)
    utilisateurs = db.relationship('Utilisateur', backref='etablissement', lazy=True)
    objets = db.relationship('Objet', backref='etablissement', lazy=True)
    kits = db.relationship('Kit', backref='etablissement', lazy=True)
    armoires = db.relationship('Armoire', backref='etablissement', lazy=True)
    categories = db.relationship('Categorie', backref='etablissement', lazy=True)

class Utilisateur(UserMixin, db.Model):
    __tablename__ = 'utilisateurs'
    id = db.Column(db.Integer, primary_key=True)
    nom_utilisateur = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150))
    mot_de_passe = db.Column(db.String(255), nullable=False) # Hash bcrypt/scrypt
    role = db.Column(db.String(50), default='utilisateur')
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)

# ============================================================
# 2. GESTION DU MATÉRIEL (Objets & Kits)
# ============================================================

class Armoire(db.Model):
    __tablename__ = 'armoires'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    objets = db.relationship('Objet', back_populates='armoire')

class Categorie(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    objets = db.relationship('Objet', back_populates='categorie')

class Objet(db.Model):
    __tablename__ = 'objets'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    quantite_physique = db.Column(db.Integer, default=0)
    seuil = db.Column(db.Integer, default=0)
    date_peremption = db.Column(db.Date, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    fds_url = db.Column(db.String(255), nullable=True)
    
    # FK
    armoire_id = db.Column(db.Integer, db.ForeignKey('armoires.id'))
    categorie_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    
    # Relations
    armoire = db.relationship('Armoire', back_populates='objets')
    categorie = db.relationship('Categorie', back_populates='objets')
    
    # Champs de gestion
    en_commande = db.Column(db.Integer, default=0) 
    traite = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.Index('idx_objets_etablissement_categorie', 'etablissement_id', 'categorie_id'),
    )

class Kit(db.Model):
    __tablename__ = 'kits'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    
    # Relation vers la table de liaison
    objets_assoc = db.relationship("KitObjet", back_populates="kit", cascade="all, delete-orphan")

class KitObjet(db.Model):
    """Table de liaison Kit <-> Objet (kit_composants)"""
    __tablename__ = 'kit_composants'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Clés étrangères
    kit_id = db.Column(db.Integer, db.ForeignKey('kits.id', ondelete='CASCADE'), nullable=False)
    objet_id = db.Column(db.Integer, db.ForeignKey('objets.id', ondelete='RESTRICT'), nullable=False)
    
    # Données
    quantite = db.Column(db.Integer, nullable=False)
    date_creation = db.Column(db.DateTime(timezone=True), server_default=func.current_timestamp())
    
    # SaaS
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)

    # Relations
    kit = db.relationship("Kit", back_populates="objets_assoc")
    objet = db.relationship("Objet")

    __table_args__ = (
        db.UniqueConstraint('kit_id', 'objet_id', name='_kit_objet_uc'),
        db.CheckConstraint('quantite > 0', name='check_quantite_positive'),
        db.Index('idx_kit_composants_kit', 'kit_id'),
        db.Index('idx_kit_composants_objet', 'objet_id'),
    )

# ============================================================
# 3. SYSTÈME DE RÉSERVATION & PANIER (NOUVEAU)
# ============================================================

class Panier(db.Model):
    __tablename__ = 'paniers'
    
    # UUID stocké en String(36) pour compatibilité maximale (SQLite/Postgres)
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False)
    date_creation = db.Column(db.DateTime(timezone=True), server_default=func.current_timestamp())
    date_expiration = db.Column(db.DateTime(timezone=True), nullable=False)
    statut = db.Column(db.String(20), default='actif') # actif, validé, expiré
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)

    items = db.relationship("PanierItem", back_populates="panier", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.Index('idx_paniers_utilisateur', 'id_utilisateur'),
        db.Index('idx_paniers_expiration', 'date_expiration'),
    )

class PanierItem(db.Model):
    __tablename__ = 'panier_items'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_panier = db.Column(db.String(36), db.ForeignKey('paniers.id', ondelete='CASCADE'), nullable=False)
    
    type = db.Column(db.String(10), nullable=False) # 'objet' ou 'kit'
    id_item = db.Column(db.Integer, nullable=False) # ID de l'objet ou du kit
    quantite = db.Column(db.Integer, nullable=False)
    
    # Créneau
    date_reservation = db.Column(db.Date, nullable=False)
    heure_debut = db.Column(db.String(5), nullable=False)
    heure_fin = db.Column(db.String(5), nullable=False)
    
    date_ajout = db.Column(db.DateTime(timezone=True), server_default=func.current_timestamp())

    panier = db.relationship("Panier", back_populates="items")
    
    __table_args__ = (
        db.CheckConstraint('quantite > 0', name='check_panier_qte_positive'),
        db.Index('idx_panier_items_panier', 'id_panier'),
    )

class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    
    # Quoi (Objet OU Kit) - XOR Logic
    objet_id = db.Column(db.Integer, db.ForeignKey('objets.id'), nullable=True)
    kit_id = db.Column(db.Integer, db.ForeignKey('kits.id'), nullable=True)
    
    # Détails
    quantite_reservee = db.Column(db.Integer, nullable=False)
    debut_reservation = db.Column(db.DateTime, nullable=False)
    fin_reservation = db.Column(db.DateTime, nullable=False)
    
    # Groupement et Statut
    groupe_id = db.Column(db.String(36), nullable=False, index=True)
    statut = db.Column(db.String(20), default='confirmée') # en_attente, confirmée, annulée
    
    # Traçabilité
    date_creation = db.Column(db.DateTime(timezone=True), server_default=func.current_timestamp())
    date_modification = db.Column(db.DateTime(timezone=True), onupdate=func.current_timestamp())

    # Relations
    objet = db.relationship('Objet')
    kit = db.relationship('Kit')
    utilisateur = db.relationship('Utilisateur')

    __table_args__ = (
        # Contrainte XOR : Soit objet_id, soit kit_id, mais pas les deux (ni aucun)
        db.CheckConstraint(
            '(objet_id IS NOT NULL AND kit_id IS NULL) OR (objet_id IS NULL AND kit_id IS NOT NULL)',
            name='check_objet_ou_kit'
        ),
        db.Index('idx_reservations_groupe', 'groupe_id'),
        db.Index('idx_reservations_statut', 'statut'),
        db.Index('idx_reservations_dates', 'debut_reservation', 'fin_reservation'),
        db.Index('idx_reservations_etablissement_statut', 'etablissement_id', 'statut'),
    )

# ============================================================
# 4. AUDIT & LOGS
# ============================================================

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.current_timestamp())
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id', ondelete='SET NULL'), nullable=True)
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    
    action = db.Column(db.String(50), nullable=False)
    table_cible = db.Column(db.String(50), nullable=False)
    id_enregistrement = db.Column(db.String(50), nullable=True)
    
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    utilisateur = db.relationship("Utilisateur")

    __table_args__ = (
        db.Index('idx_audit_timestamp', 'timestamp'),
        db.Index('idx_audit_utilisateur', 'id_utilisateur'),
    )

class Historique(db.Model):
    """
    DEPRECATED: Utilisez AuditLog pour les nouveaux enregistrements.
    Cette table est conservée pour les données historiques existantes.
    """
    __tablename__ = 'historique'
    id = db.Column(db.Integer, primary_key=True)
    objet_id = db.Column(db.Integer, nullable=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.now)
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    utilisateur = db.relationship('Utilisateur')

# ============================================================
# 5. AUTRES (Budget, Paramètres...)
# ============================================================

class Parametre(db.Model):
    __tablename__ = 'parametres'
    id = db.Column(db.Integer, primary_key=True)
    cle = db.Column(db.String(50), nullable=False)
    valeur = db.Column(db.Text, nullable=False)
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)

class Budget(db.Model):
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True)
    annee = db.Column(db.Integer, nullable=False)
    montant_initial = db.Column(db.Float, default=0.0)
    cloture = db.Column(db.Boolean, default=False)
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    depenses = db.relationship('Depense', backref='budget', lazy=True, cascade="all, delete-orphan")

class Depense(db.Model):
    __tablename__ = 'depenses'
    id = db.Column(db.Integer, primary_key=True)
    date_depense = db.Column(db.Date, nullable=False)
    contenu = db.Column(db.String(200))
    montant = db.Column(db.Float, nullable=False)
    est_bon_achat = db.Column(db.Boolean, default=False)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), nullable=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id'), nullable=False)
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    fournisseur = db.relationship('Fournisseur', back_populates='depenses')

class Fournisseur(db.Model):
    __tablename__ = 'fournisseurs'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    site_web = db.Column(db.String(255))
    logo = db.Column(db.String(255))
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    depenses = db.relationship('Depense', back_populates='fournisseur')

class Echeance(db.Model):
    __tablename__ = 'echeances'
    id = db.Column(db.Integer, primary_key=True)
    intitule = db.Column(db.String(100), nullable=False)
    date_echeance = db.Column(db.Date, nullable=False)
    details = db.Column(db.Text)
    traite = db.Column(db.Integer, default=0)
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)

class Suggestion(db.Model):
    __tablename__ = 'suggestions'
    id = db.Column(db.Integer, primary_key=True)
    objet_id = db.Column(db.Integer, db.ForeignKey('objets.id'), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    quantite = db.Column(db.Integer, default=1)
    commentaire = db.Column(db.Text)
    date_demande = db.Column(db.DateTime, default=datetime.now)
    statut = db.Column(db.String(20), default='En attente')
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    objet = db.relationship('Objet')
    utilisateur = db.relationship('Utilisateur')