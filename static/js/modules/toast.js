/**
 * Affiche une notification (toast) Bootstrap 5.
 * Crée dynamiquement le conteneur de toasts s'il n'existe pas.
 * @param {string} message Le message à afficher.
 * @param {string} type Le type de toast ('success', 'danger', 'warning', 'info'). Par défaut 'info'.
 */
export function showToast(message, type = 'info') {
    // Crée le conteneur de toasts s'il n'est pas déjà dans la page
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        // CORRECTION : "end-0" a été remplacé par "start-0" pour positionner à gauche.
        toastContainer.className = 'toast-container position-fixed top-0 start-0 p-3';
        toastContainer.style.zIndex = 1090; // S'assurer qu'il est au-dessus des modales
        document.body.appendChild(toastContainer);
    }

    // Détermine la couleur du toast en fonction du type
    const toastClassMap = {
        success: 'text-bg-success',
        danger: 'text-bg-danger',
        warning: 'text-bg-warning',
        info: 'text-bg-info',
    };
    // Pour le message de déconnexion, on utilise le bleu principal
    if (type === 'logout') {
        toastClassMap.logout = 'text-bg-primary';
    }
    const toastClass = toastClassMap[type] || 'text-bg-secondary';

    // Crée l'élément toast
    const toastElement = document.createElement('div');
    toastElement.className = `toast align-items-center ${toastClass} border-0`;
    toastElement.setAttribute('role', 'alert');
    toastElement.setAttribute('aria-live', 'assertive');
    toastElement.setAttribute('aria-atomic', 'true');

    toastElement.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    // Ajoute le toast au conteneur et l'affiche
    toastContainer.appendChild(toastElement);

    const toast = new bootstrap.Toast(toastElement, {
        delay: 2000 // Disparaît après 3 secondes
    });

    // Supprime l'élément du DOM après sa disparition pour garder la page propre
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });

    toast.show();
}