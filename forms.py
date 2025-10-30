from flask_wtf import FlaskForm
from wtforms import IntegerField, FloatField, DateField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional

class BudgetForm(FlaskForm):
    """Formulaire pour créer ou modifier un budget annuel."""
    annee = IntegerField(
        "Année de début de l'année scolaire", 
        validators=[DataRequired(message="L'année est requise."), NumberRange(min=2020, max=2100)]
    )
    montant_initial = FloatField(
        'Montant initial (€)', 
        validators=[DataRequired(message="Le montant est requis."), NumberRange(min=0)]
    )
    submit = SubmitField('Enregistrer')

class DepenseForm(FlaskForm):
    """Formulaire pour ajouter ou modifier une dépense."""
    date_depense = DateField(
        'Date de la dépense', 
        validators=[DataRequired(message="La date est requise.")], 
        format='%Y-%m-%d'
    )
    fournisseur_id = SelectField(
        'Fournisseur', 
        coerce=int, 
        validators=[Optional()]
    )
    est_bon_achat = BooleanField("Bon d'achat petit matériel (sans fournisseur)")
    contenu = TextAreaField(
        'Contenu / Libellé', 
        validators=[DataRequired(message="Le contenu est requis.")]
    )
    montant = FloatField(
        'Montant (€)', 
        validators=[DataRequired(message="Le montant est requis."), NumberRange(min=0.01)]
    )
    submit = SubmitField('Ajouter')