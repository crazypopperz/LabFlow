// static/js/modules/booking-modal.js
import { showToast } from './toast.js';
import { updateCartBadge } from './cart-utils.js';

const bookingModalElement = document.getElementById('bookingModal');
let bookingModalInstance = null;

let modalTitle, dateInput, startTimeSelect, endTimeSelect;
let availableItemsContainer, bookingCartContainer, validateBtn, cancelBtn;
let editingGroupId = null;

// Gestion Modale "Dernier Item"
let lastItemModalInstance = null;
let pendingDelete = null;

export function initBookingModal() {
    if (!bookingModalElement) return;

    modalTitle = bookingModalElement.querySelector('.modal-title');
    dateInput = document.getElementById('bookingDate');
    startTimeSelect = document.getElementById('startTime');
    endTimeSelect = document.getElementById('endTime');
    availableItemsContainer = document.getElementById('availableItems');
    bookingCartContainer = document.getElementById('bookingCart');
    validateBtn = document.getElementById('validateBookingBtn');
    cancelBtn = bookingModalElement.querySelector('.modal-footer .btn-secondary');

    // Init Modale Warning
    const warningEl = document.getElementById('lastItemWarningModal');
    if (warningEl) {
        lastItemModalInstance = new bootstrap.Modal(warningEl);
        const confirmBtn = document.getElementById('btnConfirmLastItemDelete');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                if (pendingDelete) {
                    performRemoveItem(pendingDelete.id, pendingDelete.type);
                    lastItemModalInstance.hide();
                    pendingDelete = null;
                }
            });
        }
    }

    bookingModalElement.addEventListener('show.bs.modal', handleModalOpen);
    
    // CORRECTION : Nettoyage forcé à la fermeture
    bookingModalElement.addEventListener('hidden.bs.modal', () => {
        resetModalState();
        forceCleanup(); 
    });

    if (startTimeSelect) startTimeSelect.addEventListener('change', handleTimeChange);
    if (endTimeSelect) endTimeSelect.addEventListener('change', loadAvailabilities);

    setupDelegatedEvents();
}

export function openReservationModal(date, groupId = null) {
    if (!bookingModalElement) return;
    bookingModalElement.dataset.date = date;
    if (groupId) bookingModalElement.dataset.groupId = groupId;
    else delete bookingModalElement.dataset.groupId;

    if (!bookingModalInstance) bookingModalInstance = new bootstrap.Modal(bookingModalElement);
    bookingModalInstance.show();
}

async function handleModalOpen(event) {
    const trigger = event.relatedTarget || bookingModalElement;
    const date = trigger.dataset.date;
    editingGroupId = trigger.dataset.groupId || null;

    if (!date) return;

    dateInput.value = date;
    const dateFr = new Date(date).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
    
    if (bookingCartContainer) bookingCartContainer.style.display = 'block';

    if (editingGroupId) {
        // --- MODE ÉDITION ---
        modalTitle.innerHTML = `<i class="bi bi-pencil-square me-2"></i>Modifier la réservation`;
        if (validateBtn) validateBtn.style.display = 'none';
        
        if (cancelBtn) {
            cancelBtn.textContent = "Fermer";
            cancelBtn.classList.remove('btn-secondary', 'btn-outline-secondary');
            cancelBtn.classList.add('btn-dark');
            
            // Reset du bouton pour comportement par défaut (fermeture)
            const newCancelBtn = cancelBtn.cloneNode(true);
            // Pas d'event listener spécifique, le data-bs-dismiss suffit
            cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
            cancelBtn = newCancelBtn;
        }
        await loadExistingReservation(editingGroupId);

    } else {
        // --- MODE CRÉATION ---
        modalTitle.innerHTML = `<i class="bi bi-calendar-check me-2"></i>Réserver pour le ${dateFr}`;
        
        if (validateBtn) {
            validateBtn.style.display = 'inline-block';
            validateBtn.innerHTML = '<i class="bi bi-cart-check me-2"></i>Voir mon panier';
            validateBtn.classList.remove('btn-primary', 'disabled');
            validateBtn.classList.add('btn-success');
            
            const newValidateBtn = validateBtn.cloneNode(true);
            newValidateBtn.type = 'button';
            newValidateBtn.disabled = false;
            newValidateBtn.onclick = (e) => { 
                e.preventDefault(); 
                window.location.href = '/panier'; 
            };
            validateBtn.parentNode.replaceChild(newValidateBtn, validateBtn);
            validateBtn = newValidateBtn;
        }

        // Bouton "Poursuivre"
        if (cancelBtn) {
            cancelBtn.innerHTML = '<i class="bi bi-calendar-week me-2"></i>Poursuivre (Calendrier)';
            cancelBtn.classList.remove('btn-dark', 'btn-secondary', 'btn-danger');
            cancelBtn.classList.add('btn-outline-secondary');
            
            const newCancelBtn = cancelBtn.cloneNode(true);
            newCancelBtn.type = 'button';
            
            newCancelBtn.onclick = (e) => {
                e.preventDefault();
                
                // Fermeture manuelle propre
                if (bookingModalInstance) bookingModalInstance.hide();
                else {
                    const instance = bootstrap.Modal.getInstance(bookingModalElement);
                    if (instance) instance.hide();
                }
                
                // Nettoyage forcé immédiat
                forceCleanup();

                // Redirection si nécessaire
                if (!window.location.pathname.includes('/calendrier')) {
                    window.location.href = '/calendrier';
                }
            };
            
            cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
            cancelBtn = newCancelBtn;
        }

        updateHourOptions(); 
        setSmartTime();      
        loadAvailabilities();
        refreshMiniCart();
    }
}

