from waitress import serve
from app import app # NOTE: On importe 'app', pas 'create_app'
import socket

port = 5000

def get_network_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == '__main__':
    network_ip = get_network_ip()
    print("="*70)
    print("===== Serveur de l'Application GestionLabo Démarré =====")
    print(f"1. Pour VOUS (administrateur), utilisez : http://127.0.0.1:{port}")
    print(f"2. Pour les AUTRES utilisateurs, donnez-leur : http://{network_ip}:{port}")
    print("="*70)
    serve(app, host='0.0.0.0', port=port)