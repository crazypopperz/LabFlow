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

    try {
        const response = await fetch('/api/panier');
        if (response.ok) {
            const json = await response.json();
            // L'API retourne { success: true, data: { items: [], total: X } }
            const count = json.data.total || 0;

            badge.textContent = count > 99 ? '99+' : count;
            
            if (count > 0) {
                badge.style.display = 'flex';
                badge.classList.add('pulse');
                // On retire l'anim après 1s
                setTimeout(() => badge.classList.remove('pulse'), 1000);
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (error) {
        console.error("Erreur synchro badge panier:", error);
    }
}

// Auto-update au chargement de la page si le script est importé
document.addEventListener('DOMContentLoaded', updateCartBadge);