function resetModalState() {
    delete bookingModalElement.dataset.date;
    delete bookingModalElement.dataset.groupId;
    editingGroupId = null;
    availableItemsContainer.innerHTML = '';
    if (bookingCartContainer) bookingCartContainer.innerHTML = '';
}

/**
 * NETTOYAGE FORCÉ DU BACKDROP (CORRECTION BUG CHROME)
 * Supprime manuellement les éléments fantômes de Bootstrap
 */
function forceCleanup() {
    setTimeout(() => {
        // 1. Supprimer tous les backdrops restants
        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
        
        // 2. Restaurer le scroll du body
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    }, 150); // Petit délai pour laisser l'animation Bootstrap finir
}

// --- LOGIQUE MÉTIER ---

async function loadExistingReservation(groupId) {
    try {
        bookingCartContainer.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-muted"></div></div>';
        const response = await fetch(`/api/reservation_details/${groupId}`);
        if (!response.ok) throw new Error("Erreur chargement");
        const data = await response.json();

        if (data.debut && data.fin) {
            startTimeSelect.value = data.debut.substring(11, 16);
            endTimeSelect.value = data.fin.substring(11, 16);
        }

        renderMiniCart(data.items, false); 
        
        const startDt = new Date(data.debut);
        if (startDt < new Date()) {
            availableItemsContainer.innerHTML = `<div class="alert alert-warning"><i class="bi bi-clock-history me-2"></i>Réservation passée. Lecture seule.</div>`;
            renderMiniCart(data.items, true);
        } else {
            loadAvailabilities();
        }
    } catch (error) {
        console.error(error);
        bookingCartContainer.innerHTML = '<div class="text-danger">Erreur chargement</div>';
    }
}

function loadAvailabilities() {
    const date = dateInput.value;
    const start = startTimeSelect.value;
    const end = endTimeSelect.value;
    if (!date || !start || !end) return;

    availableItemsContainer.innerHTML = `<div class="text-center py-5"><div class="spinner-border text-primary mb-2"></div><p class="text-muted small">Vérification stocks...</p></div>`;

    let url = `/api/disponibilites?date=${date}&heure_debut=${start}&heure_fin=${end}`;
    fetch(url).then(res => res.json()).then(response => {
        if (!response.success) {
            availableItemsContainer.innerHTML = `<div class="alert alert-danger">${response.error}</div>`;
        } else {
            renderAvailableItems(response.data);
        }
    }).catch(() => availableItemsContainer.innerHTML = `<div class="alert alert-danger">Erreur connexion.</div>`);
}

