# Fichier : db.py (Version Finale Complète)

import click
from datetime import date, datetime
from flask.cli import with_appcontext
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (Integer, String, Float, Boolean, Date, DateTime, Text,
                        ForeignKey)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# --- CONFIGURATION DE BASE DE SQLAlchemy ---
class Base(DeclarativeBase):
    pass
db = SQLAlchemy(model_class=Base)

# -----------------------------------------------------------------------------
# DÉFINITION DES MODÈLES
# -----------------------------------------------------------------------------

class Etablissement(db.Model):
    __tablename__ = 'etablissements'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String, nullable=False)
    ville: Mapped[str] = mapped_column(String, nullable=True)

class Utilisateur(db.Model):
    __tablename__ = 'utilisateurs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom_utilisateur: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    mot_de_passe: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default='utilisateur')
    email: Mapped[str] = mapped_column(String, nullable=True)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class Armoire(db.Model):
    __tablename__ = 'armoires'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String, nullable=False)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class Budget(db.Model):
    __tablename__ = 'budgets'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    annee: Mapped[int] = mapped_column(Integer, nullable=False)
    montant_initial: Mapped[float] = mapped_column(Float, nullable=False)
    cloture: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class Categorie(db.Model):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String, nullable=False)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class Fournisseur(db.Model):
    __tablename__ = 'fournisseurs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String, nullable=False)
    site_web: Mapped[str] = mapped_column(String, nullable=True)
    logo: Mapped[str] = mapped_column(String, nullable=True) # Note: Ce sera une URL maintenant
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class Depense(db.Model):
    __tablename__ = 'depenses'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    budget_id: Mapped[int] = mapped_column(Integer, ForeignKey('budgets.id'), nullable=False)
    fournisseur_id: Mapped[int] = mapped_column(Integer, ForeignKey('fournisseurs.id'), nullable=True)
    contenu: Mapped[str] = mapped_column(Text, nullable=False)
    montant: Mapped[float] = mapped_column(Float, nullable=False)
    date_depense: Mapped[date] = mapped_column(Date, nullable=False)
    est_bon_achat: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class Echeance(db.Model):
    __tablename__ = 'echeances'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    intitule: Mapped[str] = mapped_column(Text, nullable=False)
    date_echeance: Mapped[date] = mapped_column(Date, nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=True)
    traite: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class Kit(db.Model):
    __tablename__ = 'kits'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class Objet(db.Model):
    __tablename__ = 'objets'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String, nullable=False)
    quantite_physique: Mapped[int] = mapped_column(Integer, nullable=False)
    seuil: Mapped[int] = mapped_column(Integer, nullable=False)
    armoire_id: Mapped[int] = mapped_column(Integer, ForeignKey('armoires.id'), nullable=False)
    categorie_id: Mapped[int] = mapped_column(Integer, ForeignKey('categories.id'), nullable=False)
    en_commande: Mapped[int] = mapped_column(Integer, default=0)
    date_peremption: Mapped[str] = mapped_column(String, nullable=True)
    traite: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    fds_url: Mapped[str] = mapped_column(String, nullable=True)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class Historique(db.Model):
    __tablename__ = 'historique'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objet_id: Mapped[int] = mapped_column(Integer, ForeignKey('objets.id', ondelete='CASCADE'), nullable=False)
    utilisateur_id: Mapped[int] = mapped_column(Integer, ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class KitObjet(db.Model):
    __tablename__ = 'kit_objets'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kit_id: Mapped[int] = mapped_column(Integer, ForeignKey('kits.id', ondelete='CASCADE'), nullable=False)
    objet_id: Mapped[int] = mapped_column(Integer, ForeignKey('objets.id', ondelete='CASCADE'), nullable=False)
    quantite: Mapped[int] = mapped_column(Integer, nullable=False)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class Parametre(db.Model):
    __tablename__ = 'parametres'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) # Ajout d'un ID pour la clé primaire
    cle: Mapped[str] = mapped_column(String, nullable=False)
    valeur: Mapped[str] = mapped_column(String, nullable=True)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

class Reservation(db.Model):
    __tablename__ = 'reservations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objet_id: Mapped[int] = mapped_column(Integer, ForeignKey('objets.id'), nullable=False)
    utilisateur_id: Mapped[int] = mapped_column(Integer, ForeignKey('utilisateurs.id'), nullable=False)
    quantite_reservee: Mapped[int] = mapped_column(Integer, nullable=False)
    debut_reservation: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fin_reservation: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    groupe_id: Mapped[str] = mapped_column(String, nullable=True)
    kit_id: Mapped[int] = mapped_column(Integer, ForeignKey('kits.id'), nullable=True)
    etablissement_id: Mapped[int] = mapped_column(ForeignKey('etablissements.id'), nullable=False)

# --- FONCTIONS D'INITIALISATION ---
def init_app(app):
    db.init_app(app)
    app.cli.add_command(init_db_command)

def init_db():
    db.create_all()

@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Base de données initialisée avec le schéma final.')