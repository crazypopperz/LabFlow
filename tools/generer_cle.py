import hashlib
import sys

# C'est TA clé secrète (copiée depuis ton .env)
# Elle doit être IDENTIQUE à celle du fichier .env sinon ça ne marchera pas
SECRET_KEY = "LABO-PRO-2025-X@v14211825!S@cha14211825!Quentin14211825!"

def generate(instance_id):
    # On colle l'ID et le Secret
    raw = f"{instance_id}-{SECRET_KEY}"
    # On mélange le tout (Hash) et on prend les 16 premiers caractères
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

if __name__ == "__main__":
    print("\n--- GÉNÉRATEUR DE LICENCE LABFLOW ---")
    
    # Si l'ID est passé en argument ou demandé
    if len(sys.argv) > 1:
        iid = sys.argv[1]
    else:
        iid = input("Collez l'Identifiant d'Instance ici : ").strip()
    
    if iid:
        cle = generate(iid)
        print(f"\nPOUR L'INSTANCE : {iid}")
        print(f"LA CLÉ EST      : {cle}")
        print("-" * 40)
    else:
        print("Erreur : ID manquant.")