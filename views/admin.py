# ============================================================
# FICHIER : views/admin.py (VERSION FINALE & COMPLÈTE)
# ============================================================
import json
import hashlib
import secrets
import re
import logging
import io
import os
import imghdr
from io import BytesIO
from urllib.parse import urlparse
from html import escape
from datetime import date, datetime, timedelta
from collections import defaultdict
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, jsonify, send_file, current_app, abort, make_response)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

# --- IMPORTS POUR EXPORT PDF (ReportLab) ---
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Flowable, Image as ReportLabImage
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.graphics.shapes import Drawing, Rect, Line
from reportlab.graphics import renderPDF

# --- IMPORTS POUR EXPORT EXCEL (OpenPyXL) ---
import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.drawing.image import Image as OpenPyXLImage
from openpyxl.worksheet.datavalidation import DataValidation

# Imports Locaux
from extensions import limiter, cache
from db import db, Utilisateur, Parametre, Objet, Armoire, Categorie, Fournisseur, Kit, KitObjet, Budget, Depense, Echeance, Historique, Etablissement, Reservation, Suggestion
from utils import calculate_license_key, admin_required, login_required, log_action, get_etablissement_params, allowed_file

from services.security_service import SecurityService

# ============================================================
# CONFIGURATION
# ============================================================
admin_bp = Blueprint('admin', __name__, template_folder='../templates', url_prefix='/admin')

MAX_EXPORT_LIMIT = 3000
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10 Mo
PASSWORD_MIN_LENGTH = 12
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
MAX_IMPORT_ROWS = 5000
MAX_JSON_SIZE = 5 * 1024 * 1024

# ============================================================
# UTILITAIRES DE SÉCURITÉ
# ============================================================
def hash_user_id(user_id):
    return hashlib.sha256(str(user_id).encode()).hexdigest()[:8]

def validate_email(email):
    return re.match(EMAIL_REGEX, email) is not None

def validate_password_strength(password):
    if len(password) < PASSWORD_MIN_LENGTH: return False, f"Min {PASSWORD_MIN_LENGTH} caractères."
    if not re.search(r"[a-z]", password): return False, "Min 1 minuscule."
    if not re.search(r"[A-Z]", password): return False, "Min 1 majuscule."
    if not re.search(r"[0-9]", password): return False, "Min 1 chiffre."
    if not re.search(r"[^a-zA-Z0-9]", password): return False, "Min 1 caractère spécial."
    return True, ""

def validate_url(url):
    if not url: return True
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except ValueError: return False

def sanitize_for_excel(value):
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@')): return f"'{value}"
    return value

def generer_code_unique():
    for _ in range(100):
        code = f"LABFLOW-{secrets.token_hex(3).upper()}"
        nested = db.session.begin_nested()
        try:
            test_etab = Etablissement(nom="__TEST__", code_invitation=code)
            db.session.add(test_etab)
            db.session.flush()
            nested.rollback()
            return code
        except IntegrityError:
            nested.rollback()
            continue
    raise RuntimeError("Impossible de générer un code unique")

def json_serial(obj):
    if isinstance(obj, (datetime, date)): return obj.isoformat()
    raise TypeError(f"Type {type(obj)} non sérialisable")

def sanitize_filename(name):
    safe = re.sub(r'[^\w\s-]', '', str(name))
    cleaned = secure_filename(safe)
    return cleaned[:100] if cleaned else "Export"

def sanitize_filename_report(text):
    if not text: return "Rapport"
    return re.sub(r'[^\w\s-]', '', str(text)).strip().replace(' ', '_')

def sanitize_for_excel_report(text):
    if not text: return ""
    text = str(text)
    if text.startswith(('=', '+', '-', '@')): text = "'" + text
    return text

# ============================================================
# GÉNÉRATEURS PDF / EXCEL
# ============================================================

class LogoGraphique(Flowable):
    def __init__(self, width=40, height=40):
        Flowable.__init__(self)
        self.width = width
        self.height = height
    def draw(self):
        self.canv.setFillColor(colors.HexColor('#1F3B73'))
        self.canv.rect(0, 0, 8, 15, fill=1, stroke=0)
        self.canv.rect(12, 0, 8, 25, fill=1, stroke=0)
        self.canv.setFillColor(colors.HexColor('#4facfe'))
        self.canv.rect(24, 0, 8, 35, fill=1, stroke=0)
        self.canv.setStrokeColor(colors.HexColor('#FFD700'))
        self.canv.setLineWidth(2)
        self.canv.line(-5, 5, 35, 40)

def ajouter_logo_excel(ws):
    """Ajoute le logo LabFlow dans le fichier Excel si disponible."""
    logo_path = os.path.join(current_app.root_path, 'static', 'logo.png')
    if os.path.exists(logo_path):
        try:
            img = OpenPyXLImage(logo_path)
            img.width = 50
            img.height = 50
            ws.add_image(img, 'A1')
            return True
        except Exception:
            return False
    return False

def generer_budget_pdf_pro(data_export, metadata):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm, title=f"Budget {metadata['etablissement']}")
    elements = []
    styles = getSampleStyleSheet()
    LABFLOW_BLUE = colors.HexColor('#1F3B73')
    style_titre = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=22, textColor=LABFLOW_BLUE, alignment=TA_CENTER)
    style_normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10)
    style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9)
    elements.append(Paragraph(metadata['etablissement'], style_titre))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"Rapport du {metadata['date_debut']} au {metadata['date_fin']}", style_normal))
    elements.append(Spacer(1, 0.5*cm))
    table_data = [['Date', 'Fournisseur', 'Libellé', 'Montant']]
    for item in data_export:
        table_data.append([Paragraph(item['date'], style_cell), Paragraph(escape(item['fournisseur']), style_cell), Paragraph(escape(item['contenu']), style_cell), Paragraph(f"{item['montant']:.2f} €", style_cell)])
    table_data.append(['', '', 'TOTAL', f"{metadata['total']:.2f} €"])
    t = Table(table_data, colWidths=[2.5*cm, 5*cm, 8*cm, 3*cm])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), LABFLOW_BLUE), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.whitesmoke])]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    filename = f"Budget_{sanitize_filename(metadata['etablissement'])}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

def generer_budget_excel_pro(data_export, metadata):
    wb = Workbook()
    ws = wb.active
    ws.title = "Budget"
    
    COLOR_PRIMARY = "1F3B73"
    fill_header = PatternFill(start_color=COLOR_PRIMARY, end_color=COLOR_PRIMARY, fill_type="solid")
    font_header = Font(name='Segoe UI', size=11, bold=True, color="FFFFFF")
    
    font_titre = Font(name='Segoe UI', size=16, bold=True, color=COLOR_PRIMARY)
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    align_right = Alignment(horizontal="right", vertical="center")
    font_data = Font(name='Segoe UI', size=10)
    border_thin = Border(left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9'))

    ws.merge_cells('B1:E1')
    ws['B1'] = f"Rapport Budgétaire - {metadata['etablissement']}"
    ws['B1'].font = font_titre
    ws['B1'].alignment = align_left
    ws.row_dimensions[1].height = 40
    
    ajouter_logo_excel(ws)

    ws.merge_cells('A2:D2')
    ws['A2'] = f"Période : {metadata['date_debut']} au {metadata['date_fin']}"
    ws['A2'].alignment = align_left
    ws.merge_cells('A3:D3')
    ws['A3'] = f"Généré le {metadata['date_generation']} | {metadata['nombre_depenses']} écritures"
    ws['A3'].alignment = align_left
    ws.row_dimensions[3].height = 20

    headers = ['Date', 'Fournisseur', 'Libellé', 'Montant']
    ws.append([]) 
    ws.append(headers) 
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_num)
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = align_center
        cell.border = border_thin
    
    ws.row_dimensions[5].height = 25

    current_row = 6
    for item in data_export:
        ws.cell(row=current_row, column=1, value=item['date']).alignment = align_center
        ws.cell(row=current_row, column=2, value=item['fournisseur'])
        ws.cell(row=current_row, column=3, value=item['contenu'])
        c4 = ws.cell(row=current_row, column=4, value=item['montant'])
        c4.number_format = '#,##0.00 €'
        c4.alignment = align_right
        
        for col in range(1, 5):
            ws.cell(row=current_row, column=col).border = border_thin
            ws.cell(row=current_row, column=col).font = font_data
        current_row += 1

    ws.cell(row=current_row, column=3, value="TOTAL").font = Font(bold=True)
    ws.cell(row=current_row, column=3).alignment = align_right
    c_total = ws.cell(row=current_row, column=4, value=metadata['total'])
    c_total.font = Font(bold=True, color=COLOR_PRIMARY, size=12)
    c_total.number_format = '#,##0.00 €'

    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 50
    ws.column_dimensions['D'].width = 15

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"Budget_{sanitize_filename(metadata['etablissement'])}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

def generer_rapport_pdf(data, metadata):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1.0*cm, leftMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm, title=f"Rapport - {metadata['etablissement']}")
    elements = []
    styles = getSampleStyleSheet()
    logo = LogoGraphique(width=40, height=40)
    titre_style = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#1F3B73'), alignment=TA_LEFT)
    sous_titre_style = ParagraphStyle('SousTitre', parent=styles['Normal'], fontSize=12, textColor=colors.gray, alignment=TA_LEFT)
    titre_bloc = [Paragraph(f"RAPPORT D'ACTIVITÉ", titre_style), Paragraph(f"{escape(metadata['etablissement'])}", sous_titre_style)]
    header_table = Table([[logo, titre_bloc]], colWidths=[1.5*cm, 20*cm])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 0)]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=10, textColor=colors.black)
    meta_label = ParagraphStyle('MetaLabel', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#1F3B73'), fontName='Helvetica-Bold')
    meta_data = [[Paragraph('Période :', meta_label), Paragraph(metadata['periode'], meta_style), Paragraph('Généré le :', meta_label), Paragraph(metadata['date_generation'], meta_style)], [Paragraph('Total :', meta_label), Paragraph(f"{metadata['total']} entrées", meta_style), '', '']]
    meta_table = Table(meta_data, colWidths=[2.5*cm, 8*cm, 2.5*cm, 8*cm])
    meta_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')), ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')), ('PADDING', (0,0), (-1,-1), 6), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.8*cm))
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9, textColor=colors.black)
    headers = [Paragraph('Date', header_style), Paragraph('Heure', header_style), Paragraph('Utilisateur', header_style), Paragraph('Action', header_style), Paragraph('Objet', header_style), Paragraph('Détails', header_style)]
    table_data = [headers]
    for row in data:
        table_data.append([Paragraph(row['date'], cell_style), Paragraph(row['heure'], cell_style), Paragraph(escape(row['utilisateur']), cell_style), Paragraph(escape(row['action']), cell_style), Paragraph(escape(row['objet']), cell_style), Paragraph(escape(row['details']) if row['details'] else '-', cell_style)])
    col_widths = [2.5*cm, 1.5*cm, 4.0*cm, 3.0*cm, 6.5*cm, 10.0*cm]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F3B73')), ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, 0), 10), ('BOTTOMPADDING', (0, 0), (-1, 0), 10), ('VALIGN', (0, 1), (-1, -1), 'TOP'), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F4F6F9')]), ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')), ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1F3B73'))]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    filename = f"Rapport_{sanitize_filename_report(metadata['etablissement'])}_{date.today().strftime('%Y%m%d')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

