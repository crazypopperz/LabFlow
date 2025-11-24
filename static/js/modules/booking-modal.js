// static/js/modules/booking-modal.js

import { showToast } from './toast.js';

// ===================================================================
// VARIABLES GLOBALES DU MODULE
// ===================================================================
let bookingModalInstance = null; 
const bookingModalElement = document.getElementById('bookingModal');

let cart = {};
let selectedDate = '';
let editingGroupId = null;
let editingCartKey = null; // NOUVEAU : pour éditer un item du panier

// Références aux éléments DOM
let modalTitle, dateInput, startTimeSelect, endTimeSelect;
let availableItemsContainer, bookingCartContainer, validateBookingBtn, hiddenGroupIdInput;

// ===================================================================
// FONCTIONS UTILITAIRES
// ===================================================================

function resetModalState() {
    cart = {};
    editingCartKey = null;
    if (availableItemsContainer) {
        availableItemsContainer.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    }
    if (bookingCartContainer) {
        bookingCartContainer.innerHTML = '<p class="text-muted">Votre panier est vide.</p>';
    }
    if (validateBookingBtn) {
        validateBookingBtn.disabled = true;
    }
}

function updateHourOptions() {
    if (!startTimeSelect) return;
    
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    const currentHour = now.getHours();
    
    Array.from(startTimeSelect.options).forEach(opt => opt.disabled = false);
    
    if (selectedDate === today) {
        Array.from(startTimeSelect.options).forEach(opt => {
            const optionHour = parseInt(opt.value.split(':')[0]);
            if (optionHour <= currentHour) opt.disabled = true;
        });
    }
    
    if (startTimeSelect.options[startTimeSelect.selectedIndex].disabled) {
        const firstEnabledOption = startTimeSelect.querySelector('option:not([disabled])');
        if (firstEnabledOption) {
            startTimeSelect.value = firstEnabledOption.value;
        } else {
            startTimeSelect.value = '';
            if (endTimeSelect) endTimeSelect.value = '';
        }
    }
    handleTimeChange({ target: startTimeSelect });
}

async function handleTimeChange(event) {
    if (event.target === startTimeSelect) {
        const startHour = parseInt(startTimeSelect.value.split(':')[0]);
        const endHour = startHour + 1;
        if (endHour <= 18 && endTimeSelect) {
            const newEndTime = `${String(endHour).padStart(2, '0')}:00`;
            const endTimeOption = endTimeSelect.querySelector(`option[value="${newEndTime}"]`);
            if (endTimeOption) endTimeSelect.value = newEndTime;
        }
    }
    await fetchAndDisplayAvailabilities();
}

async function fetchAndDisplayAvailabilities() {
    if (!startTimeSelect || !endTimeSelect || !availableItemsContainer) return;
    
    const startTime = startTimeSelect.value;
    const endTime = endTimeSelect.value;
    
    if (!startTime || !endTime || startTime >= endTime) {
        availableItemsContainer.innerHTML = '<div class="alert alert-warning">Veuillez sélectionner un créneau horaire valide.</div>';
        return;
    }
    
    try {
        let url = `/api/disponibilites?date=${selectedDate}&heure_debut=${startTime}&heure_fin=${endTime}`;
        if (editingGroupId) {
            url += `&exclude_group_id=${editingGroupId}`;
        }
        const response = await fetch(url);
        if (!response.ok) throw new Error('Erreur réseau.');
        const data = await response.json();
        renderAvailableItems(data);
    } catch (error) {
        console.error('Erreur:', error);
        availableItemsContainer.innerHTML = '<div class="alert alert-danger">Impossible de charger les disponibilités.</div>';
    }
}

