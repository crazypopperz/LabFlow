import os
import logging
import uuid
import re
from datetime import date, datetime
from typing import List, Dict, Any, TypedDict, TYPE_CHECKING
from werkzeug.utils import secure_filename

# ReportLab Imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Flowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from html import escape

if TYPE_CHECKING:
    from db import Objet

logger = logging.getLogger(__name__)

# --- CONFIGURATION TYPÉE (Point 3) ---
class DocumentConfig(TypedDict, total=False):
    color_primary: colors.Color
    color_secondary: colors.Color
    color_alert: colors.Color
    color_border: colors.Color
    max_items: int
    margins: float
    col_widths: List[float] # Point 4

DEFAULT_CONFIG: DocumentConfig = {
    'color_primary': colors.HexColor('#1F3B73'),
    'color_secondary': colors.HexColor('#F4F6F9'),
    'color_alert': colors.red,
    'color_border': colors.HexColor('#E0E0E0'),
    'max_items': 2000,
    'margins': 1.0 * cm,
    'col_widths': [9.0*cm, 6.0*cm, 6.0*cm, 3.0*cm, 3.0*cm] # Externalisé
}

class DocumentServiceError(Exception):
    """Erreur métier générique."""
    pass

class FileSystemError(DocumentServiceError):
    """Erreur I/O (Disque plein, permissions)."""
    pass

class LogoGraphique(Flowable):
    """Composant graphique vectoriel."""
    def __init__(self, width=40, height=40, primary_color=colors.blue):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.primary_color = primary_color

    def draw(self):
        self.canv.setFillColor(self.primary_color)
        self.canv.rect(0, 0, 8, 15, fill=1, stroke=0)
        self.canv.rect(12, 0, 8, 25, fill=1, stroke=0)
        self.canv.setFillColor(colors.HexColor('#4facfe'))
        self.canv.rect(24, 0, 8, 35, fill=1, stroke=0)
        self.canv.setStrokeColor(colors.HexColor('#FFD700'))
        self.canv.setLineWidth(2)
        self.canv.line(-5, 5, 35, 40)