def generer_rapport_excel(data, metadata):
    wb = Workbook()
    ws = wb.active
    ws.title = "Activité"
    
    COLOR_PRIMARY = "1F3B73"
    fill_header = PatternFill(start_color="1F3B73", end_color="1F3B73", fill_type="solid")
    font_header = Font(name='Segoe UI', size=11, bold=True, color="FFFFFF")
    
    font_titre = Font(name='Segoe UI', size=18, bold=True, color=COLOR_PRIMARY)
    align_center = Alignment(horizontal="center", vertical="center")
    font_data = Font(name='Segoe UI', size=10)
    align_top = Alignment(vertical="top", wrap_text=True)
    border_thin = Border(left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9'))

    ws.merge_cells('B1:F1')
    ws['B1'] = f"RAPPORT D'ACTIVITÉ - {metadata['etablissement']}"
    ws['B1'].font = font_titre
    ws['B1'].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 45
    
    ajouter_logo_excel(ws)
    
    ws.merge_cells('A2:F4')
    ws['A2'] = f"Période : {metadata['periode']}\nGénéré le : {metadata['date_generation']}\nTotal : {metadata['total']} enregistrements"
    ws['A2'].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    
    headers = ["Date", "Heure", "Utilisateur", "Action", "Objet", "Détails"]
    ws.append([])
    ws.append(headers)
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=6, column=col_num)
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = align_center
    
    ws.row_dimensions[6].height = 30
    
    for row in data:
        ws.append([
            row['date'], row['heure'], 
            sanitize_for_excel_report(row['utilisateur']), 
            sanitize_for_excel_report(row['action']), 
            sanitize_for_excel_report(row['objet']), 
            sanitize_for_excel_report(row['details'])
        ])
    
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 10
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 30
    ws.column_dimensions['F'].width = 50
    
    for row in ws.iter_rows(min_row=7, max_row=ws.max_row):
        for cell in row:
            cell.font = font_data
            cell.alignment = align_top
            cell.border = border_thin

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"Rapport_{sanitize_filename_report(metadata['etablissement'])}_{date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

def generer_inventaire_pdf(data, metadata):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1.0*cm, leftMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm, title=f"Inventaire - {metadata['etablissement']}")
    elements = []
    styles = getSampleStyleSheet()
    logo = LogoGraphique(width=40, height=40)
    titre_style = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#1F3B73'), alignment=TA_LEFT)
    sous_titre_style = ParagraphStyle('SousTitre', parent=styles['Normal'], fontSize=12, textColor=colors.gray, alignment=TA_LEFT)
    titre_bloc = [Paragraph(f"ÉTAT DE L'INVENTAIRE", titre_style), Paragraph(f"{escape(metadata['etablissement'])}", sous_titre_style)]
    header_table = Table([[logo, titre_bloc]], colWidths=[1.5*cm, 20*cm])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))
    info_text = f"<b>Généré le :</b> {metadata['date_generation']}  |  <b>Total références :</b> {metadata['total']}"
    elements.append(Paragraph(info_text, ParagraphStyle('Info', parent=styles['Normal'], fontSize=10, alignment=TA_RIGHT, textColor=colors.HexColor('#1F3B73'))))
    elements.append(Spacer(1, 0.3*cm))
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9, textColor=colors.black)
    cell_center = ParagraphStyle('CellCenter', parent=cell_style, alignment=TA_CENTER)
    headers = [Paragraph('Catégorie', header_style), Paragraph('Désignation', header_style), Paragraph('Qté', header_style), Paragraph('Seuil', header_style), Paragraph('Emplacement', header_style), Paragraph('Péremption', header_style)]
    table_data = [headers]
    for row in data:
        qty_style = cell_center
        if row['quantite'] <= row['seuil']: qty_style = ParagraphStyle('Alert', parent=cell_center, textColor=colors.red, fontName='Helvetica-Bold')
        table_data.append([Paragraph(escape(row['categorie']), cell_style), Paragraph(escape(row['nom']), cell_style), Paragraph(str(row['quantite']), qty_style), Paragraph(str(row['seuil']), cell_center), Paragraph(escape(row['armoire']), cell_style), Paragraph(row['peremption'], cell_center)])
    col_widths = [5.0*cm, 9.5*cm, 2.0*cm, 2.0*cm, 5.0*cm, 4.0*cm]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F3B73')), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, 0), 8), ('BOTTOMPADDING', (0, 0), (-1, 0), 8), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F4F6F9')]), ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')), ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1F3B73'))]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    filename = f"Inventaire_{sanitize_filename_report(metadata['etablissement'])}_{date.today().strftime('%Y%m%d')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

