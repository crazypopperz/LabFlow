// static/js/modules/cart-summary.js
import { showToast } from './toast.js';
import { updateCartBadge, escapeHtml } from './cart-utils.js';

// --- GESTION MODALE ---
let cartModalInstance = null;
let pendingAction = null; // Stocke la fonction à exécuter après confirmation
const modalMessageEl = document.getElementById('cartModalMessage');

document.addEventListener('DOMContentLoaded', () => {
    // Init Modale
    const modalEl = document.getElementById('cartActionModal');
    if (modalEl) {
        cartModalInstance = new bootstrap.Modal(modalEl);
        const confirmBtn = document.getElementById('btnConfirmCartAction');
        
        // Clic sur "Confirmer" dans la modale
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                if (pendingAction) pendingAction(); // Exécute l'action stockée
                if (cartModalInstance) cartModalInstance.hide();
            });
        }
    }

    loadServerCart();
    setupGlobalActions();
});

// Références DOM
const container = document.getElementById('cart-items-container');
const emptyState = document.getElementById('empty-cart-message');
const actionsBar = document.getElementById('cart-actions');
const btnConfirm = document.getElementById('confirm-cart-btn');
const btnClear = document.getElementById('clear-cart-btn');

/**
 * Charge le panier depuis l'API
 */
async function loadServerCart() {
    if (!container) return;

    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2 text-muted">Chargement de votre panier...</p>
        </div>`;

    try {
        const response = await fetch('/api/panier');
        const json = await response.json();

        if (!json.success || !json.data.items || json.data.items.length === 0) {
            showEmptyState();
            return;
        }

        renderCartItems(json.data.items);
        updateCartBadge();

    } catch (error) {
        console.error(error);
        container.innerHTML = `<div class="alert alert-danger">Impossible de charger le panier.</div>`;
    }
}

function showEmptyState() {
    if (container) container.innerHTML = '';
    if (emptyState) emptyState.style.display = 'block';
    if (actionsBar) actionsBar.style.display = 'none';
    updateCartBadge();
}

function renderCartItems(items) {
    const groups = {};
    
    items.forEach(item => {
        const key = `${item.date}_${item.heure_debut}_${item.heure_fin}`;
        if (!groups[key]) {
            groups[key] = {
                date: item.date,
                start: item.heure_debut,
                end: item.heure_fin,
                items: []
            };
        }
        groups[key].items.push(item);
    });

    let html = '';
    
    Object.values(groups).forEach(group => {
        const dateObj = new Date(group.date);
        const dateFr = dateObj.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });

        html += `
            <div class="card mb-3 border-0 shadow-sm overflow-hidden">
                <div class="card-header bg-light d-flex justify-content-between align-items-center py-3">
                    <div>
                        <strong class="text-primary text-capitalize"><i class="bi bi-calendar-event me-2"></i>${dateFr}</strong>
                        <span class="mx-2 text-muted">|</span>
                        <span class="fw-bold text-dark">${group.start} - ${group.end}</span>
                    </div>
                </div>
                <div class="card-body p-0">
                    <ul class="list-group list-group-flush">
        `;

        group.items.forEach(item => {
            const badge = item.type === 'kit' 
                ? '<span class="badge bg-info text-dark me-2">KIT</span>' 
                : '<span class="badge bg-secondary me-2">OBJET</span>';

            html += `
                <li class="list-group-item d-flex justify-content-between align-items-center py-3">
                    <div class="d-flex align-items-center">
                        ${badge}
                        <span class="fw-medium">${escapeHtml(item.nom)}</span>
                    </div>
                    <div class="d-flex align-items-center gap-3">
                        <span class="fw-bold fs-5">x${item.quantite}</span>
                        <button class="btn btn-sm btn-outline-danger border-0 btn-delete-item" 
                                data-id="${item.id}" 
                                title="Retirer">
                            <i class="bi bi-trash-fill"></i>
                        </button>
                    </div>
                </li>
            `;
        });

        html += `</ul></div></div>`;
    });

    container.innerHTML = html;
    
    if (emptyState) emptyState.style.display = 'none';
    if (actionsBar) actionsBar.style.display = 'flex';

    // Events Suppression Item
    document.querySelectorAll('.btn-delete-item').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const itemId = e.currentTarget.dataset.id;
            askConfirmation("Retirer cet élément du panier ?", () => deleteItem(itemId));
        });
    });
}

/**
 * Ouvre la modale de confirmation
 */
function askConfirmation(message, actionCallback) {
    if (cartModalInstance) {
        if (modalMessageEl) modalMessageEl.textContent = message;
        pendingAction = actionCallback;
        cartModalInstance.show();
    } else {
        // Fallback si modale pas trouvée (ne devrait pas arriver)
        if (confirm(message)) actionCallback();
    }
}

async function deleteItem(itemId) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    try {
        const res = await fetch(`/api/panier/retirer/${itemId}`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': csrfToken }
        });

        if (res.ok) {
            showToast("Élément retiré", "info");
            loadServerCart();
        } else {
            showToast("Erreur lors de la suppression", "error");
        }
    } catch (err) {
        console.error(err);
        showToast("Erreur technique", "error");
    }
}

function setupGlobalActions() {
    // 1. Vider le panier
    if (btnClear) {
        btnClear.addEventListener('click', () => {
            askConfirmation("Voulez-vous vraiment vider tout votre panier ?", async () => {
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
                try {
                    const res = await fetch('/api/panier', {
                        method: 'DELETE',
                        headers: { 'X-CSRFToken': csrfToken }
                    });
                    if (res.ok) {
                        showToast("Panier vidé", "info");
                        showEmptyState();
                    }
                } catch (err) {
                    showToast("Erreur technique", "error");
                }
            });
        });
    }

    // 2. Valider (Checkout)
    if (btnConfirm) {
        btnConfirm.addEventListener('click', async () => {
            const originalText = btnConfirm.innerHTML;
            btnConfirm.disabled = true;
            btnConfirm.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Validation...';

            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

            try {
                const res = await fetch('/api/panier/checkout', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken 
                    }
                });

                const json = await res.json();

                if (res.ok && json.success) {
                    showToast(`Succès ! ${json.data.reservations_count} réservations créées.`, "success");
                    setTimeout(() => {
                        window.location.href = '/calendrier';
                    }, 1500);
                } else {
                    showToast(json.error || "Erreur lors de la validation", "error");
                    btnConfirm.disabled = false;
                    btnConfirm.innerHTML = originalText;
                    loadServerCart();
                }
            } catch (err) {
                console.error(err);
                showToast("Erreur technique critique", "error");
                btnConfirm.disabled = false;
                btnConfirm.innerHTML = originalText;
            }
        });
    }
}