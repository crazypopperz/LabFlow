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
                recurrence: item.recurrence || null,
                items: []
            };
        }
        groups[key].items.push(item);
    });

    let html = '';

    Object.values(groups).forEach(group => {
        const dateObj = new Date(group.date + 'T00:00:00');
        const dateFr = dateObj.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });

        // --- Bloc recurrence ---
        let recurrenceHtml = '';
        if (group.recurrence) {
            const rec = group.recurrence;
            const labelsFreq = {
                'hebdo':           'Chaque semaine',
                'bi_hebdo':        'Toutes les deux semaines',
                'mensuel':         'Chaque mois',
                'quotidien_ouvre': 'Chaque jour ouvre'
            };
            const freqLabel = labelsFreq[rec.type] || rec.type;

            const occurrences = genererDatesRecurrence(
                group.date,
                rec.type,
                rec.date_fin || null,
                rec.nb_occurrences ? parseInt(rec.nb_occurrences) : null
            );

            let finLabel = '';
            if (rec.date_fin) {
                const finObj = new Date(rec.date_fin + 'T00:00:00');
                finLabel = `jusqu'au ${finObj.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })}`;
            } else if (rec.nb_occurrences) {
                finLabel = `${rec.nb_occurrences} occurrence(s) au total`;
            }

            const allDates = [group.date, ...occurrences];
            const occListItems = allDates.map((d, i) => {
                const dObj = new Date(d + 'T00:00:00');
                const dFr = dObj.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
                return `<li class="py-1 border-bottom border-light d-flex align-items-center gap-2">
                            <i class="bi bi-arrow-return-right text-muted small"></i>
                            <span class="${i === 0 ? 'fw-semibold text-primary' : 'text-muted'}">${dFr}</span>
                            ${i === 0 ? '<span class="badge bg-primary bg-opacity-10 text-primary ms-1" style="font-size:0.7rem;">Date de depart</span>' : ''}
                        </li>`;
            }).join('');

            const totalOcc = allDates.length;
            const listId = `occ-list-${group.date.replace(/-/g, '')}`;

            recurrenceHtml = `
                <div class="px-3 pb-2 pt-2">
                    <div class="rounded-2 border border-primary border-opacity-25 bg-primary bg-opacity-10 p-2">
                        <div class="d-flex align-items-center justify-content-between">
                            <div class="d-flex align-items-center gap-2 flex-wrap">
                                <i class="bi bi-arrow-repeat text-primary"></i>
                                <span class="fw-semibold text-primary small">${freqLabel}</span>
                                <span class="text-muted small">— ${finLabel}</span>
                            </div>
                            <button class="btn btn-link btn-sm text-primary p-0 toggle-occ-btn"
                                    type="button"
                                    data-target="${listId}"
                                    title="Voir les occurrences">
                                <i class="bi bi-chevron-down"></i>
                                <span class="small ms-1">${totalOcc} séance(s)</span>
                            </button>
                        </div>
                        <ul id="${listId}"
                            class="list-unstyled mb-0 mt-2 ps-1"
                            style="display:none; max-height:220px; overflow-y:auto;">
                            ${occListItems}
                        </ul>
                    </div>
                </div>`;
        }

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
                    ${recurrenceHtml}
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

    // Toggle liste occurrences
    document.querySelectorAll('.toggle-occ-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            const list = document.getElementById(targetId);
            const icon = btn.querySelector('i');
            if (list) {
                const isHidden = list.style.display === 'none';
                list.style.display = isHidden ? 'block' : 'none';
                icon.className = isHidden ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
            }
        });
    });

    // Suppression item
    document.querySelectorAll('.btn-delete-item').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const itemId = e.currentTarget.dataset.id;
            askConfirmation("Retirer cet élément du panier ?", () => deleteItem(itemId));
        });
    });
}

/**
 * Genere les dates d'occurrences recurrentes (sans la date de depart).
 * Miroir JS de panier_service.py::_generer_dates_recurrence()
 */
function genererDatesRecurrence(dateDebutStr, typeRec, dateFinStr, nbOccurrences) {
    const dates = [];
    let current = new Date(dateDebutStr + 'T00:00:00');
    const maxOcc = nbOccurrences ? nbOccurrences - 1 : 365;
    const dateFin = dateFinStr ? new Date(dateFinStr + 'T00:00:00') : null;

    while (dates.length < maxOcc) {
        current = new Date(current);
        if (typeRec === 'hebdo') {
            current.setDate(current.getDate() + 7);
        } else if (typeRec === 'bi_hebdo') {
            current.setDate(current.getDate() + 14);
        } else if (typeRec === 'mensuel') {
            const day = current.getDate();
            current.setMonth(current.getMonth() + 1);
            if (current.getDate() !== day) current.setDate(0);
        } else if (typeRec === 'quotidien_ouvre') {
            current.setDate(current.getDate() + 1);
            while (current.getDay() === 0 || current.getDay() === 6) {
                current.setDate(current.getDate() + 1);
            }
        } else {
            break;
        }

        if (dateFin && current > dateFin) break;

        const y = current.getFullYear();
        const m = String(current.getMonth() + 1).padStart(2, '0');
        const d = String(current.getDate()).padStart(2, '0');
        dates.push(`${y}-${m}-${d}`);
    }

    return dates;
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
					const count = json.data.reservations_count;
					const accord = count > 1 ? "s" : "";
					const conflits = json.data.conflits || [];
					if (conflits.length > 0) {
						const datesStr = conflits.map(d => new Date(d).toLocaleDateString('fr-FR')).join(', ');
						showToast(`${count} réservation${accord} créée${accord}. ⚠️ ${conflits.length} créneau(x) ignoré(s) : ${datesStr}`, "warning", 6000);
					} else {
						showToast(`Succès ! ${count} réservation${accord} créée${accord}.`, "success");
					}
					setTimeout(() => {
						window.location.href = '/calendrier';
					}, conflits.length > 0 ? 6000 : 1500);
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