def generer_inventaire_excel(data, metadata):
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventaire"
    font_titre = Font(name='Segoe UI', size=16, bold=True, color="1F3B73")
    fill_header = PatternFill(start_color="1F3B73", end_color="1F3B73", fill_type="solid")
    font_header = Font(name='Segoe UI', size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")
    border_thin = Border(left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9'))
    font_alert = Font(color="DC3545", bold=True)
    
    ws.merge_cells('B1:F1')
    ws['B1'] = f"📦 ÉTAT DE L'INVENTAIRE - {metadata['etablissement']}"
    ws['B1'].font = font_titre
    ws['B1'].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 35
    
    ajouter_logo_excel(ws)
    
    ws['A2'] = f"Généré le : {metadata['date_generation']}"
    ws['A2'].font = Font(italic=True, color="666666")
    
    headers = ["Catégorie", "Désignation", "Quantité", "Seuil", "Emplacement", "Péremption"]
    ws.append([])
    ws.append(headers)
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num)
        cell.value = header
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = align_center
    
    ws.row_dimensions[4].height = 30
    
    for row in data:
        ws.append([
            row['categorie'], row['nom'], row['quantite'], 
            row['seuil'], row['armoire'], row['peremption']
        ])
        
        current_row = ws.max_row
        for col in range(1, 7):
            cell = ws.cell(row=current_row, column=col)
            cell.border = border_thin
            cell.alignment = Alignment(vertical="center")
            if col in [3, 4, 6]: cell.alignment = align_center
            
        if row['quantite'] <= row['seuil']:
            ws.cell(row=current_row, column=3).font = font_alert

    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 40
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 25
    ws.column_dimensions['F'].width = 15
    
    ws.auto_filter.ref = f"A4:F{ws.max_row}"
    ws.freeze_panes = "A5"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"Inventaire_{sanitize_filename_report(metadata['etablissement'])}_{date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ============================================================
# ROUTE PRINCIPALE
# ============================================================
@admin_bp.route("/")
@admin_required
def admin():
    etablissement_id = session.get('etablissement_id')
    etablissement = db.session.get(Etablissement, etablissement_id)
    
    if not etablissement:
        admin_hash = hash_user_id(session.get('user_id'))
        current_app.logger.critical(f"Admin access attempt invalid etab by admin_{admin_hash}")
        flash("Erreur critique : Établissement introuvable.", "error")
        return redirect(url_for('auth.login'))

    if not etablissement.code_invitation:
        try:
            etablissement.code_invitation = generer_code_unique()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error("Erreur génération code invitation", exc_info=True)

    params = get_etablissement_params(etablissement_id)
    
    licence_info = {
        'is_pro': params.get('licence_statut') == 'PRO',
        'instance_id': params.get('instance_id', 'N/A'),
        'statut': params.get('licence_statut', 'FREE')
    }

    # --- RECUPERATION STATS SÉCURITÉ ---
    try:
        sec_service = SecurityService()
        securite_stats = sec_service.get_dashboard_stats(etablissement_id)
    except Exception as e:
        current_app.logger.error(f"Erreur chargement stats sécurité admin: {str(e)}")
        securite_stats = None
    # -----------------------------------

    return render_template("admin.html", 
                           now=datetime.now(), 
                           licence=licence_info, 
                           etablissement=etablissement,
                           securite_stats=securite_stats)

# ============================================================
# GESTION ARMOIRES / CATÉGORIES
# ============================================================
@admin_bp.route("/ajouter", methods=["POST"])
@admin_required
@limiter.limit("30 per minute") # Rate limit ajouté
def ajouter():
    etablissement_id = session['etablissement_id']
    type_objet = request.form.get("type")
    nom = request.form.get("nom", "").strip()
    
    if not nom:
        flash("Le nom ne peut pas être vide.", "error")
        return redirect(request.referrer)

    Model = Armoire if type_objet == "armoire" else Categorie
    
    try:
        nouvel_element = Model(nom=nom, etablissement_id=etablissement_id)
        db.session.add(nouvel_element)
        db.session.commit()
        flash(f"L'élément '{nom}' a été créé.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(f"L'élément '{nom}' existe déjà.", "error")
    except Exception:
        db.session.rollback()
        current_app.logger.error(f"Erreur ajout {type_objet}", exc_info=True) # Log sécurisé
        flash("Erreur technique.", "error")
    
    redirect_to = "main.gestion_armoires" if type_objet == "armoire" else "main.gestion_categories"
    return redirect(url_for(redirect_to))

@admin_bp.route("/supprimer/<type_objet>/<int:id>", methods=["POST"])
@admin_required
@limiter.limit("20 per minute")
def supprimer(type_objet, id):
    etablissement_id = session['etablissement_id']
    
    if type_objet == "armoire":
        Model = Armoire
        redirect_to = "main.gestion_armoires"
    elif type_objet == "categorie":
        Model = Categorie
        redirect_to = "main.gestion_categories"
    else:
        abort(400)

    element = db.session.get(Model, id)

    if not element or element.etablissement_id != etablissement_id:
        admin_hash = hash_user_id(session.get('user_id'))
        current_app.logger.warning(f"IDOR SUSPECT: AdminHash {admin_hash} delete {type_objet} {id}")
        abort(403)

    if type_objet == "armoire":
        count = db.session.query(Objet).filter_by(armoire_id=id, etablissement_id=etablissement_id).count()
    else:
        count = db.session.query(Objet).filter_by(categorie_id=id, etablissement_id=etablissement_id).count()
        
    if count > 0:
        flash(f"Impossible de supprimer '{element.nom}' car il contient encore {count} objet(s).", "error")
        return redirect(url_for(redirect_to))

    try:
        nom_element = element.nom
        db.session.delete(element)
        db.session.commit()
        flash(f"L'élément '{nom_element}' a été supprimé.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.error(f"Erreur suppression {type_objet}", exc_info=True)
        flash("Erreur technique.", "error")
    
    return redirect(url_for(redirect_to))

def _modifier_element_generique(model_class, request_data):
    """Helper pour modifier Armoire ou Categorie sans duplication."""
    try:
        etablissement_id = session['etablissement_id']
        element_id = request_data.get("id")
        nouveau_nom = request_data.get("nom", "").strip()

        if not all([element_id, nouveau_nom]): 
            return jsonify(success=False, error="Données invalides"), 400

        element = db.session.get(model_class, element_id)
        if not element or element.etablissement_id != etablissement_id:
            return jsonify(success=False, error="Élément introuvable"), 404

        element.nom = nouveau_nom
        db.session.commit()
        return jsonify(success=True, nouveau_nom=nouveau_nom)
    
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, error="Ce nom existe déjà"), 409
    except Exception:
        db.session.rollback()
        current_app.logger.error(f"Erreur modif {model_class.__name__}", exc_info=True)
        return jsonify(success=False, error="Erreur serveur"), 500

@admin_bp.route("/modifier_armoire", methods=["POST"])
@admin_required
def modifier_armoire():
    return _modifier_element_generique(Armoire, request.get_json())

@admin_bp.route("/modifier_categorie", methods=["POST"])
@admin_required
def modifier_categorie():
    return _modifier_element_generique(Categorie, request.get_json())

# ============================================================
# GESTION UTILISATEURS (DURCIE)
# ============================================================
@admin_bp.route("/utilisateurs")
@admin_required
def gestion_utilisateurs():
    etablissement_id = session['etablissement_id']
    utilisateurs = db.session.execute(
        db.select(Utilisateur)
        .filter_by(etablissement_id=etablissement_id)
        .order_by(Utilisateur.nom_utilisateur)
        .limit(100)
    ).scalars().all()

    breadcrumbs = [{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Utilisateurs'}]
    return render_template("admin_utilisateurs.html", utilisateurs=utilisateurs, breadcrumbs=breadcrumbs, now=datetime.now)

@admin_bp.route("/utilisateurs/ajouter", methods=["POST"])
@admin_required
@limiter.limit("5 per minute") # Rate Limit Strict
def ajouter_utilisateur():
    etablissement_id = session['etablissement_id']
    nom_utilisateur = request.form.get('nom_utilisateur', '').strip()
    email = request.form.get('email', '').strip()
    mot_de_passe = request.form.get('mot_de_passe', '').strip()
    est_admin = 'est_admin' in request.form

    if not nom_utilisateur or not mot_de_passe:
        flash("Champs obligatoires manquants.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))
    
    if email and not validate_email(email):
        flash("Format d'email invalide.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))

    is_valid, error_msg = validate_password_strength(mot_de_passe)
    if not is_valid:
        flash(error_msg, "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        nouvel_utilisateur = Utilisateur(
            nom_utilisateur=nom_utilisateur,
            email=email or None,
            mot_de_passe=generate_password_hash(mot_de_passe, method='pbkdf2:sha256'),
            role='admin' if est_admin else 'utilisateur',
            etablissement_id=etablissement_id
        )
        db.session.add(nouvel_utilisateur)
        db.session.commit()
        
        admin_hash = hash_user_id(session['user_id'])
        current_app.logger.info(f"Utilisateur créé par admin_{admin_hash}")
        flash(f"Utilisateur '{nom_utilisateur}' créé.", "success")
        
    except IntegrityError:
        db.session.rollback()
        # ANTI-ENUMERATION : Message générique
        flash("Erreur : Impossible de créer cet utilisateur (nom peut-être déjà pris).", "danger")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur création user", exc_info=True)
        flash("Erreur technique.", "danger")

    return redirect(url_for('admin.gestion_utilisateurs'))

@admin_bp.route("/utilisateurs/modifier_email/<int:id_user>", methods=["POST"])
@admin_required
def modifier_email_utilisateur(id_user):
    etablissement_id = session['etablissement_id']
    email = request.form.get('email', '').strip()
    
    if email and not validate_email(email):
        flash("Format d'email invalide.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    user = db.session.get(Utilisateur, id_user)
    if not user or user.etablissement_id != etablissement_id:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        user.email = email if email else None
        db.session.commit()
        flash("Email mis à jour.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur modif email", exc_info=True)
        flash("Erreur technique.", "error")

    return redirect(url_for('admin.gestion_utilisateurs'))

@admin_bp.route("/utilisateurs/reinitialiser_mdp/<int:id_user>", methods=["POST"])
@admin_required
@limiter.limit("5 per minute") # Rate Limit Strict
def reinitialiser_mdp(id_user):
    etablissement_id = session['etablissement_id']
    
    if id_user == session['user_id']:
        flash("Action impossible sur soi-même.", "warning")
        return redirect(url_for('admin.gestion_utilisateurs'))

    nouveau_mdp = request.form.get('nouveau_mot_de_passe')
    is_valid, error_msg = validate_password_strength(nouveau_mdp)
    if not is_valid:
        flash(error_msg, "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    user = db.session.get(Utilisateur, id_user)
    if not user or user.etablissement_id != etablissement_id:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        user.mot_de_passe = generate_password_hash(nouveau_mdp, method='pbkdf2:sha256')
        db.session.commit()
        flash(f"Mot de passe réinitialisé pour {user.nom_utilisateur}.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur reset MDP", exc_info=True)
        flash("Erreur technique.", "error")

    return redirect(url_for('admin.gestion_utilisateurs'))

@admin_bp.route("/utilisateurs/supprimer/<int:id_user>", methods=["POST"])
@admin_required
@limiter.limit("5 per minute") # Rate Limit Strict
def supprimer_utilisateur(id_user):
    if id_user == session['user_id']:
        flash("Impossible de supprimer son propre compte.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))
    
    etablissement_id = session['etablissement_id']
    user = db.session.get(Utilisateur, id_user)
    
    if not user or user.etablissement_id != etablissement_id:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        has_history = db.session.query(Historique).filter_by(utilisateur_id=user.id).first()
        has_reservations = db.session.query(Reservation).filter_by(utilisateur_id=user.id).first()

        if has_history or has_reservations:
            user.nom_utilisateur = f"Utilisateur_Supprimé_{user.id}_{secrets.token_hex(2)}"
            user.email = None
            user.mot_de_passe = "deleted"
            user.role = "desactive"
            db.session.commit()
            flash("Utilisateur anonymisé et désactivé (historique conservé).", "warning")
        else:
            db.session.delete(user)
            db.session.commit()
            flash("Utilisateur supprimé définitivement.", "success")
            
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur suppression user", exc_info=True)
        flash("Erreur technique.", "error")
        
    return redirect(url_for('admin.gestion_utilisateurs'))

@admin_bp.route("/utilisateurs/promouvoir/<int:id_user>", methods=["POST"])
@admin_required
@limiter.limit("3 per minute") # Rate Limit Très Strict
def promouvoir_utilisateur(id_user):
    if id_user == session['user_id']:
        flash("Action impossible sur soi-même.", "warning")
        return redirect(url_for('admin.gestion_utilisateurs'))
    
    etablissement_id = session['etablissement_id']
    target_user = db.session.get(Utilisateur, id_user)
    current_admin = db.session.get(Utilisateur, session['user_id'])
    
    if not target_user or target_user.etablissement_id != etablissement_id:
        flash("Utilisateur cible introuvable.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))

    password_confirm = request.form.get('password')
    if not password_confirm or not check_password_hash(current_admin.mot_de_passe, password_confirm):
        flash("Mot de passe incorrect.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        target_user.role = 'admin'
        current_admin.role = 'utilisateur'
        db.session.commit()
        session['user_role'] = 'utilisateur'
        flash(f"Passation réussie ! {target_user.nom_utilisateur} est administrateur.", "success")
        return redirect(url_for('inventaire.index'))
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur promotion", exc_info=True)
        flash("Erreur technique.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))

# ============================================================
# GESTION KITS
# ============================================================
@admin_bp.route("/kits")
@admin_required
def gestion_kits():
    etablissement_id = session['etablissement_id']
    kits_data = db.session.execute(
        db.select(Kit, func.count(KitObjet.id).label('count'))
        .outerjoin(KitObjet, Kit.id == KitObjet.kit_id)
        .filter(Kit.etablissement_id == etablissement_id)
        .group_by(Kit.id)
        .order_by(Kit.nom)
    ).mappings().all()
    breadcrumbs = [{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Kits'}]
    return render_template("admin_kits.html", kits=kits_data, breadcrumbs=breadcrumbs)

@admin_bp.route("/kits/ajouter", methods=["POST"])
@admin_required
@limiter.limit("10 per minute")
def ajouter_kit():
    etablissement_id = session['etablissement_id']
    nom = request.form.get("nom", "").strip()
    description = request.form.get("description", "").strip()

    if not nom:
        flash("Le nom du kit est requis.", "danger")
        return redirect(url_for('admin.gestion_kits'))

    try:
        nouveau_kit = Kit(nom=nom, description=description, etablissement_id=etablissement_id)
        db.session.add(nouveau_kit)
        db.session.commit()
        flash(f"Kit '{nom}' créé.", "success")
        return redirect(url_for('admin.modifier_kit', kit_id=nouveau_kit.id))
    except IntegrityError:
        db.session.rollback()
        flash("Un kit portant ce nom existe déjà.", "danger")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur ajout kit", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.gestion_kits'))

@admin_bp.route("/kits/modifier/<int:kit_id>", methods=["GET", "POST"])
@admin_required
def modifier_kit(kit_id):
    etablissement_id = session['etablissement_id']
    kit = db.session.get(Kit, kit_id)
    
    if not kit or kit.etablissement_id != etablissement_id:
        flash("Kit introuvable.", "danger")
        return redirect(url_for('admin.gestion_kits'))

    if request.method == "POST":
        try:
            # CAS 1 : Modification du Nom/Description
            if 'nom_kit' in request.form:
                nouveau_nom = request.form.get('nom_kit', '').strip()
                nouvelle_desc = request.form.get('description_kit', '').strip()
                
                if not nouveau_nom:
                    flash("Le nom du kit ne peut pas être vide.", "warning")
                else:
                    kit.nom = nouveau_nom
                    kit.description = nouvelle_desc
                    db.session.commit()
                    flash("Informations du kit mises à jour.", "success")

            # CAS 2 : Ajout d'un objet
            elif request.form.get("objet_id"):
                objet_id = int(request.form.get("objet_id"))
                quantite = int(request.form.get("quantite", 1))
                
                if quantite <= 0: raise ValueError("Quantité > 0 requise.")

                objet = db.session.get(Objet, objet_id)
                if not objet or objet.etablissement_id != etablissement_id:
                    raise ValueError("Objet invalide.")
                
                assoc = db.session.execute(db.select(KitObjet).filter_by(kit_id=kit.id, objet_id=objet_id)).scalar_one_or_none()
                if assoc:
                    assoc.quantite += quantite
                else:
                    db.session.add(KitObjet(kit_id=kit.id, objet_id=objet_id, quantite=quantite, etablissement_id=etablissement_id))
                
                db.session.commit()
                flash(f"Objet '{objet.nom}' ajouté.", "success")

            # CAS 3 : Mise à jour des quantités (Tableau)
            else:
                modifs = 0
                for key, value in request.form.items():
                    if key.startswith("quantite_"):
                        try:
                            # CORRECTION : Validation stricte de l'ID
                            k_id_str = key.split("_")[1]
                            if not k_id_str.isdigit(): continue
                            
                            k_id = int(k_id_str)
                            val = int(value)
                            
                            assoc = db.session.get(KitObjet, k_id)
                            # Vérification supplémentaire d'appartenance
                            if assoc and assoc.kit_id == kit.id:
                                if val > 0:
                                    assoc.quantite = val
                                    modifs += 1
                                else:
                                    db.session.delete(assoc)
                                    modifs += 1
                        except (ValueError, IndexError): 
                            continue
                if modifs > 0:
                    db.session.commit()
                    flash("Quantités mises à jour.", "success")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error("Erreur modif kit", exc_info=True)
            flash(f"Erreur : {str(e)}", "danger")
            
        return redirect(url_for('admin.modifier_kit', kit_id=kit_id))

    # Chargement des données pour l'affichage
    objets_in_kit = db.session.execute(
        db.select(KitObjet)
        .filter_by(kit_id=kit.id)
        .options(joinedload(KitObjet.objet))
    ).scalars().all()
    
    ids_in_kit = [o.objet_id for o in objets_in_kit]
    
    objets_disponibles = db.session.execute(
        db.select(Objet)
        .filter(Objet.etablissement_id == etablissement_id)
        .filter(~Objet.id.in_(ids_in_kit) if ids_in_kit else True)
        .order_by(Objet.nom)
        .limit(500)
    ).scalars().all()

    breadcrumbs = [
        {'text': 'Admin', 'url': url_for('admin.admin')}, 
        {'text': 'Kits', 'url': url_for('admin.gestion_kits')}, 
        {'text': kit.nom}
    ]
    
    return render_template("admin_kit_modifier.html", 
                           kit=kit, 
                           breadcrumbs=breadcrumbs, 
                           objets_in_kit=objets_in_kit, 
                           objets_disponibles=objets_disponibles)

@admin_bp.route("/kits/retirer_objet/<int:kit_objet_id>", methods=["POST"])
@admin_required
def retirer_objet_kit(kit_objet_id):
    etablissement_id = session['etablissement_id']
    assoc = db.session.get(KitObjet, kit_objet_id)
    if not assoc or assoc.etablissement_id != etablissement_id:
        flash("Objet introuvable.", "danger")
        return redirect(url_for('admin.gestion_kits'))
    kit_id = assoc.kit_id
    try:
        db.session.delete(assoc)
        db.session.commit()
        flash("Objet retiré.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur retrait objet kit", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.modifier_kit', kit_id=kit_id))

@admin_bp.route("/kits/supprimer/<int:kit_id>", methods=["POST"])
@admin_required
def supprimer_kit(kit_id):
    etablissement_id = session['etablissement_id']
    kit = db.session.get(Kit, kit_id)
    if kit and kit.etablissement_id == etablissement_id:
        try:
            db.session.delete(kit)
            db.session.commit()
            flash("Kit supprimé.", "success")
        except Exception:
            db.session.rollback()
            current_app.logger.error("Erreur suppression kit", exc_info=True)
            flash("Erreur technique.", "danger")
    else:
        flash("Kit introuvable.", "danger")
    return redirect(url_for('admin.gestion_kits'))

# ============================================================
# GESTION ÉCHÉANCES
# ============================================================
@admin_bp.route("/echeances", methods=['GET'])
@admin_required
def gestion_echeances():
    etablissement_id = session['etablissement_id']
    echeances = db.session.execute(db.select(Echeance).filter_by(etablissement_id=etablissement_id).order_by(Echeance.date_echeance.asc())).scalars().all()
    breadcrumbs = [{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Échéances'}]
    return render_template("admin_echeances.html", echeances=echeances, breadcrumbs=breadcrumbs, date_actuelle=date.today())

@admin_bp.route("/echeances/ajouter", methods=['POST'])
@admin_required
def ajouter_echeance():
    etablissement_id = session['etablissement_id']
    intitule = request.form.get('intitule', '').strip()
    date_str = request.form.get('date_echeance')
    details = request.form.get('details', '').strip()

    if not intitule or not date_str:
        flash("Champs obligatoires manquants.", "warning")
        return redirect(url_for('admin.gestion_echeances'))

    try:
        date_echeance = datetime.strptime(date_str, '%Y-%m-%d').date()
        db.session.add(Echeance(intitule=intitule, date_echeance=date_echeance, details=details or None, etablissement_id=etablissement_id))
        db.session.commit()
        flash("Échéance ajoutée.", "success")
    except ValueError:
        flash("Format de date invalide.", "warning")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur ajout échéance", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.gestion_echeances'))

@admin_bp.route("/echeances/modifier/<int:id>", methods=['POST'])
@admin_required
def modifier_echeance(id):
    etablissement_id = session['etablissement_id']
    echeance = db.session.get(Echeance, id)
    if not echeance or echeance.etablissement_id != etablissement_id:
        flash("Échéance introuvable.", "danger")
        return redirect(url_for('admin.gestion_echeances'))

    try:
        echeance.intitule = request.form.get('intitule', '').strip()
        echeance.date_echeance = datetime.strptime(request.form.get('date_echeance'), '%Y-%m-%d').date()
        echeance.details = request.form.get('details', '').strip() or None
        echeance.traite = 1 if 'traite' in request.form else 0
        db.session.commit()
        flash("Échéance modifiée.", "success")
    except ValueError:
        flash("Format de date invalide.", "warning")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur modif échéance", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.gestion_echeances'))

@admin_bp.route("/echeances/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_echeance(id):
    etablissement_id = session['etablissement_id']
    echeance = db.session.get(Echeance, id)
    if not echeance or echeance.etablissement_id != etablissement_id:
        flash("Échéance introuvable.", "danger")
        return redirect(url_for('admin.gestion_echeances'))
    try:
        db.session.delete(echeance)
        db.session.commit()
        flash("Échéance supprimée.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur suppression échéance", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.gestion_echeances'))

# ============================================================
# GESTION BUDGET
# ============================================================
@admin_bp.route("/budget", methods=['GET'])
@admin_required
def budget():
    etablissement_id = session['etablissement_id']
    now = datetime.now()
    annee_scolaire_actuelle = now.year if now.month >= 8 else now.year - 1
    try:
        annee_selectionnee = int(request.args.get('annee', annee_scolaire_actuelle))
    except ValueError:
        annee_selectionnee = annee_scolaire_actuelle

    budgets_archives = db.session.execute(db.select(Budget).filter_by(etablissement_id=etablissement_id).order_by(Budget.annee.desc())).scalars().all()
    budget_affiche = db.session.execute(db.select(Budget).filter_by(etablissement_id=etablissement_id, annee=annee_selectionnee)).scalar_one_or_none()

    if not budget_affiche and not budgets_archives:
        try:
            budget_affiche = Budget(annee=annee_selectionnee, montant_initial=0.0, etablissement_id=etablissement_id)
            db.session.add(budget_affiche)
            db.session.commit()
            budgets_archives.insert(0, budget_affiche)
        except IntegrityError: db.session.rollback()

    depenses = []
    total_depenses = 0
    solde = 0
    cloture_autorisee = False

    if budget_affiche:
        depenses = db.session.execute(
            db.select(Depense).filter_by(budget_id=budget_affiche.id).options(joinedload(Depense.fournisseur)).order_by(Depense.date_depense.desc())
        ).scalars().all()
        total_depenses = sum(d.montant for d in depenses)
        solde = budget_affiche.montant_initial - total_depenses
        if date.today() >= date(budget_affiche.annee + 1, 6, 1): cloture_autorisee = True

    budget_actuel_pour_modales = budget_affiche if budget_affiche and not budget_affiche.cloture else db.session.execute(db.select(Budget).filter_by(etablissement_id=etablissement_id, cloture=False).order_by(Budget.annee.desc())).scalars().first()
    annee_proposee = annee_scolaire_actuelle
    if budgets_archives and budgets_archives[0].annee >= annee_scolaire_actuelle: annee_proposee = budgets_archives[0].annee + 1
    fournisseurs = db.session.execute(db.select(Fournisseur).filter_by(etablissement_id=etablissement_id).order_by(Fournisseur.nom)).scalars().all()
    
    return render_template("budget.html", breadcrumbs=[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Budget'}], 
                           budget_affiche=budget_affiche, budget_actuel_pour_modales=budget_actuel_pour_modales,
                           annee_proposee_pour_creation=annee_proposee, depenses=depenses, total_depenses=total_depenses,
                           solde=solde, fournisseurs=fournisseurs, budgets_archives=budgets_archives,
                           annee_selectionnee=annee_selectionnee, cloture_autorisee=cloture_autorisee, now=now)

@admin_bp.route("/budget/definir", methods=['POST'])
@admin_required
def definir_budget():
    etablissement_id = session['etablissement_id']
    try:
        montant = float(request.form.get('montant_initial', '0').replace(',', '.'))
        annee = int(request.form.get('annee'))
        if montant < 0: raise ValueError("Montant négatif.")
        
        budget = db.session.execute(db.select(Budget).filter_by(annee=annee, etablissement_id=etablissement_id)).scalar_one_or_none()
        if budget:
            budget.montant_initial = montant
            budget.cloture = False
            flash(f"Budget {annee} mis à jour.", "success")
        else:
            db.session.add(Budget(annee=annee, montant_initial=montant, etablissement_id=etablissement_id))
            flash(f"Budget {annee} créé.", "success")
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Erreur définition budget", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.budget', annee=annee if 'annee' in locals() else None))

@admin_bp.route("/budget/depense/ajouter", methods=['POST'])
@admin_required
def ajouter_depense():
    etablissement_id = session['etablissement_id']
    try:
        budget = db.session.get(Budget, int(request.form.get('budget_id')))
        if not budget or budget.etablissement_id != etablissement_id or budget.cloture:
            raise ValueError("Budget invalide ou clôturé.")

        est_bon_achat = 'est_bon_achat' in request.form
        fournisseur_id = int(request.form.get('fournisseur_id')) if not est_bon_achat else None
        montant = float(request.form.get('montant').replace(',', '.'))
        date_depense = datetime.strptime(request.form.get('date_depense'), '%Y-%m-%d').date()

        db.session.add(Depense(
            date_depense=date_depense, contenu=request.form.get('contenu', '').strip(),
            montant=montant, est_bon_achat=est_bon_achat, fournisseur_id=fournisseur_id,
            budget_id=budget.id, etablissement_id=etablissement_id
        ))
        db.session.commit()
        flash("Dépense ajoutée.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Erreur ajout dépense", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.budget'))

@admin_bp.route("/budget/depense/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_depense(id):
    etablissement_id = session['etablissement_id']
    depense = db.session.get(Depense, id)
    if depense and depense.etablissement_id == etablissement_id:
        try:
            db.session.delete(depense)
            db.session.commit()
            flash("Dépense supprimée.", "success")
        except Exception:
            db.session.rollback()
            current_app.logger.error("Erreur suppression dépense", exc_info=True)
            flash("Erreur technique.", "danger")
    else:
        flash("Dépense introuvable.", "danger")
    return redirect(url_for('admin.budget'))

@admin_bp.route("/budget/cloturer", methods=['POST'])
@admin_required
def cloturer_budget():
    etablissement_id = session['etablissement_id']
    try:
        budget = db.session.get(Budget, int(request.form.get('budget_id')))
        if budget and budget.etablissement_id == etablissement_id:
            budget.cloture = True
            db.session.commit()
            flash("Budget clôturé.", "success")
        else:
            flash("Budget introuvable.", "danger")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur clôture budget", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.budget'))

@admin_bp.route("/budget/exporter", methods=['GET'])
@admin_required
def exporter_budget():
    etablissement_id = session['etablissement_id']
    date_debut_str = request.args.get('date_debut')
    date_fin_str = request.args.get('date_fin')
    format_type = request.args.get('format')
    
    redirect_url = url_for('main.voir_budget')

    if not all([date_debut_str, date_fin_str, format_type]):
        flash("Paramètres manquants.", "error")
        return redirect(redirect_url)
    
    try:
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        
        depenses = db.session.execute(
            db.select(Depense).options(joinedload(Depense.fournisseur))
            .filter_by(etablissement_id=etablissement_id)
            .filter(Depense.date_depense >= date_debut, Depense.date_depense <= date_fin)
            .order_by(Depense.date_depense.asc())
        ).scalars().all()
        
        if not depenses:
            flash("Aucune dépense sur cette période.", "warning")
            return redirect(redirect_url)
        
        data_export = []
        total = 0.0
        for d in depenses:
            nom_fournisseur = "Petit matériel" if d.est_bon_achat else (d.fournisseur.nom if d.fournisseur else "Inconnu")
            data_export.append({
                'date': d.date_depense.strftime('%d/%m/%Y'),
                'fournisseur': nom_fournisseur,
                'contenu': d.contenu or "-",
                'montant': d.montant
            })
            total += d.montant
        
        metadata = {
            'etablissement': session.get('nom_etablissement', 'Mon Établissement'),
            'date_debut': date_debut.strftime('%d/%m/%Y'),
            'date_fin': date_fin.strftime('%d/%m/%Y'),
            'date_generation': datetime.now().strftime('%d/%m/%Y à %H:%M'),
            'nombre_depenses': len(data_export),
            'total': total
        }
        
        if format_type == 'excel': 
            return generer_budget_excel_pro(data_export, metadata)
        else: 
            return generer_budget_pdf_pro(data_export, metadata)
    
    except Exception as e:
        current_app.logger.error(f"Erreur export budget: {e}", exc_info=True)
        flash("Erreur technique lors de l'export.", "error")
        return redirect(redirect_url)

# ============================================================
# GESTION FOURNISSEURS
# ============================================================
@admin_bp.route("/fournisseurs", methods=['GET'])
@admin_required
def gestion_fournisseurs():
    etablissement_id = session['etablissement_id']
    fournisseurs = db.session.execute(
        db.select(Fournisseur, func.count(Depense.id).label('depenses_count'))
        .outerjoin(Depense, Fournisseur.id == Depense.fournisseur_id)
        .filter(Fournisseur.etablissement_id == etablissement_id)
        .group_by(Fournisseur.id).order_by(Fournisseur.nom)
    ).all()
    return render_template("admin_fournisseurs.html", fournisseurs=fournisseurs, breadcrumbs=[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Fournisseurs'}])

@admin_bp.route("/fournisseurs/ajouter", methods=["POST"])
@admin_required
def ajouter_fournisseur():
    etablissement_id = session['etablissement_id']
    nom = request.form.get("nom")
    site_web = request.form.get("site_web")
    
    try:
        logo_filename = None
        
        # 1. Gestion Fichier (Sécurisée)
        if 'logo_file' in request.files:
            file = request.files['logo_file']
            if file and file.filename != '':
                # A. Vérification Taille
                file.seek(0, 2)
                if file.tell() > MAX_FILE_SIZE:
                    raise ValueError("Image trop volumineuse (Max 10Mo).")
                file.seek(0)
                
                # B. Vérification Type (Magic Bytes)
                header = file.read(512)
                file.seek(0)
                format_img = imghdr.what(None, header)
                
                if format_img not in ['jpeg', 'png', 'gif']:
                    raise ValueError("Format image non supporté (JPG, PNG, GIF uniquement).")
                
                # C. Upload
                filename = secure_filename(file.filename)
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                unique_filename = f"{ts}_{filename}"
                
                upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'fournisseurs')
                os.makedirs(upload_folder, exist_ok=True)
                    
                file.save(os.path.join(upload_folder, unique_filename))
                logo_filename = unique_filename

        # 2. Gestion URL (Si pas de fichier)
        if not logo_filename:
            logo_url = request.form.get("logo_url", "").strip()
            if logo_url:
                if validate_url(logo_url):
                    logo_filename = logo_url
                else:
                    raise ValueError("URL du logo invalide.")

        # 3. Insertion DB
        new_fournisseur = Fournisseur(
            nom=nom,
            site_web=site_web,
            logo=logo_filename,
            etablissement_id=etablissement_id
        )
        db.session.add(new_fournisseur)
        db.session.commit()
        flash("Fournisseur ajouté avec succès.", "success")

    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Erreur ajout fournisseur", exc_info=True)
        flash("Erreur technique lors de l'ajout.", "error")

    return redirect(url_for('main.voir_fournisseurs'))

@admin_bp.route("/fournisseurs/modifier/<int:id>", methods=["POST"])
@admin_required
def modifier_fournisseur(id):
    etablissement_id = session['etablissement_id']
    fournisseur = db.session.get(Fournisseur, id)
    
    if not fournisseur or fournisseur.etablissement_id != etablissement_id:
        flash("Fournisseur introuvable.", "error")
        return redirect(url_for('main.voir_fournisseurs'))

    try:
        fournisseur.nom = request.form.get("nom")
        fournisseur.site_web = request.form.get("site_web")

        # 1. Gestion Fichier (Sécurisée)
        if 'logo_file' in request.files:
            file = request.files['logo_file']
            if file and file.filename != '':
                file.seek(0, 2)
                if file.tell() > MAX_FILE_SIZE:
                    raise ValueError("Image trop volumineuse (Max 10Mo).")
                file.seek(0)
                
                header = file.read(512)
                file.seek(0)
                format_img = imghdr.what(None, header)
                
                if format_img not in ['jpeg', 'png', 'gif']:
                    raise ValueError("Format image non supporté.")
                
                filename = secure_filename(file.filename)
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                unique_filename = f"{ts}_{filename}"
                
                upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'fournisseurs')
                os.makedirs(upload_folder, exist_ok=True)
                    
                file.save(os.path.join(upload_folder, unique_filename))
                fournisseur.logo = unique_filename
        
        # 2. Gestion URL (Seulement si renseignée et pas de fichier uploadé)
        logo_url = request.form.get("logo_url", "").strip()
        if logo_url and 'logo_file' in request.files and request.files['logo_file'].filename == '':
            if validate_url(logo_url):
                fournisseur.logo = logo_url
            else:
                raise ValueError("URL du logo invalide.")

        db.session.commit()
        flash("Fournisseur modifié.", "success")

    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Erreur modif fournisseur", exc_info=True)
        flash("Erreur technique.", "error")

    return redirect(url_for('main.voir_fournisseurs'))

@admin_bp.route("/fournisseurs/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_fournisseur(id):
    etablissement_id = session['etablissement_id']
    fournisseur = db.session.get(Fournisseur, id)
    if fournisseur and fournisseur.etablissement_id == etablissement_id:
        if fournisseur.depenses:
            flash("Impossible : lié à des dépenses.", "danger")
        else:
            try:
                db.session.delete(fournisseur)
                db.session.commit()
                flash("Fournisseur supprimé.", "success")
            except Exception:
                db.session.rollback()
                current_app.logger.error("Erreur suppression fournisseur", exc_info=True)
                flash("Erreur technique.", "danger")
    else:
        flash("Fournisseur introuvable.", "danger")
    return redirect(url_for('admin.gestion_fournisseurs'))

# ============================================================
# SAUVEGARDE & RESTAURATION
# ============================================================
@admin_bp.route("/sauvegardes")
@admin_required
def gestion_sauvegardes():
    etablissement_id = session['etablissement_id']
    params = get_etablissement_params(etablissement_id)
    if params.get('licence_statut') != 'PRO':
        flash("Réservé à la version PRO.", "warning")
        return redirect(url_for('admin.admin'))
    return render_template("admin_backup.html", now=datetime.now(), breadcrumbs=[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Sauvegardes'}])

@admin_bp.route("/telecharger_db")
@admin_required
def telecharger_db():
    etablissement_id = session['etablissement_id']
    params = get_etablissement_params(etablissement_id)
    if params.get('licence_statut') != 'PRO':
        flash("Réservé PRO.", "warning")
        return redirect(url_for('admin.gestion_sauvegardes'))

    try:
        data = {
            'metadata': {'version': '1.0', 'date': datetime.now().isoformat(), 'etablissement': session.get('nom_etablissement')},
            'armoires': [], 'categories': [], 'fournisseurs': [], 'objets': [], 'budget': [], 'depenses': [], 'echeances': []
        }
        
        # Extraction des données (simplifiée pour la lisibilité)
        for a in db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars():
            data['armoires'].append({'id': a.id, 'nom': a.nom})
        for c in db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars():
            data['categories'].append({'id': c.id, 'nom': c.nom})
        for f in db.session.execute(db.select(Fournisseur).filter_by(etablissement_id=etablissement_id)).scalars():
            data['fournisseurs'].append({'id': f.id, 'nom': f.nom, 'site_web': f.site_web, 'logo': f.logo})
        for o in db.session.execute(db.select(Objet).filter_by(etablissement_id=etablissement_id)).scalars():
            data['objets'].append({
                'id': o.id, 'nom': o.nom, 'quantite': o.quantite_physique, 'seuil': o.seuil,
                'armoire_id': o.armoire_id, 'categorie_id': o.categorie_id, 'date_peremption': o.date_peremption,
                'image_url': o.image_url, 'fds_url': o.fds_url
            })
        for b in db.session.execute(db.select(Budget).filter_by(etablissement_id=etablissement_id)).scalars():
            b_data = {'id': b.id, 'annee': b.annee, 'montant': b.montant_initial, 'cloture': b.cloture}
            data['budget'].append(b_data)
            for d in b.depenses:
                data['depenses'].append({
                    'budget_id': b.id, 'date': d.date_depense, 'contenu': d.contenu,
                    'montant': d.montant, 'est_bon_achat': d.est_bon_achat, 'fournisseur_id': d.fournisseur_id
                })
        for e in db.session.execute(db.select(Echeance).filter_by(etablissement_id=etablissement_id)).scalars():
            data['echeances'].append({'intitule': e.intitule, 'date': e.date_echeance, 'details': e.details, 'traite': e.traite})

        json_str = json.dumps(data, default=json_serial, indent=4)
        buffer = BytesIO()
        buffer.write(json_str.encode('utf-8'))
        buffer.seek(0)
        log_action('backup_download', "Export JSON")
        safe_etab = sanitize_filename(session.get('nom_etablissement', 'Backup'))
        return send_file(buffer, as_attachment=True, download_name=f"Sauvegarde_{safe_etab}_{date.today()}.json", mimetype='application/json')

    except Exception:
        current_app.logger.error("Erreur backup", exc_info=True)
        flash("Erreur technique.", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))

@admin_bp.route("/importer_db", methods=["POST"])
@admin_required
def importer_db():
    etablissement_id = session['etablissement_id']
    if 'fichier' not in request.files:
        flash("Aucun fichier.", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))
        
    fichier = request.files['fichier']
    
    # CORRECTION : Vérification taille fichier avant lecture
    fichier.seek(0, 2)
    if fichier.tell() > MAX_JSON_SIZE:
        flash("Fichier JSON trop volumineux (Max 5Mo).", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))
    fichier.seek(0)

    if fichier.filename == '' or not allowed_file(fichier.filename) or not fichier.filename.endswith('.json'):
        flash("Fichier invalide (.json requis).", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))

    try:
        data = json.load(fichier)
        
        # CORRECTION : Transaction atomique (Tout ou rien)
        with db.session.begin_nested():
            map_armoires = {}
            map_categories = {}
            map_fournisseurs = {}
            map_budgets = {}

            # Nettoyage
            for model in [KitObjet, Historique, Reservation, Suggestion, Depense, Objet, Kit, Budget, Echeance, Armoire, Categorie, Fournisseur]:
                db.session.query(model).filter_by(etablissement_id=etablissement_id).delete()
            db.session.flush()

            # Reconstruction
            for a in data.get('armoires', []):
                new_a = Armoire(nom=a['nom'], etablissement_id=etablissement_id)
                db.session.add(new_a)
                db.session.flush()
                map_armoires[a['id']] = new_a.id

            for c in data.get('categories', []):
                new_c = Categorie(nom=c['nom'], etablissement_id=etablissement_id)
                db.session.add(new_c)
                db.session.flush()
                map_categories[c['id']] = new_c.id

            for f in data.get('fournisseurs', []):
                new_f = Fournisseur(nom=f['nom'], site_web=f.get('site_web'), logo=f.get('logo'), etablissement_id=etablissement_id)
                db.session.add(new_f)
                db.session.flush()
                map_fournisseurs[f['id']] = new_f.id

            for o in data.get('objets', []):
                new_armoire_id = map_armoires.get(o['armoire_id'])
                new_cat_id = map_categories.get(o['categorie_id'])
                if not new_armoire_id or not new_cat_id: continue 
                
                date_perim = None
                if o.get('date_peremption'):
                    try: date_perim = datetime.fromisoformat(o['date_peremption']).date()
                    except: pass

                db.session.add(Objet(
                    nom=o['nom'], quantite_physique=o['quantite'], seuil=o['seuil'],
                    armoire_id=new_armoire_id, categorie_id=new_cat_id, date_peremption=date_perim,
                    image_url=o.get('image_url'), fds_url=o.get('fds_url'), etablissement_id=etablissement_id
                ))

            for b in data.get('budget', []):
                new_b = Budget(annee=b['annee'], montant_initial=b['montant'], cloture=b['cloture'], etablissement_id=etablissement_id)
                db.session.add(new_b)
                db.session.flush()
                map_budgets[b['id']] = new_b.id

            for d in data.get('depenses', []):
                new_budget_id = map_budgets.get(d['budget_id'])
                if not new_budget_id: continue
                new_fournisseur_id = map_fournisseurs.get(d['fournisseur_id']) if d.get('fournisseur_id') else None
                try: date_dep = datetime.fromisoformat(d['date']).date()
                except: date_dep = date.today()
                db.session.add(Depense(
                    budget_id=new_budget_id, fournisseur_id=new_fournisseur_id, contenu=d['contenu'],
                    montant=d['montant'], date_depense=date_dep, est_bon_achat=d.get('est_bon_achat', False),
                    etablissement_id=etablissement_id
                ))

            for e in data.get('echeances', []):
                try: date_ech = datetime.fromisoformat(e['date']).date()
                except: continue
                db.session.add(Echeance(intitule=e['intitule'], date_echeance=date_ech, details=e.get('details'), traite=e.get('traite', 0), etablissement_id=etablissement_id))

        db.session.commit()
        log_action('backup_restore', "Import JSON")
        flash("Restauration réussie !", "success")

    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur import DB", exc_info=True)
        flash("Erreur critique lors de l'importation.", "error")

    return redirect(url_for('admin.gestion_sauvegardes'))

# ============================================================
# IMPORT EXCEL
# ============================================================
@admin_bp.route("/importer", methods=['GET'])
@admin_required
def importer_page():
    etablissement_id = session['etablissement_id']
    armoires = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars().all()
    categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars().all()
    return render_template("admin_import.html", breadcrumbs=[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Import'}], armoires=armoires, categories=categories, now=datetime.now())

@admin_bp.route("/telecharger_modele")
@admin_required
def telecharger_modele_excel():
    etablissement_id = session['etablissement_id']
    armoires = db.session.execute(db.select(Armoire.nom).filter_by(etablissement_id=etablissement_id).order_by(Armoire.nom)).scalars().all()
    categories = db.session.execute(db.select(Categorie.nom).filter_by(etablissement_id=etablissement_id).order_by(Categorie.nom)).scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventaire"
    ws.append(["Nom", "Quantité", "Seuil", "Armoire", "Catégorie", "Date Péremption", "Image (URL)"])
    
    # Styles et validations (simplifié)
    ws_data = wb.create_sheet("Data_Listes")
    ws_data.sheet_state = 'hidden'
    for i, nom in enumerate(armoires, 1): ws_data.cell(row=i, column=1, value=nom)
    for i, nom in enumerate(categories, 1): ws_data.cell(row=i, column=2, value=nom)
    
    if armoires:
        dv = DataValidation(type="list", formula1=f"'Data_Listes'!$A$1:$A${len(armoires)}", allow_blank=True)
        ws.add_data_validation(dv)
        dv.add('D2:D1000')
    if categories:
        dv = DataValidation(type="list", formula1=f"'Data_Listes'!$B$1:$B${len(categories)}", allow_blank=True)
        ws.add_data_validation(dv)
        dv.add('E2:E1000')

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='modele_import.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@admin_bp.route("/importer", methods=['POST'])
@admin_required
@limiter.limit("10 per minute")
def importer_fichier():
    etablissement_id = session['etablissement_id']
    if 'fichier_excel' not in request.files:
        flash("Aucun fichier.", "error")
        return redirect(url_for('admin.importer_page'))

    fichier = request.files['fichier_excel']
    if fichier.filename == '' or not allowed_file(fichier.filename) or not fichier.filename.endswith('.xlsx'):
        flash("Fichier invalide (.xlsx requis).", "error")
        return redirect(url_for('admin.importer_page'))

    # Check size
    fichier.seek(0, 2)
    if fichier.tell() > MAX_FILE_SIZE:
        flash("Fichier trop volumineux.", "error")
        return redirect(url_for('admin.importer_page'))
    fichier.seek(0)

    try:
        wb = load_workbook(fichier)
        ws = wb.active
        
        # 1. Validation des en-têtes
        headers = {cell.value: idx for idx, cell in enumerate(ws[1], 0) if cell.value}
        required_cols = {'Nom', 'Quantité', 'Seuil', 'Armoire', 'Catégorie'}
        
        if not required_cols.issubset(headers.keys()):
            flash(f"Colonnes manquantes. Requis : {', '.join(required_cols)}", "error")
            return redirect(url_for('admin.importer_page'))

        existing_objets = {o.nom.lower() for o in db.session.execute(db.select(Objet).filter_by(etablissement_id=etablissement_id)).scalars().all()}
        armoires_map = {a.nom.lower(): a.id for a in db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars().all()}
        categories_map = {c.nom.lower(): c.id for c in db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars().all()}
        
        success_count = 0
        errors = []
        
        # 2. Lecture avec limite de lignes
        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            if i > MAX_IMPORT_ROWS:
                errors.append(f"Limite de {MAX_IMPORT_ROWS} lignes atteinte. Le reste a été ignoré.")
                break
                
            if not row: continue
            
            # Récupération via le mapping des colonnes
            try:
                nom = row[headers['Nom']]
                qte = row[headers['Quantité']]
                seuil = row[headers['Seuil']]
                arm_nom = row[headers['Armoire']]
                cat_nom = row[headers['Catégorie']]
                
                # Colonnes optionnelles
                date_val = row[headers['Date Péremption']] if 'Date Péremption' in headers else None
                img_val = row[headers['Image (URL)']] if 'Image (URL)' in headers else None
            except IndexError:
                continue # Ligne malformée

            if not all([nom, qte is not None, seuil is not None]):
                errors.append(f"Ligne {i}: Données obligatoires manquantes")
                continue
                
            if str(nom).lower() in existing_objets: continue
            
            arm_id = armoires_map.get(str(arm_nom).lower().strip()) if arm_nom else None
            cat_id = categories_map.get(str(cat_nom).lower().strip()) if cat_nom else None
            
            if not arm_id or not cat_id:
                errors.append(f"Ligne {i}: Armoire ou Catégorie inconnue")
                continue
                
            date_perim = None
            if date_val:
                if isinstance(date_val, datetime): date_perim = date_val.date()
                elif isinstance(date_val, str):
                    try: date_perim = datetime.strptime(date_val.split(' ')[0], '%Y-%m-%d').date()
                    except: pass

            db.session.add(Objet(
                nom=str(nom), quantite_physique=int(qte), seuil=int(seuil),
                armoire_id=arm_id, categorie_id=cat_id, date_peremption=date_perim,
                image_url=str(img_val) if img_val else None,
                etablissement_id=etablissement_id
            ))
            success_count += 1
            
        if errors:
            db.session.rollback()
            for e in errors[:5]: flash(e, "error")
            if len(errors) > 5: flash(f"... et {len(errors)-5} autres erreurs.", "error")
        else:
            db.session.commit()
            log_action('import_excel', f"{success_count} objets importés")
            flash(f"{success_count} objets importés.", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Erreur import Excel", exc_info=True)
        flash("Erreur technique.", "error")

    return redirect(url_for('admin.importer_page'))



@admin_bp.route("/exporter_inventaire")
@admin_required
@limiter.limit("5 per minute")
def exporter_inventaire():
    etablissement_id = session['etablissement_id']
    format_type = request.args.get('format')
    
    if format_type not in ['excel', 'pdf']:
        flash("Format non supporté.", "error")
        return redirect(url_for('admin.admin'))

    try:
        # 1. Récupération des données (Optimisée avec Jointures)
        objets = db.session.execute(
            db.select(Objet)
            .options(joinedload(Objet.categorie), joinedload(Objet.armoire))
            .filter_by(etablissement_id=etablissement_id)
            .order_by(Objet.categorie_id, Objet.nom) # Tri par Catégorie puis Nom
        ).scalars().all()
        
        # 2. Préparation des données pour les générateurs
        data_export = []
        for obj in objets:
            data_export.append({
                'categorie': obj.categorie.nom if obj.categorie else "Sans catégorie",
                'nom': obj.nom,
                'quantite': obj.quantite_physique,
                'seuil': obj.seuil,
                'armoire': obj.armoire.nom if obj.armoire else "Non rangé",
                'peremption': obj.date_peremption.strftime('%d/%m/%Y') if obj.date_peremption else "-"
            })
            
        # 3. Métadonnées
        metadata = {
            'etablissement': session.get('nom_etablissement', 'Mon Établissement'),
            'date_generation': datetime.now().strftime('%d/%m/%Y à %H:%M'),
            'total': len(data_export)
        }

        log_action('export_inventaire', f"Format: {format_type}, Items: {len(data_export)}")

        # 4. Appel des générateurs
        if format_type == 'excel':
            return generer_inventaire_excel(data_export, metadata)
        else:
            return generer_inventaire_pdf(data_export, metadata)

    except Exception as e:
        current_app.logger.error(f"Erreur export inventaire: {e}", exc_info=True)
        flash("Une erreur technique est survenue lors de l'export.", "error")
        return redirect(url_for('admin.admin'))

# ============================================================
# MODULE RAPPORTS & ACTIVITÉ (Version Durcie)
# ============================================================

# Constantes de sécurité pour les rapports
MAX_EXPORT_DAYS = 366      # Limite la plage à 1 an
MAX_EXPORT_ROWS = 5000     # Limite le nombre de lignes pour éviter le crash RAM (ReportLab/OpenPyXL)
ALLOWED_FORMATS = {'excel', 'pdf'}

@admin_bp.route("/rapports")
@admin_required
def rapports():
    etablissement_id = session['etablissement_id']
    
    # 1. Récupération des paramètres d'URL
    page = request.args.get('page', 1, type=int)
    filtre_action = request.args.get('action', 'all') # all, creation, modification, deplacement, suppression
    search_query = request.args.get('q', '').strip()
    
    # 2. Construction de la requête de base
    stmt = (
        db.select(Historique, Utilisateur.nom_utilisateur, Objet.nom.label('objet_nom'))
        .outerjoin(Utilisateur, Historique.utilisateur_id == Utilisateur.id)
        .outerjoin(Objet, Historique.objet_id == Objet.id)
        .filter(Historique.etablissement_id == etablissement_id)
        .order_by(Historique.timestamp.desc())
    )

    # 3. Application des filtres
    if filtre_action == 'creation':
        stmt = stmt.filter(Historique.action == 'Création')
    elif filtre_action == 'suppression':
        stmt = stmt.filter(Historique.action == 'Suppression')
    elif filtre_action == 'modification':
        # Exclure les déplacements (qui sont techniquement des modifs)
        stmt = stmt.filter(
            Historique.action == 'Modification',
            ~Historique.details.ilike('%Déplacé%'),
            ~Historique.details.ilike('%Armoire%')
        )
    elif filtre_action == 'deplacement':
        stmt = stmt.filter(
            Historique.action == 'Modification',
            (Historique.details.ilike('%Déplacé%') | Historique.details.ilike('%Armoire%'))
        )

    # 4. Recherche textuelle
    if search_query:
        stmt = stmt.filter(
            (Historique.details.ilike(f'%{search_query}%')) |
            (Objet.nom.ilike(f'%{search_query}%')) |
            (Utilisateur.nom_utilisateur.ilike(f'%{search_query}%'))
        )

    # 5. Pagination (50 items par page)
    pagination = db.paginate(stmt, page=page, per_page=50)

    # 6. Formatage des données pour la vue
    logs = []
    for item in pagination.items:
        # Détection du type pour gérer le cas où paginate renvoie un objet ou un tuple
        if isinstance(item, Historique):
            # Cas : Modèle seul
            h = item
            user_name = h.utilisateur.nom_utilisateur if h.utilisateur else "Utilisateur supprimé"
            
            # Récupération manuelle du nom de l'objet (si nécessaire)
            obj_name = "Objet supprimé"
            if h.objet_id:
                obj = db.session.get(Objet, h.objet_id)
                if obj: obj_name = obj.nom
        else:
            # Cas : Tuple (Historique, nom_user, nom_objet)
            h, user_name, obj_name = item

        # Détection du type pour les badges (si pas déjà filtré)
        type_badge = 'secondary'
        if h.action == 'Création': type_badge = 'success'
        elif h.action == 'Suppression': type_badge = 'danger'
        elif 'Déplacé' in (h.details or ''): type_badge = 'info'
        elif h.action == 'Modification': type_badge = 'warning'

        logs.append({
            'date': h.timestamp,
            'user': user_name or "Utilisateur supprimé",
            'objet': obj_name or "Objet supprimé",
            'action': h.action,
            'details': h.details,
            'type_badge': type_badge
        })

    breadcrumbs = [
        {'text': 'Admin', 'url': url_for('admin.admin')}, 
        {'text': 'Historique Complet'}
    ]

    return render_template("rapports.html", 
                           logs=logs, 
                           pagination=pagination, 
                           filtre_actif=filtre_action,
                           search_query=search_query,
                           breadcrumbs=breadcrumbs)


@admin_bp.route("/exporter_rapports", methods=['GET'])
@admin_required
@limiter.limit("5 per minute")
def exporter_rapports():
    etablissement_id = session['etablissement_id']
    
    # 1. Récupération des paramètres
    date_debut_str = request.args.get('date_debut')
    date_fin_str = request.args.get('date_fin')
    format_type = request.args.get('format')
    group_by = request.args.get('group_by', 'date')
    
    # NOUVEAU : Récupération des actions cochées (liste)
    # Flask récupère les checkbox multiples avec getlist
    selected_actions = request.args.getlist('actions') 

    if not all([date_debut_str, date_fin_str, format_type]):
        flash("Paramètres manquants.", "warning")
        return redirect(url_for('admin.rapports'))

    if format_type not in ALLOWED_FORMATS:
        flash("Format non supporté.", "error")
        return redirect(url_for('admin.rapports'))

    try:
        # 2. Parsing Dates
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d')
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d')
        date_fin = date_fin.replace(hour=23, minute=59, second=59)

        if date_debut > date_fin:
            flash("Dates incohérentes.", "warning")
            return redirect(url_for('admin.rapports'))
            
        if (date_fin - date_debut).days > MAX_EXPORT_DAYS:
            flash(f"Période limitée à {MAX_EXPORT_DAYS} jours.", "warning")
            return redirect(url_for('admin.rapports'))

        # 3. Construction Requête
        query = db.select(
            Historique,
            Utilisateur.nom_utilisateur,
            Objet.nom.label('objet_nom')
        ).outerjoin(Utilisateur, Historique.utilisateur_id == Utilisateur.id)\
         .outerjoin(Objet, Historique.objet_id == Objet.id)\
         .filter(Historique.etablissement_id == etablissement_id)\
         .filter(Historique.timestamp >= date_debut)\
         .filter(Historique.timestamp <= date_fin)

        # --- LOGIQUE DE FILTRE ET TRI ---
        if group_by == 'action':
            # Si des actions spécifiques sont cochées, on filtre
            if selected_actions:
                query = query.filter(Historique.action.in_(selected_actions))
            
            # On trie par Action puis par Date
            query = query.order_by(Historique.action.asc(), Historique.timestamp.desc())
        else:
            # Tri chronologique standard
            query = query.order_by(Historique.timestamp.desc())

        # Protection RAM
        query = query.limit(MAX_EXPORT_ROWS)
        resultats = db.session.execute(query).all()

        if not resultats:
            flash("Aucune donnée trouvée pour ces critères.", "info")
            return redirect(url_for('admin.rapports'))

        # 4. Préparation Données
        data_export = []
        for h, user_name, obj_name in resultats:
            data_export.append({
                'date': h.timestamp.strftime('%d/%m/%Y'),
                'heure': h.timestamp.strftime('%H:%M'),
                'utilisateur': user_name or "Inconnu",
                'action': h.action,
                'objet': obj_name or "-",
                'details': h.details or ""
            })

        # Métadonnées enrichies
        filtre_info = "Tous types"
        if group_by == 'action' and selected_actions:
            filtre_info = ", ".join(selected_actions)

        metadata = {
            'etablissement': session.get('nom_etablissement', 'LabFlow'),
            'periode': f"Du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}",
            'total': len(data_export),
            'date_generation': datetime.now().strftime('%d/%m/%Y à %H:%M'),
            'filtre': filtre_info # On pourra l'afficher dans le PDF si on veut
        }

        log_action('export_rapport', f"Format: {format_type}, Rows: {len(data_export)}")

        if format_type == 'excel':
            return generer_rapport_excel(data_export, metadata)
        else:
            return generer_rapport_pdf(data_export, metadata)

    except Exception as e:
        current_app.logger.error(f"Erreur export: {e}", exc_info=True)
        flash("Erreur technique lors de la génération.", "error")
        return redirect(url_for('admin.rapports'))

# ============================================================
# LICENCE (Rate Limit Custom)
# ============================================================
class RateLimiter:
    def __init__(self):
        self.attempts = defaultdict(list)
        self.last_cleanup = datetime.now()

    def _cleanup_all(self):
        """Supprime les clés vides et obsolètes."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=15)
        
        # On itère sur une copie des clés pour pouvoir supprimer
        for key in list(self.attempts.keys()):
            # On ne garde que les tentatives récentes
            self.attempts[key] = [t for t in self.attempts[key] if t > cutoff]
            # Si la liste est vide, on supprime la clé pour libérer la mémoire
            if not self.attempts[key]:
                del self.attempts[key]
        
        self.last_cleanup = now

    def is_allowed(self, key):
        now = datetime.now()
        
        # Nettoyage opportuniste global (toutes les heures)
        if (now - self.last_cleanup) > timedelta(hours=1):
            self._cleanup_all()
        
        # Nettoyage spécifique à la clé courante
        cutoff = now - timedelta(minutes=15)
        self.attempts[key] = [t for t in self.attempts[key] if t > cutoff]
        
        if len(self.attempts[key]) >= 5: 
            return False
            
        self.attempts[key].append(now)
        return True
    
    def reset(self, key):
        if key in self.attempts: del self.attempts[key]

license_limiter = RateLimiter()

def rate_limit_license(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        eid = session.get('etablissement_id')
        if not eid: return redirect(url_for('main.index'))
        if not license_limiter.is_allowed(eid):
            flash("Trop de tentatives. Réessayez dans 15 min.", "error")
            return redirect(url_for('main.a_propos'))
        return f(*args, **kwargs)
    return wrapped

@admin_bp.route("/activer_licence", methods=["POST"])
@admin_required
@rate_limit_license
def activer_licence():
    etablissement_id = session.get('etablissement_id')
    cle_fournie = request.form.get('licence_cle', '').strip().upper()
    
    if not cle_fournie or len(cle_fournie) < 10:
        flash("Clé invalide.", "error")
        return redirect(url_for('main.a_propos'))
    
    try:
        param_instance = db.session.execute(db.select(Parametre).filter_by(etablissement_id=etablissement_id, cle='instance_id')).scalar_one_or_none()
        if not param_instance:
            flash("Erreur critique : Instance ID manquant.", "error")
            return redirect(url_for('main.a_propos'))
        
        cle_attendue = calculate_license_key(param_instance.valeur.strip())
        if not secrets.compare_digest(cle_fournie, cle_attendue):
            flash("Clé incorrecte.", "error")
            return redirect(url_for('main.a_propos'))
        
        # Activation
        param_statut = db.session.execute(db.select(Parametre).filter_by(etablissement_id=etablissement_id, cle='licence_statut')).scalar_one_or_none()
        if not param_statut: db.session.add(Parametre(etablissement_id=etablissement_id, cle='licence_statut', valeur='PRO'))
        else: param_statut.valeur = 'PRO'
        
        db.session.commit()
        try: cache.delete_memoized(get_etablissement_params, etablissement_id)
        except: pass
        license_limiter.reset(etablissement_id)
        flash("Licence PRO activée !", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur activation licence: {str(e)}", exc_info=True)
        flash("Erreur technique lors de l'activation.", "error")
    
    return redirect(url_for('main.a_propos'))


# ============================================================
# GÉNÉRATEURS RAPPORTS PROFESSIONNELS (PDF/EXCEL) - VERSION FINALE
# ============================================================

# Imports spécifiques aux rapports (à laisser ici pour ne pas polluer le haut du fichier)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from html import escape
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from io import BytesIO
from datetime import date
import re


# ============================================================
# UTILITAIRES INTERNES AUX RAPPORTS
# ============================================================

def sanitize_filename_report(text):
    """Nettoie un nom de fichier pour éviter les caractères problématiques."""
    if not text: return "Rapport"
    # On garde uniquement alphanumérique, tirets et underscores
    return re.sub(r'[^\w\s-]', '', str(text)).strip().replace(' ', '_')


def sanitize_for_excel_report(text):
    """Prépare le texte pour Excel (évite les formules injection)."""
    if not text:
        return ""
    text = str(text)
    # Empêche l'injection de formules (=, +, -, @)
    if text.startswith(('=', '+', '-', '@')):
        text = "'" + text
    return text


# ============================================================
# GÉNÉRATEUR PDF AVEC LOGO VECTORIEL
# ============================================================

class LogoGraphique(Flowable):
    """Dessine un petit graphique vectoriel (Logo) directement en PDF."""
    def __init__(self, width=40, height=40):
        Flowable.__init__(self)
        self.width = width
        self.height = height

    def draw(self):
        # Couleurs
        bleu_fonce = colors.HexColor('#1F3B73')
        bleu_clair = colors.HexColor('#4facfe')
        
        # Barres du graphique
        self.canv.setFillColor(bleu_fonce)
        self.canv.rect(0, 0, 8, 15, fill=1, stroke=0)  # Barre 1
        self.canv.rect(12, 0, 8, 25, fill=1, stroke=0) # Barre 2
        
        self.canv.setFillColor(bleu_clair)
        self.canv.rect(24, 0, 8, 35, fill=1, stroke=0) # Barre 3 (La plus haute)
        
        # Ligne de tendance (Flèche)
        self.canv.setStrokeColor(colors.HexColor('#FFD700')) # Or
        self.canv.setLineWidth(2)
        self.canv.line(-5, 5, 35, 40) # Ligne montante

def generer_rapport_pdf(data, metadata):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.0*cm, leftMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm,
        title=f"Rapport - {metadata['etablissement']}"
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # --- EN-TÊTE AVEC LOGO ---
    # On crée un tableau invisible pour mettre le Logo à gauche et le Titre au centre
    logo = LogoGraphique(width=40, height=40)
    
    titre_style = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#1F3B73'), alignment=TA_LEFT)
    sous_titre_style = ParagraphStyle('SousTitre', parent=styles['Normal'], fontSize=12, textColor=colors.gray, alignment=TA_LEFT)
    
    titre_bloc = [
        Paragraph(f"RAPPORT D'ACTIVITÉ", titre_style),
        Paragraph(f"{escape(metadata['etablissement'])}", sous_titre_style)
    ]
    
    # Tableau d'en-tête : [Logo | Textes]
    header_table_data = [[logo, titre_bloc]]
    header_table = Table(header_table_data, colWidths=[1.5*cm, 20*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(header_table)
    
    elements.append(Spacer(1, 0.5*cm))
    
    # --- MÉTADONNÉES (Cadre Gris) ---
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=10, textColor=colors.black)
    meta_label = ParagraphStyle('MetaLabel', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#1F3B73'), fontName='Helvetica-Bold')
    
    meta_data = [
        [Paragraph('Période :', meta_label), Paragraph(metadata['periode'], meta_style),
         Paragraph('Généré le :', meta_label), Paragraph(metadata['date_generation'], meta_style)],
        [Paragraph('Total :', meta_label), Paragraph(f"{metadata['total']} entrées", meta_style), '', '']
    ]
    
    meta_table = Table(meta_data, colWidths=[2.5*cm, 8*cm, 2.5*cm, 8*cm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # --- TABLEAU DE DONNÉES ---
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9, textColor=colors.black)
    
    headers = [
        Paragraph('Date', header_style),
        Paragraph('Heure', header_style),
        Paragraph('Utilisateur', header_style),
        Paragraph('Action', header_style),
        Paragraph('Objet', header_style),
        Paragraph('Détails', header_style)
    ]
    
    table_data = [headers]
    for row in data:
        table_data.append([
            Paragraph(row['date'], cell_style),
            Paragraph(row['heure'], cell_style),
            Paragraph(escape(row['utilisateur']), cell_style),
            Paragraph(escape(row['action']), cell_style),
            Paragraph(escape(row['objet']), cell_style),
            Paragraph(escape(row['details']) if row['details'] else '-', cell_style)
        ])
        
    col_widths = [2.5*cm, 1.5*cm, 4.0*cm, 3.0*cm, 6.5*cm, 10.0*cm]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F3B73')), # En-tête Bleu
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F4F6F9')]), # Zebra
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1F3B73')), # Ligne forte sous header
    ]))
    
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"Rapport_{sanitize_filename_report(metadata['etablissement'])}_{date.today().strftime('%Y%m%d')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


# ============================================================
# GÉNÉRATEUR EXCEL (DESIGN TABLEAU DE BORD)
# ============================================================

def generer_rapport_excel(data, metadata):
    wb = Workbook()
    ws = wb.active
    ws.title = "Activité"
    
    # --- STYLES ---
    # Titre
    font_titre = Font(name='Segoe UI', size=18, bold=True, color="1F3B73")
    
    # En-têtes Tableau
    fill_header = PatternFill(start_color="1F3B73", end_color="1F3B73", fill_type="solid")
    font_header = Font(name='Segoe UI', size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")
    
    # Données
    font_data = Font(name='Segoe UI', size=10)
    align_top = Alignment(vertical="top", wrap_text=True)
    border_thin = Border(left=Side(style='thin', color='D9D9D9'), 
                         right=Side(style='thin', color='D9D9D9'), 
                         bottom=Side(style='thin', color='D9D9D9'))

    # --- MISE EN PAGE ---
    
    # 1. Titre et Logo (Simulé par emoji pour Excel)
    ws.merge_cells('A1:F1')
    ws['A1'] = f"📊 RAPPORT D'ACTIVITÉ - {metadata['etablissement']}"
    ws['A1'].font = font_titre
    ws['A1'].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 40
    
    # 2. Métadonnées (Cadre gris clair)
    ws.merge_cells('A2:F4')
    meta_text = (f"Période : {metadata['periode']}\n"
                 f"Généré le : {metadata['date_generation']}\n"
                 f"Total : {metadata['total']} enregistrements")
    
    ws['A2'] = meta_text
    ws['A2'].font = Font(name='Segoe UI', size=10, italic=True, color="555555")
    ws['A2'].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws['A2'].fill = PatternFill(start_color="F8F9FA", fill_type="solid")
    ws.row_dimensions[2].height = 60 # Hauteur pour les 3 lignes
    
    # 3. En-têtes du tableau (Ligne 6)
    headers = ["Date", "Heure", "Utilisateur", "Action", "Objet", "Détails"]
    ws.append([]) # Ligne 5 vide
    ws.append(headers) # Ligne 6
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=6, column=col_num)
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = align_center
    
    ws.row_dimensions[6].height = 30
    
    # 4. Données
    for row in data:
        ws.append([
            row['date'],
            row['heure'],
            sanitize_for_excel_report(row['utilisateur']),
            sanitize_for_excel_report(row['action']),
            sanitize_for_excel_report(row['objet']),
            sanitize_for_excel_report(row['details']) if row['details'] else '-'
        ])
        
    # 5. Finitions (Bordures et Largeurs)
    # Largeurs optimisées
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 10
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 18
    ws.column_dimensions['E'].width = 35
    ws.column_dimensions['F'].width = 60
    
    # Appliquer styles aux données
    for row in ws.iter_rows(min_row=7, max_row=ws.max_row):
        for cell in row:
            cell.font = font_data
            cell.alignment = align_top
            cell.border = border_thin
            
    # Filtres automatiques
    ws.auto_filter.ref = f"A6:F{ws.max_row}"
    
    # Figer les volets
    ws.freeze_panes = "A7"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"Rapport_{sanitize_filename_report(metadata['etablissement'])}_{date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ============================================================
# GÉNÉRATEURS INVENTAIRE (PDF/EXCEL)
# ============================================================

def generer_inventaire_pdf(data, metadata):
    """Génère un PDF propre de l'inventaire complet (Paysage)."""
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.0*cm, leftMargin=1.0*cm, topMargin=1.0*cm, bottomMargin=1.0*cm,
        title=f"Inventaire - {metadata['etablissement']}"
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # --- EN-TÊTE (Réutilisation du style Rapport) ---
    logo = LogoGraphique(width=40, height=40) # Utilise la classe existante
    
    titre_style = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#1F3B73'), alignment=TA_LEFT)
    sous_titre_style = ParagraphStyle('SousTitre', parent=styles['Normal'], fontSize=12, textColor=colors.gray, alignment=TA_LEFT)
    
    titre_bloc = [
        Paragraph(f"ÉTAT DE L'INVENTAIRE", titre_style),
        Paragraph(f"{escape(metadata['etablissement'])}", sous_titre_style)
    ]
    
    header_table = Table([[logo, titre_bloc]], colWidths=[1.5*cm, 20*cm])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elements.append(header_table)
    
    elements.append(Spacer(1, 0.5*cm))
    
    # --- INFO BARRE ---
    info_text = f"<b>Généré le :</b> {metadata['date_generation']}  |  <b>Total références :</b> {metadata['total']}"
    elements.append(Paragraph(info_text, ParagraphStyle('Info', parent=styles['Normal'], fontSize=10, alignment=TA_RIGHT, textColor=colors.HexColor('#1F3B73'))))
    elements.append(Spacer(1, 0.3*cm))

    # --- TABLEAU ---
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9, textColor=colors.black)
    cell_center = ParagraphStyle('CellCenter', parent=cell_style, alignment=TA_CENTER)
    
    headers = [
        Paragraph('Catégorie', header_style),
        Paragraph('Désignation', header_style),
        Paragraph('Qté', header_style),
        Paragraph('Seuil', header_style),
        Paragraph('Emplacement', header_style),
        Paragraph('Péremption', header_style)
    ]
    
    table_data = [headers]
    
    for row in data:
        # Alerte visuelle pour le stock bas (Rouge si Qté <= Seuil)
        qty_style = cell_center
        if row['quantite'] <= row['seuil']:
            qty_style = ParagraphStyle('Alert', parent=cell_center, textColor=colors.red, fontName='Helvetica-Bold')

        table_data.append([
            Paragraph(escape(row['categorie']), cell_style),
            Paragraph(escape(row['nom']), cell_style),
            Paragraph(str(row['quantite']), qty_style),
            Paragraph(str(row['seuil']), cell_center),
            Paragraph(escape(row['armoire']), cell_style),
            Paragraph(row['peremption'], cell_center)
        ])
    
    # Largeurs optimisées pour Paysage (Total ~27.5cm)
    col_widths = [
        5.0*cm,  # Catégorie
        9.5*cm,  # Nom (Large)
        2.0*cm,  # Qté
        2.0*cm,  # Seuil
        5.0*cm,  # Armoire
        4.0*cm   # Péremption
    ]
    
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F3B73')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F4F6F9')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1F3B73')),
    ]))
    
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"Inventaire_{sanitize_filename_report(metadata['etablissement'])}_{date.today().strftime('%Y%m%d')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


def generer_inventaire_excel(data, metadata):
    """Génère un Excel propre de l'inventaire."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventaire"
    
    # Styles
    font_titre = Font(name='Segoe UI', size=16, bold=True, color="1F3B73")
    fill_header = PatternFill(start_color="1F3B73", end_color="1F3B73", fill_type="solid")
    font_header = Font(name='Segoe UI', size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")
    border_thin = Border(left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9'))
    font_alert = Font(color="DC3545", bold=True) # Rouge pour stock bas

    # 1. En-tête
    ws.merge_cells('A1:F1')
    ws['A1'] = f"📦 ÉTAT DE L'INVENTAIRE - {metadata['etablissement']}"
    ws['A1'].font = font_titre
    ws['A1'].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 35
    
    ws['A2'] = f"Généré le : {metadata['date_generation']}"
    ws['A2'].font = Font(italic=True, color="666666")
    
    # 2. Tableau
    headers = ["Catégorie", "Désignation", "Quantité", "Seuil", "Emplacement", "Péremption"]
    ws.append([])
    ws.append(headers) # Ligne 4
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num)
        cell.value = header
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = align_center
    
    ws.row_dimensions[4].height = 30
    
    # 3. Données
    for row in data:
        ws.append([
            row['categorie'],
            row['nom'],
            row['quantite'],
            row['seuil'],
            row['armoire'],
            row['peremption']
        ])
        
        current_row = ws.max_row
        
        # Style des cellules
        for col in range(1, 7):
            cell = ws.cell(row=current_row, column=col)
            cell.border = border_thin
            cell.alignment = Alignment(vertical="center")
            
            # Centrer Qté, Seuil, Date
            if col in [3, 4, 6]:
                cell.alignment = align_center
                
        # Alerte Stock Bas (Rouge)
        if row['quantite'] <= row['seuil']:
            ws.cell(row=current_row, column=3).font = font_alert

    # 4. Largeurs
    ws.column_dimensions['A'].width = 25 # Cat
    ws.column_dimensions['B'].width = 40 # Nom
    ws.column_dimensions['C'].width = 12 # Qté
    ws.column_dimensions['D'].width = 12 # Seuil
    ws.column_dimensions['E'].width = 25 # Armoire
    ws.column_dimensions['F'].width = 15 # Date
    
    # Filtres
    ws.auto_filter.ref = f"A4:F{ws.max_row}"
    ws.freeze_panes = "A5"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"Inventaire_{sanitize_filename_report(metadata['etablissement'])}_{date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')