class DocumentService:
    def __init__(self, upload_root: str, config: DocumentConfig = None):
        """
        :param upload_root: Chemin racine absolu pour les uploads (ex: .../static/uploads)
        """
        # Point 2 : Validation du chemin absolu
        if not os.path.isabs(upload_root):
            raise ValueError(f"upload_root doit être absolu. Reçu: {upload_root}")
            
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.upload_root = upload_root
        self.archive_folder = os.path.join(upload_root, 'archives')
        self._init_styles()

    def _init_styles(self):
        """Cache des styles (Point Performance)."""
        styles = getSampleStyleSheet()
        c_prim = self.config['color_primary']
        
        self.style_titre = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=22, textColor=c_prim, alignment=TA_LEFT)
        self.style_sous_titre = ParagraphStyle('SousTitre', parent=styles['Normal'], fontSize=12, textColor=colors.gray, alignment=TA_LEFT)
        self.style_header = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)
        self.style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9, textColor=colors.black)
        self.style_cell_center = ParagraphStyle('CellCenter', parent=self.style_cell, alignment=TA_CENTER)
        self.style_cell_danger = ParagraphStyle('CellDanger', parent=self.style_cell_center, textColor=self.config['color_alert'], fontName='Helvetica-Bold')
        self.style_stats = ParagraphStyle('Stats', parent=styles['Normal'], fontSize=10, alignment=TA_RIGHT, textColor=c_prim)

    def _generate_filename(self, etablissement_id: int, name: str, prefix: str = "Inventaire") -> str:
        safe_name = re.sub(r'[^\w\s-]', '', str(name)).strip().replace(' ', '_')
        safe_name = secure_filename(safe_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        unique_id = uuid.uuid4().hex[:8]
        return f"{prefix}_{etablissement_id}_{safe_name}_{timestamp}_{unique_id}.pdf"

    def generate_inventory_pdf(self, etablissement_name: str, etablissement_id: int, objets: List['Objet'], 
                             doc_title: str = "INVENTAIRE RÉGLEMENTAIRE", 
                             filename_prefix: str = "Inventaire") -> Dict[str, Any]:
        
        # Point 6 : Validation ID
        if not isinstance(etablissement_id, int) or etablissement_id <= 0:
            raise ValueError(f"etablissement_id invalide : {etablissement_id}")

        if not objets:
            raise DocumentServiceError("La liste d'objets est vide.")
        
        if len(objets) > self.config['max_items']:
            raise DocumentServiceError(f"Trop d'objets ({len(objets)}). Limite : {self.config['max_items']}.")

        try:
            # Point 7 : TOCTOU mitigation
            os.makedirs(self.archive_folder, exist_ok=True)
            
            # Utilisation du préfixe personnalisé
            filename = self._generate_filename(etablissement_id, etablissement_name, prefix=filename_prefix)
            full_path = os.path.join(self.archive_folder, filename)

            # Configuration Doc
            margin = self.config['margins']
            doc = SimpleDocTemplate(
                full_path,
                pagesize=landscape(A4),
                rightMargin=margin, leftMargin=margin,
                topMargin=margin, bottomMargin=margin,
                title=f"{filename_prefix} - {etablissement_name}",
                author="LabFlow",
                creator="LabFlow System"
            )

            elements = []

            # En-tête
            logo = LogoGraphique(width=40, height=40, primary_color=self.config['color_primary'])
            titre_bloc = [
                Paragraph(doc_title, self.style_titre), # Titre personnalisé
                Paragraph(f"Arrêté au {date.today().strftime('%d/%m/%Y')} - {escape(etablissement_name)}", self.style_sous_titre)
            ]
            header_table = Table([[logo, titre_bloc]], colWidths=[1.5*cm, 20*cm])
            header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            elements.append(header_table)
            elements.append(Spacer(1, 0.8*cm))

            # Données
            headers = [
                Paragraph('Désignation', self.style_header),
                Paragraph('Catégorie', self.style_header),
                Paragraph('Emplacement', self.style_header),
                Paragraph('Qté', self.style_header),
                Paragraph('CMR', self.style_header)
            ]
            
            table_data = [headers]
            total_cmr = 0

            for o in objets:
                is_cmr = getattr(o, 'is_cmr', False)
                nom = getattr(o, 'nom', 'Inconnu')
                qte = getattr(o, 'quantite_physique', 0)
                cat = getattr(o, 'categorie', None)
                arm = getattr(o, 'armoire', None)

                if is_cmr:
                    total_cmr += 1
                    cmr_display = Paragraph("OUI", self.style_cell_danger)
                else:
                    cmr_display = Paragraph("-", self.style_cell_center)

                table_data.append([
                    Paragraph(escape(nom), self.style_cell),
                    Paragraph(escape(cat.nom if cat else "-"), self.style_cell),
                    Paragraph(escape(arm.nom if arm else "-"), self.style_cell),
                    Paragraph(str(qte), self.style_cell_center),
                    cmr_display
                ])

            # Tableau
            t = Table(table_data, colWidths=self.config['col_widths'], repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.config['color_primary']),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.config['color_secondary']]),
                ('GRID', (0, 0), (-1, -1), 0.5, self.config['color_border']),
                ('LINEBELOW', (0, 0), (-1, 0), 2, self.config['color_primary']),
            ]))
            elements.append(t)

            # Pied de page
            elements.append(Spacer(1, 1*cm))
            stats_text = f"<b>Total références :</b> {len(objets)}  |  <b>Dont produits CMR :</b> {total_cmr}"
            elements.append(Paragraph(stats_text, self.style_stats))

            # Écriture Disque
            try:
                doc.build(elements)
            except Exception as e:
                raise DocumentServiceError(f"Erreur ReportLab lors de la génération: {e}") from e
            
            static_folder = os.path.dirname(self.upload_root)
            relative_path = os.path.relpath(full_path, static_folder)
            relative_path = relative_path.replace(os.sep, '/')

            return {
                "filename": filename,
                "relative_path": relative_path,
                "nb_objets": len(objets),
                "titre": f"{filename_prefix} {date.today().year} (v.{datetime.now().strftime('%H%M')})"
            }

        except (OSError, IOError) as e:
            logger.error(f"Erreur I/O PDF: {e}", exc_info=True)
            raise FileSystemError(f"Erreur d'écriture disque: {e.strerror}") from e
        except Exception as e:
            logger.error(f"Erreur inattendue PDF: {e}", exc_info=True)
            raise DocumentServiceError(f"Erreur technique inattendue: {type(e).__name__}") from e