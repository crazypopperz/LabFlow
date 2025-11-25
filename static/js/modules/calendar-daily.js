import { openReservationModal } from './booking-modal.js';

document.addEventListener("DOMContentLoaded", function () {
    const scheduleContainer = document.querySelector('.daily-schedule');
    const tooltipElement = document.getElementById('reservation-tooltip');
    const dangerModalElement = document.getElementById('dangerModal');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

    if (!scheduleContainer || !tooltipElement || !dangerModalElement || !confirmDeleteBtn) {
        return;
    }

    const dangerModal = bootstrap.Modal.getOrCreateInstance(dangerModalElement);
    let hideTooltipTimeout;
    let currentFetchController = null;
    let groupIdToDelete = null;

    // --- RESTAURATION DE L'ÉDITION (SessionStorage) ---
    const editDataJSON = sessionStorage.getItem('editReservationData');
    if (editDataJSON) {
        try {
            const editData = JSON.parse(editDataJSON);
            openReservationModal(editData.date, editData.editingGroupId);
        } catch (e) {
            console.error("Erreur lors de la lecture des données d'édition:", e);
        } finally {
            sessionStorage.removeItem('editReservationData');
        }
    }

    // --- AFFICHAGE DU TOOLTIP ---
    const showTooltip = async (block) => {
        clearTimeout(hideTooltipTimeout);
        
        const groupeId = block.dataset.groupeId;
        if (!groupeId || (tooltipElement.classList.contains('visible') && tooltipElement.dataset.currentGroupeId === groupeId)) {
            return;
        }

        // Annuler la requête précédente si elle existe
        if (currentFetchController) {
            currentFetchController.abort();
        }
        currentFetchController = new AbortController();

        tooltipElement.dataset.currentGroupeId = groupeId;
        tooltipElement.innerHTML = '<div class="tooltip-header"><span class="tooltip-title">Chargement...</span></div>';
        tooltipElement.classList.add('visible');

        try {
            const response = await fetch(`/api/reservation_details/${groupeId}`, {
                signal: currentFetchController.signal
            });
            
            if (!response.ok) throw new Error(`Erreur serveur: ${response.status}`);
            
            const details = await response.json();
            
            // Vérifier que c'est toujours la bonne réservation
            if (tooltipElement.dataset.currentGroupeId !== groupeId) {
                return;
            }

            const container = document.querySelector('.main-container');
            const isAdmin = container?.dataset.isAdmin === 'true';
            const currentUserId = container?.dataset.userId;
            const isMine = String(details.utilisateur_id) === String(currentUserId);

            // Construire la liste du matériel
            let listItems = '';
            const kits = details.kits || {};
            const objetsManuels = details.objets_manuels || [];

            if (Object.keys(kits).length > 0) {
                listItems += `<li><strong>Kits :</strong></li><ul>`;
                for (const kitId in kits) {
                    listItems += `<li>${kits[kitId].quantite} x ${kits[kitId].nom}</li>`;
                }
                listItems += `</ul>`;
            }

            if (objetsManuels.length > 0) {
                listItems += `<li><strong>Matériel ajouté :</strong></li><ul>`;
                objetsManuels.forEach(item => {
                    listItems += `<li>${item.quantite_reservee} x ${item.nom}</li>`;
                });
                listItems += `</ul>`;
            }

            // Boutons d'action si autorisé
            let buttonsHtml = '';
            if (isMine || isAdmin) {
                const pathParts = window.location.pathname.split('/');
                const currentDateStr = pathParts[pathParts.length - 1];
                buttonsHtml += `<button class="btn-edit-resa" data-groupe-id="${groupeId}" data-date="${currentDateStr}">Modifier</button>`;
                buttonsHtml += `<button class="btn-delete-resa" data-groupe-id="${groupeId}">Supprimer</button>`;
            }

            tooltipElement.innerHTML = `
                <div class="tooltip-header">
                    <span class="tooltip-title">Réservation de <strong>${details.nom_utilisateur}</strong></span>
                    <div class="tooltip-buttons">${buttonsHtml}</div>
                </div>
                <ul class="tooltip-list">${listItems || '<li>Aucun matériel spécifique.</li>'}</ul>`;

            positionTooltip(block);

        } catch (error) {
            if (error.name === 'AbortError') {
                return;
            }
            console.error("Erreur lors de la récupération des détails:", error);
            tooltipElement.innerHTML = `<div class="tooltip-header"><span class="tooltip-title">Erreur de chargement</span></div>`;
            positionTooltip(block);
        }
    };

    // --- POSITIONNEMENT DU TOOLTIP ---
    const positionTooltip = (block) => {
        requestAnimationFrame(() => {
            const blockRect = block.getBoundingClientRect();
            const tooltipRect = tooltipElement.getBoundingClientRect();
            const margin = 12;

            // Positionner en haut ou en bas selon l'espace disponible
            if ((window.innerHeight - blockRect.bottom) > tooltipRect.height + margin) {
                tooltipElement.className = 'tooltip tooltip-on-bottom visible';
                tooltipElement.style.top = `${blockRect.bottom + margin}px`;
            } else {
                tooltipElement.className = 'tooltip tooltip-on-top visible';
                tooltipElement.style.top = `${blockRect.top - tooltipRect.height - margin}px`;
            }

            // Centrer horizontalement avec limites d'écran
            let leftPos = blockRect.left + (blockRect.width / 2) - (tooltipRect.width / 2);
            leftPos = Math.max(10, Math.min(leftPos, window.innerWidth - tooltipRect.width - 10));
            tooltipElement.style.left = `${leftPos}px`;
        });
    };

    // --- MASQUER LE TOOLTIP AVEC DÉLAI ---
    const startHideTooltipTimer = () => {
        hideTooltipTimeout = setTimeout(() => {
            tooltipElement.classList.remove('visible');
            tooltipElement.dataset.currentGroupeId = '';
            
            if (currentFetchController) {
                currentFetchController.abort();
                currentFetchController = null;
            }
        }, 400);
    };

    // --- ÉVÉNEMENTS SOURIS SUR LES BLOCS ---
    scheduleContainer.addEventListener('mouseenter', (e) => {
        const block = e.target.closest('.event-block');
        if (block) {
            showTooltip(block);
        }
    }, true);

    scheduleContainer.addEventListener('mouseleave', (e) => {
        const block = e.target.closest('.event-block');
        if (block) {
            startHideTooltipTimer();
        }
    }, true);

    // --- ÉVÉNEMENTS SOURIS SUR LE TOOLTIP ---
    tooltipElement.addEventListener('mouseenter', () => {
        clearTimeout(hideTooltipTimeout);
    });

    tooltipElement.addEventListener('mouseleave', startHideTooltipTimer);

    // --- CLICS DANS LE TOOLTIP ---
    tooltipElement.addEventListener('click', (e) => {
        const editBtn = e.target.closest('.btn-edit-resa');
        if (editBtn) {
            tooltipElement.classList.remove('visible');
            tooltipElement.dataset.currentGroupeId = '';
            openReservationModal(editBtn.dataset.date, editBtn.dataset.groupeId);
            return;
        }

        const deleteBtn = e.target.closest('.btn-delete-resa');
        if (deleteBtn) {
            groupIdToDelete = deleteBtn.dataset.groupeId;
            
            const modalText = dangerModalElement.querySelector('.modal-body p');
            if (modalText) {
                modalText.innerHTML = `Êtes-vous sûr de vouloir supprimer cette réservation ?<br>Cette action est irréversible.`;
            }

            tooltipElement.classList.remove('visible');
            tooltipElement.dataset.currentGroupeId = '';
            dangerModal.show();
        }
    });

    // --- CONFIRMATION DE SUPPRESSION ---
    confirmDeleteBtn.addEventListener('click', async () => {
        if (!groupIdToDelete) {
            console.warn('Aucun groupe_id à supprimer');
            return;
        }

        // Désactiver le bouton pendant la requête
        confirmDeleteBtn.disabled = true;
        const originalText = confirmDeleteBtn.textContent;
        confirmDeleteBtn.textContent = 'Suppression...';

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            
            if (!csrfToken) {
                throw new Error('Token CSRF introuvable');
            }

            const response = await fetch('/api/supprimer_reservation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: JSON.stringify({ groupe_id: groupIdToDelete })
            });

            // Gérer les redirections (session expirée)
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ 
                    error: `Erreur HTTP ${response.status}` 
                }));
                throw new Error(errorData.error || 'La suppression a échoué');
            }
            
            const result = await response.json();
            
            if (result.success) {
                dangerModal.hide();
                dangerModalElement.addEventListener('hidden.bs.modal', () => {
                    window.location.reload();
                }, { once: true });
            } else {
                throw new Error(result.error || 'Une erreur est survenue');
            }

        } catch (error) {
            console.error('Erreur lors de la suppression:', error);
            dangerModal.hide();
            
            setTimeout(() => {
                alert(`Impossible de supprimer la réservation :\n${error.message}`);
            }, 300);

        } finally {
            confirmDeleteBtn.disabled = false;
            confirmDeleteBtn.textContent = originalText;
            groupIdToDelete = null;
        }
    });

    // --- BOUTON NOUVELLE RÉSERVATION ---
    const newReservationBtn = document.getElementById('new-reservation-btn');
    if (newReservationBtn) {
        const pathParts = window.location.pathname.split('/');
        const dateStr = pathParts[pathParts.length - 1];
        newReservationBtn.addEventListener('click', () => {
            openReservationModal(dateStr);
        });
    }
});