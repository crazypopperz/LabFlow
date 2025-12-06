import { openReservationModal } from './booking-modal.js';

document.addEventListener("DOMContentLoaded", function () {
    const scheduleContainer = document.querySelector('.daily-schedule-wrapper');
    const tooltipElement = document.getElementById('reservation-tooltip');
    const dangerModalElement = document.getElementById('dangerModal');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    const mainContainer = document.querySelector('.main-container');

    if (!scheduleContainer || !tooltipElement || !dangerModalElement || !confirmDeleteBtn || !mainContainer) {
        console.warn("Éléments du calendrier manquants. Script calendar-daily.js arrêté.");
        return;
    }

    const dangerModal = bootstrap.Modal.getOrCreateInstance(dangerModalElement);
    let hideTooltipTimeout;
    let currentFetchController = null;
    let groupIdToDelete = null;

    // --- 1. RESTAURATION DE L'ÉDITION ---
    const editDataJSON = sessionStorage.getItem('editReservationData');
    if (editDataJSON) {
        try {
            const editData = JSON.parse(editDataJSON);
            openReservationModal(editData.date, editData.editingGroupId);
        } catch (e) {
            console.error("Erreur session storage:", e);
        } finally {
            sessionStorage.removeItem('editReservationData');
        }
    }

    // --- 2. FONCTION D'AFFICHAGE DU TOOLTIP ---
    const showTooltip = async (block, event) => {        
        clearTimeout(hideTooltipTimeout);
        
        const groupeId = block.dataset.groupeId;
        
        if (tooltipElement.classList.contains('visible') && tooltipElement.dataset.currentGroupeId === groupeId) {
            return;
        }

        if (currentFetchController) currentFetchController.abort();
        currentFetchController = new AbortController();

        tooltipElement.dataset.currentGroupeId = groupeId;
        
        tooltipElement.innerHTML = `
            <div class="tooltip-header">
                <span class="tooltip-title">Chargement...</span>
            </div>`;
        tooltipElement.classList.add('visible');
        
        positionTooltip(block);

        try {
            const response = await fetch(`/api/reservation_details/${groupeId}`, {
                signal: currentFetchController.signal
            });
            
            if (!response.ok) throw new Error(`Erreur ${response.status}`);
            
            const details = await response.json();
            
            if (tooltipElement.dataset.currentGroupeId !== groupeId) return;

            const isAdmin = mainContainer.dataset.isAdmin === 'true';
            const currentUserId = mainContainer.dataset.userId;
            const isMine = String(details.utilisateur_id) === String(currentUserId);

            let contentHtml = '<ul class="tooltip-list">';
            
            if (details.kits && Object.keys(details.kits).length > 0) {
                contentHtml += `<li class="text-primary fw-bold mt-2">Kits :</li>`;
                for (const kitId in details.kits) {
                    contentHtml += `<li>• ${details.kits[kitId].quantite} x ${details.kits[kitId].nom}</li>`;
                }
            }

            if (details.objets_manuels && details.objets_manuels.length > 0) {
                contentHtml += `<li class="text-primary fw-bold mt-2">Matériel :</li>`;
                details.objets_manuels.forEach(item => {
                    contentHtml += `<li>• ${item.quantite_reservee} x ${item.nom}</li>`;
                });
            }
            contentHtml += '</ul>';

            let buttonsHtml = '';
            const currentDateStr = mainContainer.dataset.date;
            
            if (isMine || isAdmin) {
                buttonsHtml = `
                    <div class="tooltip-actions">
                        <button class="btn-tooltip edit" data-groupe-id="${groupeId}" data-date="${currentDateStr}">Modifier</button>
                        <button class="btn-tooltip delete" data-groupe-id="${groupeId}">Supprimer</button>
                    </div>`;
            }

            tooltipElement.innerHTML = `
                <div class="tooltip-header">
                    <span class="tooltip-title">${details.nom_utilisateur}</span>
                    ${buttonsHtml}
                </div>
                <div class="tooltip-body">
                    <div class="mb-2 text-muted">
                        <i class="bi bi-clock"></i> ${details.debut_reservation.split('T')[1].slice(0,5)} - ${details.fin_reservation.split('T')[1].slice(0,5)}
                    </div>
                    ${contentHtml}
                </div>`;
            
            positionTooltip(block);

        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error(error);
            tooltipElement.innerHTML = `<div class="tooltip-header text-danger">Erreur de chargement</div>`;
        }
    };

    // --- 3. POSITIONNEMENT INTELLIGENT ---
    const positionTooltip = (eventBlock) => {
        const blockRect = eventBlock.getBoundingClientRect();
        const tooltipRect = tooltipElement.getBoundingClientRect();
        const margin = 10;

        let top = blockRect.bottom + margin;
        let left = blockRect.left + (blockRect.width / 2) - (tooltipRect.width / 2);

        if (left + tooltipRect.width > window.innerWidth - margin) {
            left = window.innerWidth - tooltipRect.width - margin;
        }

        if (left < margin) {
            left = margin;
        }

        if (top + tooltipRect.height > window.innerHeight - margin) {
            top = blockRect.top - tooltipRect.height - margin;
        }

        if (top < margin) {
            top = margin;
        }

        tooltipElement.style.top = `${top}px`;
        tooltipElement.style.left = `${left}px`;
    };

	// --- 4. GESTIONNAIRES D'ÉVÉNEMENTS ---

	let currentHoveredBlock = null;
	let switchTooltipTimeout = null;

	scheduleContainer.addEventListener('mouseenter', (e) => {
		const block = e.target.closest('.event-item');
		if (block) {
			// Annuler tout changement de tooltip en cours
			clearTimeout(switchTooltipTimeout);
			clearTimeout(hideTooltipTimeout);
			
			// Si c'est un nouveau bloc différent
			if (currentHoveredBlock !== block) {
				currentHoveredBlock = block;
				
				// Délai de 400ms avant de changer le tooltip
				switchTooltipTimeout = setTimeout(() => {
					showTooltip(block, e);
				}, tooltipElement.classList.contains('visible') ? 400 : 0);
				// Si pas de tooltip visible, afficher immédiatement
				// Sinon attendre 400ms (temps de traverser vers le tooltip)
			}
		}
	}, true);

	scheduleContainer.addEventListener('mouseleave', (e) => {
		const block = e.target.closest('.event-item');
		if (block && block === currentHoveredBlock) {
			currentHoveredBlock = null;
			
			// Attendre 600ms avant de fermer le tooltip
			hideTooltipTimeout = setTimeout(() => {
				if (!tooltipElement.matches(':hover')) {
					tooltipElement.classList.remove('visible');
					tooltipElement.dataset.currentGroupeId = '';
				}
			}, 300);
		}
	}, true);

	// Garder le tooltip ouvert si on est dessus
	tooltipElement.addEventListener('mouseenter', () => {
		clearTimeout(hideTooltipTimeout);
		clearTimeout(switchTooltipTimeout);
	});

	// Fermer le tooltip quand on sort
	tooltipElement.addEventListener('mouseleave', () => {
		currentHoveredBlock = null;
		hideTooltipTimeout = setTimeout(() => {
			tooltipElement.classList.remove('visible');
			tooltipElement.dataset.currentGroupeId = '';
		}, 200);
	});

	// Clics sur les boutons du tooltip
	tooltipElement.addEventListener('click', (e) => {
		const editBtn = e.target.closest('.btn-tooltip.edit');
		if (editBtn) {
			tooltipElement.classList.remove('visible');
			openReservationModal(editBtn.dataset.date, editBtn.dataset.groupeId);
			return;
		}

		const deleteBtn = e.target.closest('.btn-tooltip.delete');
		if (deleteBtn) {
			groupIdToDelete = deleteBtn.dataset.groupeId;
			const modalText = document.getElementById('dangerModalText');
			if (modalText) modalText.innerHTML = `Supprimer définitivement cette réservation ?`;
			
			tooltipElement.classList.remove('visible');
			dangerModal.show();
		}
	});
    // --- 5. BOUTON NOUVELLE RÉSERVATION ---
    const newReservationBtn = document.getElementById('new-reservation-btn');
    if (newReservationBtn) {
        newReservationBtn.addEventListener('click', () => {
            const dateStr = mainContainer.dataset.date;
            if (dateStr) {
                openReservationModal(dateStr);
            } else {
                console.error("Date introuvable dans data-date");
                alert("Erreur interne : Date introuvable.");
            }
        });
    }

    // --- 6. CONFIRMATION SUPPRESSION ---
    confirmDeleteBtn.addEventListener('click', async () => {
        if (!groupIdToDelete) return;
        confirmDeleteBtn.disabled = true;
        
        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            const response = await fetch('/api/supprimer_reservation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ groupe_id: groupIdToDelete })
            });

            if (response.ok) {
                window.location.reload();
            } else {
                alert("Erreur lors de la suppression");
            }
        } catch (error) {
            console.error(error);
            alert("Erreur réseau");
        } finally {
            confirmDeleteBtn.disabled = false;
            dangerModal.hide();
        }
    });
});