async function refreshMiniCart() {
    if (!bookingCartContainer) return;
    bookingCartContainer.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-muted"></div></div>';
    try {
        const res = await fetch('/api/panier');
        const json = await res.json();
        if (json.success && json.data.items.length > 0) renderMiniCart(json.data.items, false);
        else bookingCartContainer.innerHTML = '<div class="text-muted fst-italic text-center mt-3">Votre panier est vide.</div>';
    } catch (e) { bookingCartContainer.innerHTML = '<div class="text-danger small">Erreur panier</div>'; }
}

// --- ACTIONS ---

async function addItem(item) {
    const payload = { type: item.type, id: item.id, quantite: 1 };
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    let url = '/api/panier/ajouter';
    if (editingGroupId) {
        url = `/api/reservation/${editingGroupId}/ajouter`;
    } else {
        payload.date = dateInput.value;
        payload.heure_debut = startTimeSelect.value;
        payload.heure_fin = endTimeSelect.value;
    }

    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok && data.success) {
            showToast(`Ajouté : ${item.nom}`, "success");
            updateCartBadge();
            loadAvailabilities();
            if (editingGroupId) loadExistingReservation(editingGroupId);
            else refreshMiniCart();
        } else {
            showToast(data.error || "Erreur", "error");
        }
    } catch (err) { showToast("Erreur technique", "error"); }
}

function requestRemoveItem(itemId, itemType, currentQty) {
    if (editingGroupId) {
        const itemsCount = document.querySelectorAll('#bookingCart li').length;
        if (itemsCount === 1 && currentQty <= 1) {
            pendingDelete = { id: itemId, type: itemType };
            if (lastItemModalInstance) {
                lastItemModalInstance.show();
            } else {
                if(confirm("Supprimer la réservation ?")) performRemoveItem(itemId, itemType);
            }
            return;
        }
    }
    performRemoveItem(itemId, itemType);
}

async function performRemoveItem(itemId, itemType) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    let url = `/api/panier/retirer/${itemId}`;
    if (editingGroupId) {
        url = `/api/reservation/${editingGroupId}/retirer/${itemId}?type=${itemType}`;
    }

    try {
        const res = await fetch(url, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': csrfToken }
        });
        const data = await res.json();

        if (res.ok) {
            showToast("Retiré", "info");
            updateCartBadge();
            
            if (editingGroupId && data.remaining_items === 0) {
                if (bookingModalInstance) bookingModalInstance.hide();
                forceCleanup(); // Nettoyage aussi ici
                window.location.reload();
                return;
            }

            loadAvailabilities();
            if (editingGroupId) loadExistingReservation(editingGroupId);
            else refreshMiniCart();
        }
    } catch (e) { console.error(e); }
}

// --- RENDU ---

function renderAvailableItems(data) {
    let html = '<div class="list-group list-group-flush">';
    const getImg = (img) => img ? (img.startsWith('http') ? img : `/static/${img}`) : null;
    
    const renderRow = (item, type, style) => {
        const dispo = item.disponible;
        const active = dispo > 0;
        const imgUrl = getImg(item.image);
        const imgHtml = imgUrl ? `<img src="${imgUrl}" class="rounded border" style="width:40px;height:40px;object-fit:cover;">` : `<div class="rounded bg-light d-flex align-items-center justify-content-center" style="width:40px;height:40px;"><i class="bi bi-box text-muted"></i></div>`;

        return `
            <div class="list-group-item d-flex justify-content-between align-items-center py-2 px-0 ${style}">
                <div class="d-flex align-items-center gap-2 overflow-hidden">
                    ${imgHtml}
                    <div class="text-truncate">
                        <div class="fw-bold text-dark text-truncate" title="${item.nom}">${item.nom}</div>
                        <div class="small text-muted">${item.armoire || ''}</div>
                    </div>
                </div>
                <div class="d-flex align-items-center gap-2 flex-shrink-0">
                    <span class="badge ${active ? 'bg-light text-dark border' : 'bg-danger-subtle text-danger'} rounded-pill">${dispo}</span>
                    <button type="button" class="btn btn-sm ${active ? 'btn-primary' : 'btn-secondary disabled'} btn-add-item" 
                            data-type="${type}" data-id="${item.id}" data-nom="${item.nom}" ${!active ? 'disabled' : ''}>
                        <i class="bi bi-plus-lg"></i>
                    </button>
                </div>
            </div>`;
    };

    if (data.objets?.length) {
        html += '<h6 class="mt-3 mb-2 text-muted small fw-bold">OBJETS</h6>';
        data.objets.forEach(o => html += renderRow(o, 'objet', ''));
    }
    if (data.kits?.length) {
        html += '<h6 class="mt-3 mb-2 text-muted small fw-bold">KITS</h6>';
        data.kits.forEach(k => html += renderRow(k, 'kit', 'bg-light border-start border-3 border-info ps-2'));
    }
    availableItemsContainer.innerHTML = html + '</div>';
}

