// static/js/modules/booking-modal.js
import { showToast } from './toast.js';
import { updateCartBadge, escapeHtml } from './cart-utils.js';

const ERROR_MESSAGES = {
    CSRF_MISSING: 'Erreur de configuration de sécurité (CSRF)',
    NETWORK_ERROR: 'Erreur de connexion au serveur',
    LOADING_ERROR: 'Impossible de charger les données',
    CART_ERROR: 'Erreur lors de la mise à jour du panier',
    TECHNICAL_ERROR: 'Une erreur technique est survenue',
    AVAILABILITY_ERROR: 'Impossible de vérifier les disponibilités',
    INVALID_RESPONSE: 'Réponse serveur invalide'
};

// --- VARIABLES GLOBALES ---
const bookingModalElement = document.getElementById('bookingModal');
let bookingModalInstance = null;

// UI Elements
let modalTitle, dateInput, startHourSelect, startMinuteSelect, endHourSelect, endMinuteSelect;
let availableItemsContainer, bookingCartContainer, validateBtn, cancelBtn, modalFooter;
let editingGroupId = null;

// State
let originalTimes = { start: null, end: null };
let timeChangeDebounce = null;
let lastItemModalInstance = null;
let pendingDelete = null;
let availabilityController = null;

// --- HELPERS ---

function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!token) {
        showToast(ERROR_MESSAGES.CSRF_MISSING, 'error');
        throw new Error('Missing CSRF token');
    }
    return token;
}

function validateAPIResponse(data, requiredFields = []) {
    if (!data || typeof data !== 'object') throw new Error(ERROR_MESSAGES.INVALID_RESPONSE);
    if (data.success === false) throw new Error(data.error || 'Erreur inconnue');
    for (const field of requiredFields) {
        if (!(field in data)) throw new Error(`Champ manquant : ${field}`);
    }
    return data;
}