function renderAvailableItems(data) {
    if (!availableItemsContainer) return;
    
    let html = '<h6>Objets</h6><ul class="list-group mb-3">';
    if (data.objets && data.objets.length > 0) {
        data.objets.forEach(obj => {
            const inCartQuantity = cart[`objet_${obj.id}`] ? cart[`objet_${obj.id}`].quantity : 0;
            const remainingStock = obj.quantite_disponible - inCartQuantity;
            html += `<li class="list-group-item d-flex justify-content-between align-items-center">${obj.nom}<div><span class="badge bg-secondary rounded-pill me-2">Dispo: ${remainingStock}</span><button class="btn btn-sm btn-primary btn-add-to-cart" data-type="objet" data-id="${obj.id}" data-name="${obj.nom}" data-max-quantity="${obj.quantite_disponible}" ${remainingStock <= 0 ? 'disabled' : ''}>+</button></div></li>`;
        });
    } else {
        html += '<li class="list-group-item text-muted">Aucun objet disponible.</li>';
    }
    html += '</ul><h6>Kits</h6><ul class="list-group">';
    if (data.kits && data.kits.length > 0) {
        data.kits.forEach(kit => {
            const inCartQuantity = cart[`kit_${kit.id}`] ? cart[`kit_${kit.id}`].quantity : 0;
            const remainingStock = kit.disponible - inCartQuantity;
            html += `<li class="list-group-item d-flex justify-content-between align-items-center">${kit.nom}<div><span class="badge bg-secondary rounded-pill me-2">Dispo: ${remainingStock}</span><button class="btn btn-sm btn-primary btn-add-to-cart" data-type="kit" data-id="${kit.id}" data-name="${kit.nom}" data-max-quantity="${kit.disponible}" ${remainingStock <= 0 ? 'disabled' : ''}>+</button></div></li>`;
        });
    } else {
        html += '<li class="list-group-item text-muted">Aucun kit disponible.</li>';
    }
    html += '</ul>';
    availableItemsContainer.innerHTML = html;
}

function addToCart(type, id, name, maxQuantity) {
    const key = `${type}_${id}`;
    const inCartQuantity = cart[key] ? cart[key].quantity : 0;
    const availableStock = maxQuantity - inCartQuantity;
    if (availableStock <= 0) {
        showToast('Quantité maximale atteinte pour cet article.', 'warning');
        return;
    }
    if (cart[key]) {
        cart[key].quantity++;
    } else {
        cart[key] = { type, id, name, quantity: 1 };
    }
    updateCartAndAvailabilities();
}

function removeFromCart(key) {
    if (cart[key]) {
        cart[key].quantity--;
        if (cart[key].quantity <= 0) delete cart[key];
    }
    updateCartAndAvailabilities();
}

function updateCartAndAvailabilities() {
    renderCart();
    fetchAndDisplayAvailabilities();
}

function renderCart() {
    if (!bookingCartContainer || !validateBookingBtn) return;
    
    if (Object.keys(cart).length === 0) {
        bookingCartContainer.innerHTML = '<p class="text-muted">Votre panier est vide.</p>';
        validateBookingBtn.disabled = true;
        return;
    }
    let html = '<ul class="list-group">';
    for (const key in cart) {
        const item = cart[key];
        html += `<li class="list-group-item d-flex justify-content-between align-items-center">${item.name} (x${item.quantity})<button class="btn btn-sm btn-danger btn-remove-from-cart" data-key="${key}">-</button></li>`;
    }
    html += '</ul>';
    bookingCartContainer.innerHTML = html;
    validateBookingBtn.disabled = false;
}

// ===================================================================
// NOUVELLE FONCTION : AJOUTER AU PANIER GLOBAL (sessionStorage)
// ===================================================================
function addToGlobalCart() {
    if (!dateInput || !startTimeSelect || !endTimeSelect) return;
    
    const date = dateInput.value;
    const heureDebut = startTimeSelect.value;
    const heureFin = endTimeSelect.value;
    
    // Clé unique pour cette réservation dans le panier global
    const cartKey = editingCartKey || `${date}_${heureDebut}_${heureFin}_${Date.now()}`;
    
    // Récupération du panier global
    let globalCart = JSON.parse(sessionStorage.getItem('reservationCart')) || {};
    
    // Construction de l'objet de réservation au format attendu par cart-summary.js et api.py
    const reservationData = {
        date: date,
        heure_debut: heureDebut,
        heure_fin: heureFin,
        kits: {},
        objets: {}
    };
    
    // Transformation du cart local (format items) vers le format kits/objets
    for (const key in cart) {
        const item = cart[key];
        if (item.type === 'kit') {
            reservationData.kits[item.id] = {
                nom: item.name,
                quantite: item.quantity
            };
        } else if (item.type === 'objet') {
            reservationData.objets[item.id] = {
                nom: item.name,
                quantite: item.quantity
            };
        }
    }
    
    // Ajout ou mise à jour dans le panier global
    globalCart[cartKey] = reservationData;
    
    // Sauvegarde dans sessionStorage
    sessionStorage.setItem('reservationCart', JSON.stringify(globalCart));
    
    // Mise à jour de l'icône panier si la fonction existe
    if (typeof updateCartIcon === 'function') {
        updateCartIcon();
    }
    
    // Message de confirmation
    const message = editingCartKey ? 'Réservation mise à jour dans le panier' : 'Réservation ajoutée au panier';
    showToast(message, 'success');
    
    // Fermeture de la modale
    if (bookingModalInstance) {
        bookingModalInstance.hide();
    }
    
    // Redirection optionnelle vers le panier (à décommenter si souhaité)
    // window.location.href = '/panier';
}

