// static/js/modules/booking-modal.js
import { showToast } from './toast.js';
import { updateCartBadge, escapeHtml } from './cart-utils.js';

// --- CONFIGURATION & CONSTANTES ---
const DEBUG = true; // Mettre à false en production

const BOOKING_CONFIG = {
    MIN_HOUR: 8,
    MAX_HOUR: 18,
    DEBOUNCE_DELAY: 300
};

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
let modalTitle, dateInput, startTimeSelect, endTimeSelect;
let availableItemsContainer, bookingCartContainer, validateBtn, cancelBtn, modalFooter;
let editingGroupId = null;

// State
let originalTimes = { start: null, end: null };
let timeChangeDebounce = null;
let lastItemModalInstance = null;
let pendingDelete = null;
let availabilityController = null;

// --- HELPERS TECHNIQUES ---

/**
 * Logging structuré pour le débogage
 */
function log(level, message, data = {}) {
    if (!DEBUG && level === 'debug') return;
    
    const timestamp = new Date().toISOString();
    const logData = { timestamp, level, message, ...data };
    
    console[level === 'error' ? 'error' : 'log']('[BookingModal]', logData);
}

/**
 * Récupère et valide le token CSRF
 */
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!token) {
        log('error', ERROR_MESSAGES.CSRF_MISSING);
        showToast(ERROR_MESSAGES.CSRF_MISSING, 'error');
        throw new Error('Missing CSRF token');
    }
    return token;
}

/**
 * Valide la structure de la réponse API
 */
function validateAPIResponse(data, requiredFields = []) {
    if (!data || typeof data !== 'object') {
        throw new Error(ERROR_MESSAGES.INVALID_RESPONSE);
    }
    
    if (data.success === false) {
        throw new Error(data.error || 'Erreur inconnue renvoyée par le serveur');
    }
    
    for (const field of requiredFields) {
        if (!(field in data)) {
            throw new Error(`Champ manquant dans la réponse API : ${field}`);
        }
    }
    
    return data;
}

/**
 * Gère l'état de chargement d'un conteneur (div, ul, etc.)
 */
