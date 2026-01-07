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
	badge.classList.add('pulse-ring');
    if (!badge) return;

    try {
        const response = await fetch('/api/panier');
        if (response.ok) {
            const json = await response.json();
            const count = json.data.total || 0;

            // 1. Mise à jour du texte
            badge.textContent = count > 99 ? '99+' : count;
            
            // 2. Gestion de la visibilité (C'est ici que ça se joue)
            if (count > 0) {
                // S'il y a des articles, on affiche la pastille
                badge.style.display = 'flex';
                
                // Petite animation "Pulse" pour attirer l'attention lors d'un ajout
                badge.classList.remove('pulse'); // Reset pour rejouer l'anim
                void badge.offsetWidth; // Force le reflow (hack CSS)
                badge.classList.add('pulse');
            } else {
                // Si 0, on cache complètement la pastille
                badge.style.display = 'none';
            }
        }
    } catch (error) {
        console.error("Erreur synchro badge panier:", error);
    }
}

// Auto-update au chargement de la page si le script est importé
document.addEventListener('DOMContentLoaded', updateCartBadge);