// ===================================================================
// CHARGEMENT D'UNE RÉSERVATION EXISTANTE (pour modification depuis le panier)
// ===================================================================
async function loadExistingCartItem(cartKey) {
    const globalCart = JSON.parse(sessionStorage.getItem('reservationCart')) || {};
    const itemData = globalCart[cartKey];
    
    if (!itemData) {
        showToast('Réservation introuvable', 'danger');
        return;
    }
    
    // Chargement des horaires
    if (startTimeSelect && endTimeSelect) {
        startTimeSelect.value = itemData.heure_debut;
        endTimeSelect.value = itemData.heure_fin;
    }
    
    // Reconstruction du cart local depuis les kits et objets
    cart = {};
    
    if (itemData.kits) {
        for (const kitId in itemData.kits) {
            const kitData = itemData.kits[kitId];
            cart[`kit_${kitId}`] = {
                type: 'kit',
                id: parseInt(kitId),
                name: kitData.nom,
                quantity: kitData.quantite
            };
        }
    }
    
    if (itemData.objets) {
        for (const objetId in itemData.objets) {
            const objetData = itemData.objets[objetId];
            cart[`objet_${objetId}`] = {
                type: 'objet',
                id: parseInt(objetId),
                name: objetData.nom,
                quantity: objetData.quantite
            };
        }
    }
    
    renderCart();
}

// ===================================================================
// CHARGEMENT D'UNE RÉSERVATION DEPUIS LA BDD (pour modification admin)
// ===================================================================
async function loadExistingReservation(groupId) {
    if (!startTimeSelect || !endTimeSelect) return;
    
    try {
        const response = await fetch(`/api/reservation_details/${groupId}`);
        if (!response.ok) throw new Error('Impossible de charger la réservation.');
        const details = await response.json();
        
        startTimeSelect.value = new Date(details.debut_reservation).toTimeString().substring(0, 5);
        endTimeSelect.value = new Date(details.fin_reservation).toTimeString().substring(0, 5);

        cart = {};
        if (details.kits) {
            for (const kitId in details.kits) {
                const kit = details.kits[kitId];
                cart[`kit_${kitId}`] = { type: 'kit', id: parseInt(kitId), name: kit.nom, quantity: kit.quantite };
            }
        }
        if (details.objets_manuels) {
            details.objets_manuels.forEach(obj => {
                cart[`objet_${obj.objet_id}`] = { type: 'objet', id: obj.objet_id, name: obj.nom, quantity: obj.quantite_reservee };
            });
        }
        renderCart();
    } catch (error) {
        showToast(error.message, 'danger');
        resetModalState();
    }
}