function setLoadingState(element, isLoading, loadingText = 'Chargement...') {
    if (!element) return;
    if (isLoading) {
        element.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                <p class="text-muted small mt-2 mb-0">${escapeHtml(loadingText)}</p>
            </div>`;
    }
}

function replaceButtonHandler(button, newHandler, options = {}) {
    if (!button || !button.parentNode) return null;
    const newBtn = button.cloneNode(true);
    newBtn.style.display = options.display || 'inline-block';
    newBtn.disabled = options.disabled || false;
    if (options.html !== undefined) newBtn.innerHTML = options.html;
    if (options.text !== undefined) newBtn.textContent = options.text;
    if (options.className !== undefined) newBtn.className = options.className;
    if (options.dismiss) newBtn.dataset.bsDismiss = 'modal';
    else delete newBtn.dataset.bsDismiss;
    newBtn.onclick = newHandler || null;
    button.parentNode.replaceChild(newBtn, button);
    return newBtn;
}

function generateTimeSelectors() {
    const container = document.querySelector('.main-container') || document.body;
    const startStr = container.dataset.planningDebut || container.dataset.planningStart || '08:00';
    const endStr = container.dataset.planningFin || container.dataset.planningEnd || '18:00';
    
    const [startH, startM] = startStr.split(':').map(Number);
    const [endH, endM] = endStr.split(':').map(Number);

    let hourOptions = '';
    for (let h = startH; h <= endH; h++) {
        hourOptions += `<option value="${h}">${String(h).padStart(2, '0')}</option>`;
    }

    let minuteOptions = '';
    for (let m = 0; m < 60; m += 5) {
        minuteOptions += `<option value="${m}">${String(m).padStart(2, '0')}</option>`;
    }

    startHourSelect.innerHTML = hourOptions;
    endHourSelect.innerHTML = hourOptions;
    startMinuteSelect.innerHTML = minuteOptions;
    endMinuteSelect.innerHTML = minuteOptions;

    // Appliquer les bornes depuis la config
    startHourSelect.value = startH;
    startMinuteSelect.value = startM;
    endHourSelect.value = endH;
    endMinuteSelect.value = endM;
}

/**
 * Récupère l'heure de début et de fin formatée (HH:MM) depuis les 4 selects.
 * @returns {{start: string, end: string}}
 */
function getSelectedTimes() {
    const startH = String(startHourSelect.value).padStart(2, '0');
    const startM = String(startMinuteSelect.value).padStart(2, '0');
    const endH = String(endHourSelect.value).padStart(2, '0');
    const endM = String(endMinuteSelect.value).padStart(2, '0');
    return {
        start: `${startH}:${startM}`,
        end: `${endH}:${endM}`
    };
}

// --- INITIALISATION ---
// --- GÉNÉRATION DYNAMIQUE DES CRÉNEAUX HORAIRES ---
export function initBookingModal() {
    if (!bookingModalElement) return;

    modalTitle = bookingModalElement.querySelector('.modal-title');
    dateInput = document.getElementById('bookingDate');
    startHourSelect = document.getElementById('startHour');
	startMinuteSelect = document.getElementById('startMinute');
	endHourSelect = document.getElementById('endHour');
	endMinuteSelect = document.getElementById('endMinute');
    availableItemsContainer = document.getElementById('availableItems');
    bookingCartContainer = document.getElementById('bookingCart');
    validateBtn = document.getElementById('validateBookingBtn');
    modalFooter = bookingModalElement.querySelector('.modal-footer');
    cancelBtn = modalFooter.querySelector('.btn-secondary');
	
	generateTimeSelectors();

    // APPEL CRITIQUE : Générer les heures au chargement
	const timeSelectors = [startHourSelect, startMinuteSelect, endHourSelect, endMinuteSelect];
	timeSelectors.forEach(select => {
		if (select) select.addEventListener('change', onTimeChange);
	});

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

    initRecurrence();
    bookingModalElement.addEventListener('show.bs.modal', handleModalOpen);
	bookingModalElement.addEventListener('show.bs.modal', handleModalOpen);
    bookingModalElement.addEventListener('hidden.bs.modal', () => {
        resetModalState();
        forceCleanup();
    });

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
    const dateObj = new Date(date);
    const dateFr = dateObj.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
    
    if (bookingCartContainer) bookingCartContainer.style.display = 'block';
    if (validateBtn) validateBtn.style.display = 'none';
    if (cancelBtn) cancelBtn.style.display = 'none';

    // On régénère les options à l'ouverture pour être sûr (cas de changement de config sans reload)
    generateTimeSelectors();

    if (editingGroupId) {
        // MODE ÉDITION
        modalTitle.innerHTML = '<i class="bi bi-pencil-square me-2"></i>Modifier la réservation';
        cancelBtn = replaceButtonHandler(cancelBtn, null, {
            text: "Fermer", className: "btn btn-dark", dismiss: true
        });
        await loadExistingReservation(editingGroupId);

    } else {
        // MODE CRÉATION
        modalTitle.innerHTML = `<i class="bi bi-calendar-check me-2"></i>Réserver pour le ${dateFr}`;
        
        validateBtn = replaceButtonHandler(validateBtn, 
            (e) => { e.preventDefault(); window.location.href = '/panier'; },
            { html: '<i class="bi bi-cart-check me-2"></i>Voir mon panier', className: "btn btn-success" }
        );

        cancelBtn = replaceButtonHandler(cancelBtn, 
            (e) => {
                e.preventDefault();
                if (bookingModalInstance) bookingModalInstance.hide();
                forceCleanup();
                if (!window.location.pathname.includes('/calendrier')) window.location.href = '/calendrier';
            },
            { html: '<i class="bi bi-calendar-week me-2"></i>Poursuivre (Calendrier)', className: "btn btn-outline-secondary", dismiss: false }
        );

        generateTimeSelectors(); 
        setSmartTime();      
        loadAvailabilities();
        refreshMiniCart();
    }
}


function setSmartTime() {
    if (!startHourSelect || !startMinuteSelect || !endHourSelect || !endMinuteSelect) return;
    
    const now = new Date();
    const selectedDate = dateInput ? dateInput.value : null;
    const todayStr = now.toISOString().split('T')[0];
    const isToday = selectedDate === todayStr;
    const currentMinutes = isToday ? (now.getHours() * 60 + now.getMinutes()) : -1;
    const step = parseInt((document.querySelector('.main-container') || document.body).dataset.planningStep || '60', 10);

    const container = document.querySelector('.main-container') || document.body;
    const planningStartStr = container.dataset.planningDebut || '08:00';
    const [planningStartH, planningStartM] = planningStartStr.split(':').map(Number);
    const planningEndStr = container.dataset.planningFin || '18:00';
    const [planningEndH, planningEndM] = planningEndStr.split(':').map(Number);

    let bestH = null;
    let bestM = 0;

    if (!isToday) {
        // Jour futur : premier créneau du planning
        bestH = planningStartH;
        bestM = planningStartM;
    } else {
        // Aujourd'hui : prochain créneau après maintenant
        for (const hourOption of startHourSelect.options) {
            const h = parseInt(hourOption.value, 10);
            for (const minOption of startMinuteSelect.options) {
                const m = parseInt(minOption.value, 10);
                if (h * 60 + m > currentMinutes) {
                    bestH = h;
                    bestM = m;
                    break;
                }
            }
            if (bestH !== null) break;
        }
        // Si aucun créneau futur aujourd'hui
        if (bestH === null) {
            bestH = planningStartH;
            bestM = planningStartM;
        }
    }

    startHourSelect.value = bestH;
    startMinuteSelect.value = bestM;

    const endTotalMinutes = bestH * 60 + bestM + step;
    const endH = Math.floor(endTotalMinutes / 60);
    const endM = endTotalMinutes % 60;

    if ([...endHourSelect.options].some(o => parseInt(o.value) === endH)) {
        endHourSelect.value = endH;
    } else {
        endHourSelect.value = planningEndH;
    }
    if ([...endMinuteSelect.options].some(o => parseInt(o.value) === endM)) {
        endMinuteSelect.value = endM;
    } else {
        endMinuteSelect.value = planningEndM;
    }
}

function resetModalState() {
    delete bookingModalElement.dataset.date;
    delete bookingModalElement.dataset.groupId;
    editingGroupId = null;
    originalTimes = { start: null, end: null };
    availableItemsContainer.innerHTML = '';
    if (bookingCartContainer) bookingCartContainer.innerHTML = '';
    if (availabilityController) availabilityController.abort();
}

function forceCleanup() {
    const instance = bootstrap.Modal.getInstance(bookingModalElement);
    if (instance) instance.dispose();
    setTimeout(() => {
        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
        document.body.classList.remove('modal-open');
        document.body.style = '';
    }, 150);
}

// --- GESTION DU TEMPS ---
function onTimeChange() {
    const { start, end } = getSelectedTimes();

    // Si l'heure de fin est invalide, on l'ajuste automatiquement
    if (start >= end) {
        const [startH, startM] = start.split(':').map(Number);
        let endTotalMinutes = startH * 60 + startM + 60; // Ajoute 1 heure par défaut

        const maxEndHour = parseInt(endHourSelect.options[endHourSelect.options.length - 1].value, 10);
        if (endTotalMinutes >= (maxEndHour + 1) * 60) {
            endTotalMinutes = maxEndHour * 60 + 55;
        }

        let newEndH = Math.floor(endTotalMinutes / 60);
        let newEndM = endTotalMinutes % 60;
        
        // Arrondir aux 5 minutes supérieures
        newEndM = Math.ceil(newEndM / 5) * 5;
        if (newEndM >= 60) {
            newEndM = 0;
            newEndH += 1;
        }

        endHourSelect.value = newEndH;
        endMinuteSelect.value = newEndM;
    }

    // Déclenche la mise à jour des disponibilités avec un délai
    clearTimeout(timeChangeDebounce);
    timeChangeDebounce = setTimeout(() => {
        loadAvailabilities();
    }, 350);
}

// ============================================================
// RÉCURRENCE
// ============================================================
function initRecurrence() {
    const toggle = document.getElementById('recurrenceToggle');
    const options = document.getElementById('recurrenceOptions');
    const limiteDate = document.getElementById('limiteDate');
    const limiteOcc = document.getElementById('limiteOccurrences');
    const dateFinInput = document.getElementById('recurrenceDateFin');
    const nbOccInput = document.getElementById('recurrenceNbOccurrences');

    if (!toggle) return;

    toggle.addEventListener('change', () => {
        options.style.display = toggle.checked ? 'block' : 'none';
        updateRecurrencePreview();
    });

    document.querySelectorAll('input[name="recurrenceLimite"]').forEach(radio => {
        radio.addEventListener('change', () => {
            dateFinInput.style.display = limiteDate.checked ? 'block' : 'none';
            nbOccInput.style.display = limiteOcc.checked ? 'block' : 'none';
            updateRecurrencePreview();
        });
    });

    dateFinInput.addEventListener('change', updateRecurrencePreview);
    nbOccInput.addEventListener('input', updateRecurrencePreview);
    document.getElementById('recurrenceType')?.addEventListener('change', updateRecurrencePreview);
}

function updateRecurrencePreview() {
    const preview = document.getElementById('recurrencePreview');
    if (!preview) return;
    const type = document.getElementById('recurrenceType')?.value;
    const limiteDate = document.getElementById('limiteDate')?.checked;
    const dateFin = document.getElementById('recurrenceDateFin')?.value;
    const nbOcc = document.getElementById('recurrenceNbOccurrences')?.value;
    const labels = {
        'hebdo': 'chaque semaine',
        'quotidien_ouvre': 'chaque jour ouvré',
        'bi_hebdo': 'toutes les 2 semaines',
        'mensuel': 'chaque mois'
    };
    let text = `Réservation répétée ${labels[type] || ''}`;
    if (limiteDate && dateFin) text += ` jusqu'au ${dateFin}`;
    else if (!limiteDate && nbOcc) text += ` pendant ${nbOcc} occurrences`;
    preview.textContent = text;
}

function getRecurrenceData() {
    const toggle = document.getElementById('recurrenceToggle');
    if (!toggle?.checked) return null;
    const limiteDate = document.getElementById('limiteDate')?.checked;
    return {
        type: document.getElementById('recurrenceType')?.value,
        date_fin: limiteDate ? document.getElementById('recurrenceDateFin')?.value : null,
        nb_occurrences: !limiteDate ? parseInt(document.getElementById('recurrenceNbOccurrences')?.value) : null
    };
}

// --- GESTION DES BOUTONS DYNAMIQUES (EDITION) ---

function showEditTimeButtons() {
    if (cancelBtn) cancelBtn.style.display = 'none';
    if (validateBtn) validateBtn.style.display = 'none';
    if (modalFooter.querySelector('.btn-custom-time')) return;

    const btnReset = document.createElement('button');
    btnReset.className = 'btn btn-outline-secondary btn-custom-time me-2';
    btnReset.innerHTML = '<i class="bi bi-x-lg me-2"></i>Annuler';
    btnReset.onclick = () => {
        const [origStartH, origStartM] = originalTimes.start.split(':').map(Number);
		const [origEndH, origEndM] = originalTimes.end.split(':').map(Number);
		startHourSelect.value = origStartH;
		startMinuteSelect.value = origStartM;
		endHourSelect.value = origEndH;
		endMinuteSelect.value = origEndM;
        const customBtns = modalFooter.querySelectorAll('.btn-custom-time');
        customBtns.forEach(btn => btn.remove());
        if (cancelBtn) cancelBtn.style.display = 'inline-block';
    };

    const btnUpdate = document.createElement('button');
    btnUpdate.className = 'btn btn-primary btn-custom-time';
    btnUpdate.innerHTML = '<i class="bi bi-check-lg me-2"></i>Mettre à jour l\'heure';
    
    btnUpdate.onclick = async () => {
        const originalText = btnUpdate.innerHTML;
        btnUpdate.disabled = true;
        btnUpdate.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Vérification...';

        try {
            const checkRes = await fetch(
                `/api/disponibilites?date=${dateInput.value}&heure_debut=${getSelectedTimes().start}&heure_fin=${getSelectedTimes().end}`
            );
            const checkData = validateAPIResponse(await checkRes.json(), ['data']);
            await performTimeUpdate();

        } catch (err) {
            showToast(err.message || ERROR_MESSAGES.TECHNICAL_ERROR, "error");
            btnUpdate.disabled = false;
            btnUpdate.innerHTML = originalText;
        }
    };

    modalFooter.appendChild(btnReset);
    modalFooter.appendChild(btnUpdate);
}

async function performTimeUpdate() {
    const payload = {
        date: dateInput.value,
        heure_debut: getSelectedTimes().start,
		heure_fin: getSelectedTimes().end
    };
    
    const res = await fetch(`/api/reservation/${editingGroupId}/modifier_heure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify(payload)
    });
    
    const data = validateAPIResponse(await res.json());
    if (data.success) {
        showToast("Horaire modifié avec succès", "success");
        setTimeout(() => window.location.reload(), 500);
    }
}

// --- LOGIQUE MÉTIER ---

async function loadExistingReservation(groupId) {
    try {
        setLoadingState(bookingCartContainer, true, 'Chargement réservation...');
        const response = await fetch(`/api/reservation_details/${groupId}`);
        if (!response.ok) throw new Error(ERROR_MESSAGES.LOADING_ERROR);
        const data = await response.json();

        if (data.debut && data.fin) {
			const start = data.debut.substring(11, 16);
			const end = data.fin.substring(11, 16);
			
			const [startH, startM] = start.split(':');
			const [endH, endM] = end.split(':');

			startHourSelect.value = parseInt(startH, 10);
			startMinuteSelect.value = parseInt(startM, 10);
			endHourSelect.value = parseInt(endH, 10);
			endMinuteSelect.value = parseInt(endM, 10);

			originalTimes = { start, end }; // On garde le format HH:MM pour la comparaison
		}

        renderMiniCart(data.items, false); 
        loadAvailabilities();
    } catch (error) {
        bookingCartContainer.innerHTML = `<div class="text-danger text-center p-3">${ERROR_MESSAGES.LOADING_ERROR}</div>`;
    }
}

async function loadAvailabilities() {
    const date = dateInput.value;
    const { start, end } = getSelectedTimes();
    
    if (!date || !start || !end) return;

    const [startH, startM] = start.split(':').map(Number);
    const [endH, endM] = end.split(':').map(Number);
    if (startH * 60 + startM >= endH * 60 + endM) {
        availableItemsContainer.innerHTML = `<div class="text-center py-4 text-warning">Heure de fin invalide</div>`;
        return;
    }

    if (availabilityController) availabilityController.abort();
    availabilityController = new AbortController();

    setLoadingState(availableItemsContainer, true, 'Vérification stocks...');

    try {
        const res = await fetch(`/api/disponibilites?date=${date}&heure_debut=${start}&heure_fin=${end}`, { signal: availabilityController.signal });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const response = validateAPIResponse(await res.json(), ['data']);
        renderAvailableItems(response.data);
    } catch (err) {
        if (err.name !== 'AbortError') {
            availableItemsContainer.innerHTML = `<div class="alert alert-danger m-3">${escapeHtml(err.message)}</div>`;
        }
    }
}

async function refreshMiniCart() {
    if (!bookingCartContainer) return;
    setLoadingState(bookingCartContainer, true, 'Chargement panier...');
    try {
        const res = await fetch('/api/panier');
        const json = validateAPIResponse(await res.json(), ['data']);
        renderMiniCart(json.data.items, false);
    } catch (e) { 
        bookingCartContainer.innerHTML = `<div class="text-danger small text-center p-3">${ERROR_MESSAGES.CART_ERROR}</div>`; 
    }
}

// --- ACTIONS (ADD/REMOVE) ---

async function addItem(item) {
    const payload = { type: item.type, id: item.id, quantite: 1 };
	let url = '/api/panier/ajouter';
	if (editingGroupId) url = `/api/reservation/${editingGroupId}/ajouter`;
	else {
		payload.date = dateInput.value;
		const { start, end } = getSelectedTimes();
		payload.heure_debut = start;
		payload.heure_fin = end;
		// Salle optionnelle
		const salleSelect = document.getElementById('bookingSalle');
		if (salleSelect && salleSelect.value) {
			payload.salle_id = parseInt(salleSelect.value);
		}
		const recurrence = getRecurrenceData();
		if (recurrence) {
			payload.recurrence = recurrence;
		}
	}

    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify(payload)
        });
        const data = validateAPIResponse(await res.json());
        if (data.success) {
            showToast(`Ajouté : ${item.nom}`, "success");
            loadAvailabilities();
            if (editingGroupId) loadExistingReservation(editingGroupId);
            else { refreshMiniCart(); updateCartBadge(); }
        }
    } catch (err) { showToast(err.message, "error"); }
}

function requestRemoveItem(itemId, itemType, currentQty) {
    if (editingGroupId) {
        const itemsCount = document.querySelectorAll('#bookingCart li').length;
        if (itemsCount === 1 && currentQty <= 1) {
            pendingDelete = { id: itemId, type: itemType };
            if (lastItemModalInstance) lastItemModalInstance.show();
            else if(confirm("Supprimer la réservation ?")) performRemoveItem(itemId, itemType);
            return;
        }
    }
    performRemoveItem(itemId, itemType);
}

async function performRemoveItem(itemId, itemType) {
    let url = `/api/panier/retirer/${itemId}`;
    if (editingGroupId) url = `/api/reservation/${editingGroupId}/retirer/${itemId}?type=${itemType}`;

    try {
        const res = await fetch(url, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCSRFToken() }
        });
        const data = await res.json(); 
        if (res.ok && data.success) {
            showToast("Retiré", "info");
            updateCartBadge();
            if (editingGroupId && data.remaining_items === 0) {
                if (bookingModalInstance) bookingModalInstance.hide();
                forceCleanup();
                window.location.reload();
                return;
            }
            loadAvailabilities();
            if (editingGroupId) loadExistingReservation(editingGroupId);
            else refreshMiniCart();
        } else throw new Error(data.error);
    } catch (e) { showToast(e.message, "error"); }
}

// --- RENDU ---

function renderAvailableItems(data) {
    let html = '<div class="list-group list-group-flush">';
    const getImg = (img) => img ? (img.startsWith('http') ? img : `/static/${img}`) : null;
    
    const renderRow = (item, type, style) => {
        const dispo = item.disponible;
        const active = dispo > 0;
        const imgUrl = getImg(item.image);
        const imgHtml = imgUrl ? `<img src="${imgUrl}" class="rounded border" style="width:40px;height:40px;object-fit:cover;" alt="${escapeHtml(item.nom)}">` : `<div class="rounded bg-light d-flex align-items-center justify-content-center" style="width:40px;height:40px;"><i class="bi bi-box text-muted"></i></div>`;

        return `
            <div class="list-group-item d-flex justify-content-between align-items-center py-2 px-0 ${style}">
                <div class="d-flex align-items-center gap-2 overflow-hidden">
                    ${imgHtml}
                    <div class="text-truncate">
                        <div class="fw-bold text-dark text-truncate" title="${escapeHtml(item.nom)}">${escapeHtml(item.nom)}</div>
                        <div class="small text-muted">${escapeHtml(item.armoire || '')}</div>
                    </div>
                </div>
                <div class="d-flex align-items-center gap-2 flex-shrink-0">
                    <span class="badge ${active ? 'bg-light text-dark border' : 'bg-danger-subtle text-danger'} rounded-pill">${dispo}</span>
                    <button type="button" class="btn btn-sm ${active ? 'btn-primary' : 'btn-secondary disabled'} btn-add-item" 
                            data-type="${type}" data-id="${item.id}" data-nom="${escapeHtml(item.nom)}" ${!active ? 'disabled' : ''}>
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
    
    if (!data.objets?.length && !data.kits?.length) {
        html += '<div class="text-center py-4 text-muted small">Aucun matériel disponible.</div>';
    }
    availableItemsContainer.innerHTML = html + '</div>';
}

function renderMiniCart(items, readOnly) {
    if (!Array.isArray(items) || items.length === 0) {
        bookingCartContainer.innerHTML = '<div class="text-muted fst-italic text-center mt-3">Votre panier est vide.</div>';
        return;
    }
    let html = '<ul class="list-group list-group-flush">';
    items.forEach(item => {
        const type = item.type || 'objet'; 
        const deleteBtn = readOnly ? '' : `<button class="btn btn-link text-danger p-0 btn-remove-item" data-id="${item.id}" data-type="${type}" data-qty="${item.quantite}"><i class="bi bi-dash-circle-fill"></i></button>`;
        html += `
            <li class="list-group-item d-flex justify-content-between align-items-center px-0 py-2">
                <div class="small lh-1">
                    <div class="fw-bold text-truncate" style="max-width: 140px;">${escapeHtml(item.nom)}</div>
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
        addItem({ type: btn.dataset.type, id: parseInt(btn.dataset.id, 10), nom: btn.dataset.nom }).then(() => {
            btn.innerHTML = original;
            btn.disabled = false;
        });
    });

    if (bookingCartContainer) {
        bookingCartContainer.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-remove-item');
            if (!btn) return;
            e.preventDefault();
            requestRemoveItem(parseInt(btn.dataset.id, 10), btn.dataset.type, parseInt(btn.dataset.qty, 10));
        });
    }
}


document.addEventListener('DOMContentLoaded', initBookingModal);