function setLoadingState(element, isLoading, loadingText = 'Chargement...') {
    if (!element) return;
    
    if (isLoading) {
        // On sauvegarde le contenu actuel seulement s'il n'est pas déjà en chargement
        if (!element.querySelector('.spinner-border')) {
            element.dataset.originalContent = element.innerHTML;
        }
        element.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                <p class="text-muted small mt-2 mb-0">${escapeHtml(loadingText)}</p>
            </div>`;
    } else {
        // Note: On ne restaure pas forcément l'originalContent car souvent on le remplace par le nouveau contenu
        delete element.dataset.originalContent;
    }
}

/**
 * Remplace un bouton pour supprimer les anciens EventListeners et mettre à jour ses propriétés
 */
function replaceButtonHandler(button, newHandler, options = {}) {
    if (!button || !button.parentNode) {
        console.warn('replaceButtonHandler: bouton invalide ou absent du DOM');
        return null;
    }
    
    const newBtn = button.cloneNode(true);
    
    // Application des options
    newBtn.style.display = options.display || 'inline-block';
    newBtn.disabled = options.disabled || false;
    
    if (options.html !== undefined) newBtn.innerHTML = options.html;
    if (options.text !== undefined) newBtn.textContent = options.text;
    if (options.className !== undefined) newBtn.className = options.className;
    if (options.ariaLabel) newBtn.setAttribute('aria-label', options.ariaLabel);
    
    // Gestion du dismiss modal
    if (options.dismiss) {
        newBtn.dataset.bsDismiss = 'modal';
    } else {
        delete newBtn.dataset.bsDismiss;
    }
    
    // Handler
    if (newHandler) newBtn.onclick = newHandler;
    else newBtn.onclick = null;
    
    button.parentNode.replaceChild(newBtn, button);
    return newBtn;
}

// --- INITIALISATION ---

export function initBookingModal() {
    if (!bookingModalElement) return;

    modalTitle = bookingModalElement.querySelector('.modal-title');
    dateInput = document.getElementById('bookingDate');
    startTimeSelect = document.getElementById('startTime');
    endTimeSelect = document.getElementById('endTime');
    availableItemsContainer = document.getElementById('availableItems');
    bookingCartContainer = document.getElementById('bookingCart');
    validateBtn = document.getElementById('validateBookingBtn');
    modalFooter = bookingModalElement.querySelector('.modal-footer');
    cancelBtn = modalFooter.querySelector('.btn-secondary');

    // Init Modale Warning (Suppression dernier item)
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
    bookingModalElement.addEventListener('hidden.bs.modal', () => {
        resetModalState();
        forceCleanup();
    });

    if (startTimeSelect) startTimeSelect.addEventListener('change', onTimeChange);
    if (endTimeSelect) endTimeSelect.addEventListener('change', onTimeChange);

    setupDelegatedEvents();
}

export function openReservationModal(date, groupId = null) {
    if (!bookingModalElement) return;
    bookingModalElement.dataset.date = date;
    if (groupId) bookingModalElement.dataset.groupId = groupId;
    else delete bookingModalElement.dataset.groupId;

    if (!bookingModalInstance) bookingModalInstance = new bootstrap.Modal(bookingModalElement);
    bookingModalInstance.show();
    
    log('debug', 'Ouverture modale demandée', { date, groupId });
}

async function handleModalOpen(event) {
    const trigger = event.relatedTarget || bookingModalElement;
    const date = trigger.dataset.date;
    editingGroupId = trigger.dataset.groupId || null;

    if (!date) {
        log('error', 'Date manquante à l\'ouverture de la modale');
        return;
    }

    dateInput.value = date;
    const dateObj = new Date(date);
    const dateFr = dateObj.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
    
    if (bookingCartContainer) bookingCartContainer.style.display = 'block';

    // Reset visuel des boutons avant configuration
    if (validateBtn) validateBtn.style.display = 'none';
    if (cancelBtn) cancelBtn.style.display = 'none';

    if (editingGroupId) {
        // --- MODE ÉDITION ---
        modalTitle.innerHTML = ''; 
        const icon = document.createElement('i');
        icon.className = 'bi bi-pencil-square me-2';
        modalTitle.appendChild(icon);
        modalTitle.appendChild(document.createTextNode('Modifier la réservation'));
        
        cancelBtn = replaceButtonHandler(cancelBtn, null, {
            text: "Fermer",
            className: "btn btn-dark",
            dismiss: true,
            ariaLabel: "Fermer la fenêtre"
        });
        
        await loadExistingReservation(editingGroupId);

    } else {
        // --- MODE CRÉATION ---
        modalTitle.innerHTML = '';
        const icon = document.createElement('i');
        icon.className = 'bi bi-calendar-check me-2';
        modalTitle.appendChild(icon);
        modalTitle.appendChild(document.createTextNode(`Réserver pour le ${dateFr}`));
        
        validateBtn = replaceButtonHandler(validateBtn, 
            (e) => { e.preventDefault(); window.location.href = '/panier'; },
            { 
                html: '<i class="bi bi-cart-check me-2"></i>Voir mon panier', 
                className: "btn btn-success",
                ariaLabel: "Accéder au panier pour valider"
            }
        );

        cancelBtn = replaceButtonHandler(cancelBtn, 
            (e) => {
                e.preventDefault();
                if (bookingModalInstance) bookingModalInstance.hide();
                else bootstrap.Modal.getInstance(bookingModalElement).hide();
                forceCleanup();
                if (!window.location.pathname.includes('/calendrier')) window.location.href = '/calendrier';
            },
            {
                html: '<i class="bi bi-calendar-week me-2"></i>Poursuivre (Calendrier)',
                className: "btn btn-outline-secondary",
                dismiss: false,
                ariaLabel: "Retourner au calendrier"
            }
        );

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

function updateHourOptions() {
    if (!startTimeSelect || !endTimeSelect) return;
    
    const startVal = startTimeSelect.value;
    const endVal = endTimeSelect.value;

    if (startVal >= endVal) {
        const startHour = parseInt(startVal.split(':')[0]);
        const newEndHour = startHour + 1;
        const newEndStr = `${String(newEndHour).padStart(2, '0')}:00`;
        
        const optionExists = [...endTimeSelect.options].some(o => o.value === newEndStr);
        if (optionExists) {
            endTimeSelect.value = newEndStr;
        }
    }
}

function onTimeChange(event) {
    if (event.target === startTimeSelect) {
        updateHourOptions();
    }

    if (editingGroupId && originalTimes.start) {
        if (startTimeSelect.value !== originalTimes.start || endTimeSelect.value !== originalTimes.end) {
            showEditTimeButtons();
        } else {
            const customBtns = modalFooter.querySelectorAll('.btn-custom-time');
            customBtns.forEach(btn => btn.remove());
            if (cancelBtn) cancelBtn.style.display = 'inline-block';
        }
        return;
    }

    clearTimeout(timeChangeDebounce);
    timeChangeDebounce = setTimeout(() => {
        loadAvailabilities();
    }, BOOKING_CONFIG.DEBOUNCE_DELAY);
}

// --- GESTION DES BOUTONS DYNAMIQUES (EDITION) ---

function showEditTimeButtons() {
    if (cancelBtn) cancelBtn.style.display = 'none';
    if (validateBtn) validateBtn.style.display = 'none';

    if (modalFooter.querySelector('.btn-custom-time')) return;

    // Bouton Annuler
    const btnReset = document.createElement('button');
    btnReset.className = 'btn btn-outline-secondary btn-custom-time me-2';
    btnReset.innerHTML = '<i class="bi bi-x-lg me-2"></i>Annuler';
    btnReset.onclick = () => {
        startTimeSelect.value = originalTimes.start;
        endTimeSelect.value = originalTimes.end;
        const customBtns = modalFooter.querySelectorAll('.btn-custom-time');
        customBtns.forEach(btn => btn.remove());
        if (cancelBtn) cancelBtn.style.display = 'inline-block';
    };

    // Bouton Mettre à jour
    const btnUpdate = document.createElement('button');
    btnUpdate.className = 'btn btn-primary btn-custom-time';
    btnUpdate.innerHTML = '<i class="bi bi-check-lg me-2"></i>Mettre à jour l\'heure';
    
    btnUpdate.onclick = async () => {
        const originalText = btnUpdate.innerHTML;
        btnUpdate.disabled = true;
        btnUpdate.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Vérification...';

        try {
            // 1. Vérification des disponibilités
            const checkRes = await fetch(
                `/api/disponibilites?date=${dateInput.value}&heure_debut=${startTimeSelect.value}&heure_fin=${endTimeSelect.value}`
            );
            
            const checkData = validateAPIResponse(await checkRes.json(), ['data']);
            
            // 2. Récupération des items actuels
            const currentItems = getCurrentCartItems();
            const unavailableItems = [];
            
            currentItems.forEach(cartItem => {
                const itemType = cartItem.type === 'kit' ? 'kits' : 'objets';
                const availableItem = checkData.data[itemType]?.find(i => i.id === cartItem.id);
                
                if (!availableItem || availableItem.disponible < cartItem.quantite) {
                    unavailableItems.push({
                        nom: cartItem.nom,
                        needed: cartItem.quantite,
                        available: availableItem?.disponible || 0
                    });
                }
            });

            // 3. Alerte si conflit
            if (unavailableItems.length > 0) {
                const message = unavailableItems.map(item => 
                    `• ${item.nom} (Besoin: ${item.needed}, Dispo: ${item.available})`
                ).join('\n');
                
                if (!confirm(`⚠️ Attention : Certains items ne seront plus disponibles sur ce nouveau créneau :\n\n${message}\n\nLa mise à jour risque d'échouer. Continuer quand même ?`)) {
                    btnUpdate.disabled = false;
                    btnUpdate.innerHTML = originalText;
                    return;
                }
            }

            // 4. Envoi de la modification
            btnUpdate.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Enregistrement...';
            await performTimeUpdate();

        } catch (err) {
            log('error', 'Erreur mise à jour heure', err);
            showToast(err.message || ERROR_MESSAGES.TECHNICAL_ERROR, "error");
            btnUpdate.disabled = false;
            btnUpdate.innerHTML = originalText;
        }
    };

    modalFooter.appendChild(btnReset);
    modalFooter.appendChild(btnUpdate);
}

