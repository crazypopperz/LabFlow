// static/js/modules/cart-utils.js

// Protection XSS simple
export function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * Met à jour le badge du panier en interrogeant le serveur.
 * À appeler après chaque ajout/suppression.
 */
export async function updateCartBadge() {
    const badge = document.getElementById('cart-count-badge');
    if (!badge) return;

    badge.classList.add('pulse-ring');

    try {
        const response = await fetch('/api/panier');
        
        // Gestion des cas d'erreur (non connecté = HTML au lieu de JSON)
        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            // Redirigé vers login ou erreur → on cache le badge
            badge.textContent = '0';
            badge.style.display = 'none';
            return;
        }

        const json = await response.json();
        const count = json.data?.total || 0;

        // 1. Mise à jour du texte
        badge.textContent = count > 99 ? '99+' : count;
        
        // 2. Gestion de la visibilité
        if (count > 0) {
            badge.style.display = 'flex';
            
            // Petite animation "Pulse"
            badge.classList.remove('pulse');
            void badge.offsetWidth; // Force le reflow
            badge.classList.add('pulse');
        } else {
            badge.style.display = 'none';
        }
    } catch (error) {
        console.error("Erreur synchro badge panier:", error);
        // En cas d'erreur, on cache le badge silencieusement
        badge.textContent = '0';
        badge.style.display = 'none';
    }
}

// Auto-update au chargement de la page
document.addEventListener('DOMContentLoaded', updateCartBadge);