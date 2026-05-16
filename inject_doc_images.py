#!/usr/bin/env python3
# inject_doc_images.py
# Injecte les captures Cloudinary dans documentation.html

DOC_IMAGES = {
    'admin_dashboard': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778446992/scientral/doc/admin_dashboard.png',
    'admin_utilisateurs': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778446993/scientral/doc/admin_utilisateurs.png',
    'alertes_page': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778446994/scientral/doc/alertes_page.png',
    'armoires_liste': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778446995/scientral/doc/armoires_liste.png',
    'budget_page': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778446996/scientral/doc/budget_page.png',
    'calendrier_mois': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778446996/scientral/doc/calendrier_mois.png',
    'categories_liste': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778446997/scientral/doc/categories_liste.png',
    'inventaire_fiche': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778446998/scientral/doc/inventaire_fiche.png',
    'inventaire_liste': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778446998/scientral/doc/inventaire_liste.png',
    'panier': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778446999/scientral/doc/panier.png',
    'securite_liste': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778447000/scientral/doc/securite_liste.png',
    'vue_jour': 'https://res.cloudinary.com/dp0w3aqcq/image/upload/v1778447001/scientral/doc/vue_jour.png',
}

IMG_STYLE = 'style="width:100%;border-radius:10px;border:1px solid #e2e8f0;box-shadow:0 4px 12px rgba(0,0,0,0.08);margin:1rem 0;"'

def img(key, alt):
    url = DOC_IMAGES.get(key, '')
    return f'<img src="{url}" alt="{alt}" {IMG_STYLE} loading="lazy">\n'

content = open('templates/documentation.html', encoding='utf-8').read()

# ── INVENTAIRE ──────────────────────────────────────────────
old1 = '                    <!-- Étapes clés -->\n                <div class="doc-steps mb-4">'
new1 = f'                    {img("inventaire_liste", "Liste générale des objets")}\n                    <!-- Étapes clés -->\n                <div class="doc-steps mb-4">'
content = content.replace(old1, new1) if old1 in content else content

# Après accordion armoires
old2 = '                    <div class="accordion doc-accordion" id="accInventaire">'
new2 = f'                    <div class="row g-3 mb-4">\n                        <div class="col-md-6">{img("armoires_liste", "Gestion des armoires")}</div>\n                        <div class="col-md-6">{img("categories_liste", "Gestion des catégories")}</div>\n                    </div>\n                    <div class="accordion doc-accordion" id="accInventaire">'
content = content.replace(old2, new2) if old2 in content else content

# Fiche objet après accordion
old3 = '            </section>\n\n\n            <!-- ─────────────────────────────────────\n                 3. RÉSERVATIONS'
new3 = f'                    {img("inventaire_fiche", "Fiche détail d\'un objet")}\n            </section>\n\n\n            <!-- ─────────────────────────────────────\n                 3. RÉSERVATIONS'
content = content.replace(old3, new3) if old3 in content else content

# ── RÉSERVATIONS ─────────────────────────────────────────────
old4 = '                <div class="doc-steps mb-4">\n                    <div class="doc-step">\n                        <div class="doc-step-number" style="background:#7c3aed;">1</div>'
new4 = f'                {img("calendrier_mois", "Calendrier de réservation")}\n                <div class="doc-steps mb-4">\n                    <div class="doc-step">\n                        <div class="doc-step-number" style="background:#7c3aed;">1</div>'
content = content.replace(old4, new4) if old4 in content else content

old5 = '                <div class="doc-tip">\n                    <i class="bi bi-info-circle-fill text-primary me-2"></i>'
new5 = f'                {img("panier", "Panier de réservation")}\n                {img("vue_jour", "Vue du jour")}\n                <div class="doc-tip">\n                    <i class="bi bi-info-circle-fill text-primary me-2"></i>'
content = content.replace(old5, new5, 1) if old5 in content else content

# ── SÉCURITÉ ─────────────────────────────────────────────────
old6 = '                <div class="alert doc-alert-danger">'
new6 = f'                {img("securite_liste", "Liste des équipements de sécurité")}\n                <div class="alert doc-alert-danger">'
content = content.replace(old6, new6) if old6 in content else content

# ── BUDGET ───────────────────────────────────────────────────
old7 = '                <div class="row g-3 mb-4">\n                    <div class="col-12">\n                        <div class="card border-0 shadow-sm">'
new7 = f'                {img("budget_page", "Page de suivi budgétaire")}\n                <div class="row g-3 mb-4">\n                    <div class="col-12">\n                        <div class="card border-0 shadow-sm">'
content = content.replace(old7, new7) if old7 in content else content

# ── ALERTES ──────────────────────────────────────────────────
old8 = '                <div class="row g-3 mb-4">\n                    <div class="col-md-6">\n                        <div class="doc-feature-card h-100">\n                            <div class="doc-feature-icon" style="background:#fef3c7'
new8 = f'                {img("alertes_page", "Page des alertes et suggestions")}\n                <div class="row g-3 mb-4">\n                    <div class="col-md-6">\n                        <div class="doc-feature-card h-100">\n                            <div class="doc-feature-icon" style="background:#fef3c7'
content = content.replace(old8, new8) if old8 in content else content

# ── ADMIN ────────────────────────────────────────────────────
old9 = '                <div class="row g-4 mb-4">\n                    <div class="col-md-6">\n                        <div class="card border-0 shadow-sm h-100">\n                            <div class="card-body">\n                                <h5 class="fw-bold text-primary mb-3">'
new9 = f'                {img("admin_dashboard", "Panneau d\'administration")}\n                {img("admin_utilisateurs", "Gestion des utilisateurs")}\n                <div class="row g-4 mb-4">\n                    <div class="col-md-6">\n                        <div class="card border-0 shadow-sm h-100">\n                            <div class="card-body">\n                                <h5 class="fw-bold text-primary mb-3">'
content = content.replace(old9, new9) if old9 in content else content

open('templates/documentation.html', 'w', encoding='utf-8').write(content)
print("OK — images injectées dans documentation.html")