// ===================================================================
// CONFIGURATION DU CONTENU DE LA MODALE
// ===================================================================
async function setupModalContent(event) {
    const button = event.relatedTarget;
    selectedDate = button.getAttribute('data-date');
    editingGroupId = button.getAttribute('data-editing-group-id');
    editingCartKey = button.getAttribute('data-editing-cart-key'); // NOUVEAU

    const formattedDate = new Date(selectedDate).toLocaleDateString('fr-FR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    
    if (editingGroupId) {
        // Mode édition d'une réservation validée (depuis la BDD)
        if (modalTitle) modalTitle.textContent = `Modifier la réservation pour le ${formattedDate}`;
        if (validateBookingBtn) validateBookingBtn.textContent = 'Enregistrer les modifications';
        if (hiddenGroupIdInput) hiddenGroupIdInput.value = editingGroupId;
        await loadExistingReservation(editingGroupId);
    } else if (editingCartKey) {
        // Mode édition d'un item du panier (depuis sessionStorage)
        if (modalTitle) modalTitle.textContent = `Modifier la réservation pour le ${formattedDate}`;
        if (validateBookingBtn) validateBookingBtn.textContent = 'Mettre à jour le panier';
        if (hiddenGroupIdInput) hiddenGroupIdInput.value = '';
        await loadExistingCartItem(editingCartKey);
    } else {
        // Mode création
        if (modalTitle) modalTitle.textContent = `Réserver du matériel pour le ${formattedDate}`;
        if (validateBookingBtn) validateBookingBtn.textContent = 'Ajouter au panier';
        if (hiddenGroupIdInput) hiddenGroupIdInput.value = '';
        resetModalState();
    }
    
    if (dateInput) dateInput.value = selectedDate;
    updateHourOptions();
    await fetchAndDisplayAvailabilities();
}

// ===================================================================
// FONCTION EXPORTÉE (ouverture programmatique)
// ===================================================================
export function openReservationModal(date, groupId = null, cartKey = null) {
    if (!bookingModalElement) {
        console.error('La modale de réservation (#bookingModal) est introuvable dans le DOM');
        return;
    }
    
    selectedDate = date;
    editingGroupId = groupId;
    editingCartKey = cartKey;
    
    const fakeRelatedTarget = {
        getAttribute: (attr) => {
            if (attr === 'data-date') return selectedDate;
            if (attr === 'data-editing-group-id') return editingGroupId;
            if (attr === 'data-editing-cart-key') return editingCartKey;
            return null;
        }
    };

    setupModalContent({ relatedTarget: fakeRelatedTarget });
    
    if (!bookingModalInstance) {
        bookingModalInstance = new bootstrap.Modal(bookingModalElement);
    }
    bookingModalInstance.show();
}

// ===================================================================
// INITIALISATION DES EVENT LISTENERS
// ===================================================================
if (bookingModalElement) {
    // Initialisation des références DOM
    modalTitle = document.getElementById('bookingModalLabel');
    dateInput = document.getElementById('bookingDate');
    startTimeSelect = document.getElementById('startTime');
    endTimeSelect = document.getElementById('endTime');
    availableItemsContainer = document.getElementById('availableItems');
    bookingCartContainer = document.getElementById('bookingCart');
    validateBookingBtn = document.getElementById('validateBookingBtn');
    hiddenGroupIdInput = document.getElementById('editingGroupId');

    // Event listeners
    bookingModalElement.addEventListener('show.bs.modal', (event) => {
        if (event.relatedTarget) {
            setupModalContent(event);
        }
    });

    bookingModalElement.addEventListener('hidden.bs.modal', () => {
        cart = {};
        selectedDate = '';
        editingGroupId = null;
        editingCartKey = null;
        if (hiddenGroupIdInput) hiddenGroupIdInput.value = '';
    });

    if (startTimeSelect) startTimeSelect.addEventListener('change', handleTimeChange);
    if (endTimeSelect) endTimeSelect.addEventListener('change', handleTimeChange);
    
    // MODIFICATION CRITIQUE : Le bouton valider ajoute au panier au lieu d'appeler l'API
    if (validateBookingBtn) {
        validateBookingBtn.addEventListener('click', () => {
            if (editingGroupId) {
                // Si on modifie une réservation validée, on appelle l'API
                validateExistingReservation();
            } else {
                // Sinon on ajoute/met à jour le panier
                addToGlobalCart();
            }
        });
    }

    if (availableItemsContainer) {
        availableItemsContainer.addEventListener('click', (event) => {
            if (event.target.classList.contains('btn-add-to-cart')) {
                const button = event.target;
                addToCart(button.dataset.type, parseInt(button.dataset.id, 10), button.dataset.name, parseInt(button.dataset.maxQuantity, 10));
            }
        });
    }

    if (bookingCartContainer) {
        bookingCartContainer.addEventListener('click', (event) => {
            if (event.target.classList.contains('btn-remove-from-cart')) {
                removeFromCart(event.target.dataset.key);
            }
        });
    }
}

// ===================================================================
// FONCTION POUR MODIFIER UNE RÉSERVATION VALIDÉE (BDD)
// ===================================================================
async function validateExistingReservation() {
    if (!dateInput || !startTimeSelect || !endTimeSelect || !hiddenGroupIdInput) return;
    
    const reservationData = {
        date: dateInput.value,
        heure_debut: startTimeSelect.value,
        heure_fin: endTimeSelect.value,
        items: Object.values(cart),
        groupe_id: hiddenGroupIdInput.value
    };
    
    try {
        const response = await fetch('/api/creer_reservation', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json', 
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content') 
            },
            body: JSON.stringify(reservationData),
        });
        const result = await response.json();
        if (response.ok) {
            showToast(result.message || 'Opération réussie!', 'success');
            if (bookingModalInstance) {
                bookingModalInstance.hide();
            }
            location.reload();
        } else {
            throw new Error(result.error || 'Une erreur est survenue.');
        }
    } catch (error) {
        showToast(error.message, 'danger');
    }
}