function renderMiniCart(items, readOnly) {
    let html = '<ul class="list-group list-group-flush">';
    items.forEach(item => {
        const type = item.type || 'objet'; 
        const deleteBtn = readOnly ? '' : `<button class="btn btn-link text-danger p-0 btn-remove-item" data-id="${item.id}" data-type="${type}" data-qty="${item.quantite}"><i class="bi bi-dash-circle-fill"></i></button>`;
        
        html += `
            <li class="list-group-item d-flex justify-content-between align-items-center px-0 py-2">
                <div class="small lh-1">
                    <div class="fw-bold text-truncate" style="max-width: 140px;">${item.nom}</div>
                    ${item.heure_debut ? `<div class="text-muted" style="font-size:0.75rem;">${item.heure_debut}-${item.heure_fin}</div>` : ''}
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="badge bg-primary rounded-pill">x${item.quantite}</span>
                    ${deleteBtn}
                </div>
            </li>`;
    });
    bookingCartContainer.innerHTML = html + '</ul>';
}

function setupDelegatedEvents() {
    availableItemsContainer.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-add-item');
        if (!btn || btn.disabled) return;
        e.preventDefault();
        
        const original = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        btn.disabled = true;

        addItem({
            type: btn.dataset.type,
            id: parseInt(btn.dataset.id, 10),
            nom: btn.dataset.nom
        }).then(() => {
            btn.innerHTML = original;
            btn.disabled = false;
        });
    });

    if (bookingCartContainer) {
        bookingCartContainer.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-remove-item');
            if (!btn) return;
            e.preventDefault();
            const itemId = parseInt(btn.dataset.id, 10);
            const itemType = btn.dataset.type;
            const currentQty = parseInt(btn.dataset.qty, 10);
            
            requestRemoveItem(itemId, itemType, currentQty);
        });
    }
}

function handleTimeChange(event) {
    if (event.target === startTimeSelect) {
        const startHour = parseInt(startTimeSelect.value.split(':')[0]);
        const endHour = startHour + 1;
        if (endHour <= 18) {
            const newEndTime = `${String(endHour).padStart(2, '0')}:00`;
            const optionExists = [...endTimeSelect.options].some(o => o.value === newEndTime);
            if (optionExists) endTimeSelect.value = newEndTime;
        }
    }
    loadAvailabilities();
}

function updateHourOptions() {
    const now = new Date();
    const todayStr = now.toISOString().split('T')[0];
    if (dateInput.value === todayStr) {
        const currentHour = now.getHours();
        Array.from(startTimeSelect.options).forEach(opt => {
            const h = parseInt(opt.value.split(':')[0]);
            opt.disabled = (h <= currentHour);
        });
    } else {
        Array.from(startTimeSelect.options).forEach(opt => opt.disabled = false);
    }
}

function setSmartTime() {
    const now = new Date();
    const todayStr = now.toISOString().split('T')[0];

    if (dateInput.value === todayStr) {
        let currentHour = now.getHours();
        let targetHour = currentHour + 1;
        if (targetHour < 8) targetHour = 8;
        if (targetHour > 17) targetHour = 17;

        const startStr = `${String(targetHour).padStart(2, '0')}:00`;
        const endStr = `${String(targetHour + 1).padStart(2, '0')}:00`;

        const optionExists = [...startTimeSelect.options].some(o => o.value === startStr);
        if (optionExists) {
            startTimeSelect.value = startStr;
            endTimeSelect.value = endStr;
        }
    } else {
        startTimeSelect.value = "08:00";
        endTimeSelect.value = "09:00";
    }
}

document.addEventListener('DOMContentLoaded', initBookingModal);