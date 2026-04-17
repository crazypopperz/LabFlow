import re

with open('templates/admin_fournisseurs.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r"<!-- Modale Ajout/Modification -->.*?(?=<!-- Modale Suppression)", "", content, flags=re.DOTALL)
content = re.sub(r"<!-- Modale Suppression Spécifique -->.*?(?=\{% endblock %\})", "", content, flags=re.DOTALL)

includes = "{% include '_modale_fournisseur_add.html' %}\n{% include '_modale_fournisseur_edit.html' %}\n\n"
content = content.replace("\n{% endblock %}\n\n{% block scripts %}", "\n" + includes + "{% endblock %}\n\n{% block scripts %}")

content = content.replace('data-bs-target="#fournisseurModal" onclick="resetModal()"', 'data-bs-target="#addFournisseurModal"')

with open('templates/admin_fournisseurs.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Script 1 OK")