// Helpers
function getCurrentCartItems() {
    const items = [];
    document.querySelectorAll('#bookingCart li').forEach(li => {
        const nomEl = li.querySelector('.fw-bold');
        const badgeEl = li.querySelector('.badge');
        const btnEl = li.querySelector('.btn-remove-item');
        
        if (nomEl && badgeEl && btnEl) {
            items.push({
                nom: nomEl.textContent.trim(),
                quantite: parseInt(badgeEl.textContent.replace('x', ''), 10),
                id: parseInt(btnEl.dataset.id, 10),
                type: btnEl.dataset.type
            });
        }
    });
    return items;
}

async function performTimeUpdate() {
    const payload = {
        date: dateInput.value,
        heure_debut: startTimeSelect.value,
        heure_fin: endTimeSelect.value
    };
    
    const csrfToken = getCSRFToken();

    const res = await fetch(`/api/reservation/${editingGroupId}/modifier_heure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
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
            
            startTimeSelect.value = start;
            endTimeSelect.value = end;
            
            originalTimes = { start: start, end: end };
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
        log('error', 'Erreur loadExistingReservation', error);
        bookingCartContainer.innerHTML = `<div class="text-danger text-center p-3">${ERROR_MESSAGES.LOADING_ERROR}</div>`;
    }
}

async function loadAvailabilities() {
    const date = dateInput.value;
    const start = startTimeSelect.value;
    const end = endTimeSelect.value;
    if (!date || !start || !end) return;

    if (availabilityController) {
        availabilityController.abort();
    }
    availabilityController = new AbortController();

    setLoadingState(availableItemsContainer, true, 'Vérification stocks...');

    let url = `/api/disponibilites?date=${date}&heure_debut=${start}&heure_fin=${end}`;
    
    try {
        const res = await fetch(url, { signal: availabilityController.signal });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        const response = validateAPIResponse(await res.json(), ['data']);
        renderAvailableItems(response.data);
        
    } catch (err) {
        if (err.name === 'AbortError') return;
        
        log('error', 'Erreur loadAvailabilities', err);
        availableItemsContainer.innerHTML = `<div class="alert alert-danger m-3">${escapeHtml(err.message || ERROR_MESSAGES.AVAILABILITY_ERROR)}</div>`;
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
        log('error', 'Erreur refreshMiniCart', e);
        bookingCartContainer.innerHTML = `<div class="text-danger small text-center p-3">${ERROR_MESSAGES.CART_ERROR}</div>`; 
    }
}

// --- ACTIONS ---

async function addItem(item) {
    const payload = { type: item.type, id: item.id, quantite: 1 };
    let csrfToken;
    try {
        csrfToken = getCSRFToken();
    } catch (e) { return; }
    
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
        
        const data = validateAPIResponse(await res.json());

        if (data.success) {
            showToast(`Ajouté : ${item.nom}`, "success");
            loadAvailabilities();
            if (editingGroupId) loadExistingReservation(editingGroupId);
            else { refreshMiniCart(); updateCartBadge(); }
        }
    } catch (err) { 
        log('error', 'Erreur addItem', err);
        showToast(err.message || ERROR_MESSAGES.TECHNICAL_ERROR, "error"); 
    }
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
    let csrfToken;
    try {
        csrfToken = getCSRFToken();
    } catch (e) { return; }
    
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
        } else {
            throw new Error(data.error || ERROR_MESSAGES.TECHNICAL_ERROR);
        }
    } catch (e) { 
        log('error', 'Erreur performRemoveItem', e);
        showToast(e.message, "error");
    }
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
                            aria-label="Ajouter ${escapeHtml(item.nom)} au panier"
                            data-type="${type}" data-id="${item.id}" data-nom="${escapeHtml(item.nom)}" ${!active ? 'disabled' : ''}>
                        <i class="bi bi-plus-lg" aria-hidden="true"></i>
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
        const deleteBtn = readOnly ? '' : `<button class="btn btn-link text-danger p-0 btn-remove-item" aria-label="Retirer ${escapeHtml(item.nom)}" data-id="${item.id}" data-type="${type}" data-qty="${item.quantite}"><i class="bi bi-dash-circle-fill" aria-hidden="true"></i></button>`;
        
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

function setSmartTime() {
    const now = new Date();
    const todayStr = now.toISOString().split('T')[0];

    if (dateInput.value === todayStr) {
        let currentHour = now.getHours();
        let targetHour = currentHour + 1;
        if (targetHour < BOOKING_CONFIG.MIN_HOUR) targetHour = BOOKING_CONFIG.MIN_HOUR;
        if (targetHour > BOOKING_CONFIG.MAX_HOUR) targetHour = BOOKING_CONFIG.MAX_HOUR;

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