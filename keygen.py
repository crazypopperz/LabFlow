import tkinter as tk
from tkinter import messagebox
import hashlib

# =============================================================================
# CONFIGURATION
# =============================================================================
# C'est la clé qui est dans ton fichier .env (GMLCL_PRO_KEY)
# Elle doit être STRICTEMENT IDENTIQUE.
SECRET_KEY = "LABO-PRO-2025-X@v14211825!S@cha14211825!Quentin14211825!"

# =============================================================================
# LOGIQUE
# =============================================================================
def generer_cle():
    instance_id = entry_id.get().strip()
    
    if not instance_id:
        messagebox.showwarning("Attention", "Veuillez entrer un Identifiant d'Instance.")
        return

    try:
        # La formule magique (identique à celle de ton site)
        raw = f"{instance_id}-{SECRET_KEY}"
        cle = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
        
        # Affichage
        entry_result.config(state='normal') # On déverrouille pour écrire
        entry_result.delete(0, tk.END)
        entry_result.insert(0, cle)
        entry_result.config(state='readonly') # On reverrouille
        
        # Copie automatique dans le presse-papier
        root.clipboard_clear()
        root.clipboard_append(cle)
        lbl_info.config(text="Clé générée et copiée !", fg="green")
        
    except Exception as e:
        messagebox.showerror("Erreur", f"Une erreur est survenue : {e}")

def effacer():
    entry_id.delete(0, tk.END)
    entry_result.config(state='normal')
    entry_result.delete(0, tk.END)
    entry_result.config(state='readonly')
    lbl_info.config(text="Prêt", fg="grey")
    entry_id.focus()

# =============================================================================
# INTERFACE GRAPHIQUE
# =============================================================================
root = tk.Tk()
root.title("Générateur Licence LabFlow")
root.geometry("400x280")
root.resizable(False, False)
root.configure(bg="#f0f2f5")

# Style
font_label = ("Helvetica", 10, "bold")
font_entry = ("Courier New", 11)

# Titre
tk.Label(root, text="Générateur de Licence PRO", bg="#1f3b73", fg="white", font=("Helvetica", 14, "bold"), pady=10).pack(fill="x")

# Zone ID
frame_content = tk.Frame(root, bg="#f0f2f5", padx=20, pady=20)
frame_content.pack(fill="both", expand=True)

tk.Label(frame_content, text="Identifiant Instance (Client) :", bg="#f0f2f5", font=font_label).pack(anchor="w")
entry_id = tk.Entry(frame_content, font=font_entry, width=40, bd=2, relief="flat")
entry_id.pack(pady=(5, 15), ipady=5, fill="x")

# Bouton
btn_generate = tk.Button(frame_content, text="GÉNÉRER LA CLÉ", command=generer_cle, bg="#198754", fg="white", font=("Helvetica", 10, "bold"), cursor="hand2", relief="flat", pady=5)
btn_generate.pack(fill="x", pady=5)

# Zone Résultat
tk.Label(frame_content, text="Clé de Licence :", bg="#f0f2f5", font=font_label).pack(anchor="w", pady=(15, 0))
entry_result = tk.Entry(frame_content, font=("Courier New", 14, "bold"), width=40, bd=2, relief="solid", justify="center", state="readonly", fg="#1f3b73")
entry_result.pack(pady=5, ipady=5, fill="x")

# Info bas
lbl_info = tk.Label(frame_content, text="Entrez l'ID et cliquez sur Générer", bg="#f0f2f5", fg="grey")
lbl_info.pack(pady=5)

# Lancement
entry_id.focus()
root.bind('<Return>', lambda event: generer_cle()) # Touche Entrée pour valider
root.mainloop()