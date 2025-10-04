import socket
from app import app
# from waitress import serve

def get_local_ip():
    """
    Tente de trouver l'adresse IP locale de la machine sur le réseau.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Cette IP n'a pas besoin d'être joignable, c'est une astuce
        # pour que le système d'exploitation choisisse la bonne interface réseau.
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        # Si la machine n'est connectée à aucun réseau, on retourne l'adresse
        # de boucle locale par défaut.
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == "__main__":
    # Configuration du serveur
    host = '0.0.0.0'  # Écoute sur toutes les interfaces réseau disponibles
    port = 5000
    local_ip = get_local_ip()
    
    # Affichage des informations pour l'administrateur
    print("="*60)
    print("          Serveur GMLCL Démarré")
    print("="*60)
    print("\nL'application est maintenant accessible aux adresses suivantes :")
    print(f"  - Depuis cet ordinateur : http://127.0.0.1:{port}")
    print(f"  - Depuis un autre PC du réseau : http://{local_ip}:{port}")
    print("\nIMPORTANT :")
    print("  - NE FERMEZ PAS CETTE FENÊTRE !")
    print("  - Pour arrêter le serveur, fermez cette fenêtre ou faites Ctrl+C.")
    print("="*60)
    
    # Lancement du serveur de production waitress
    # serve(app, host=host, port=port)
    app.run(host=host, port=port, debug=True)
