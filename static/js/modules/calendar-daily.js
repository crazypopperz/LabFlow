import { openReservationModal } from './booking-modal.js';
import { escapeHtml } from './cart-utils.js';
import { showToast } from './toast.js';

document.addEventListener('DOMContentLoaded', function() {
    const tooltip = document.getElementById('reservation-tooltip');
    let activeTooltip = null;

    // --- GESTION DE LA MODALE DE SUPPRESSION ---
    const deleteModalEl = document.getElementById('deleteConfirmModal');
    let deleteModalInstance = null;
    let confirmDeleteBtn = null;
    let groupIdToDelete = null;

    if (deleteModalEl) {
        deleteModalInstance = new bootstrap.Modal(deleteModalEl);
        confirmDeleteBtn = document.getElementById('btnConfirmDeleteAction');
        
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', () => {
                if (groupIdToDelete) {
                    performDeletion(groupIdToDelete);
                }
            });
        }
    }

    // 1. GESTION DU TOOLTIP AU SURVOL
    document.querySelectorAll('.event-item').forEach(item => {
        item.addEventListener('mouseenter', async function(e) {
            const groupId = this.dataset.groupeId;
            if (!groupId) return;

            // Positionnement initial
            const rect = this.getBoundingClientRect();
            tooltip.style.left = `${rect.left + window.scrollX}px`;
            tooltip.style.top = `${rect.bottom + window.scrollY + 5}px`;
            tooltip.innerHTML = '<div class="tooltip-loading"><div class="spinner-border spinner-border-sm"></div> Chargement...</div>';
            tooltip.classList.add('visible');
            activeTooltip = groupId;

            try {
                const response = await fetch(`/api/reservation_details/${groupId}`);
                if (!response.ok) throw new Error('Erreur réseau');
                const details = await response.json();

                if (activeTooltip !== groupId) return;

                // --- CONSTRUCTION DU HTML ---
                
                // 1. Boutons d'action (Seulement si autorisé)
                let buttonsHtml = '';
                if (details.can_edit) {
                    buttonsHtml = `
                        <div class="tooltip-buttons">
                            <button class="btn-edit-resa" data-groupe-id="${groupId}" data-date="${details.debut.substring(0, 10)}" title="Modifier">
                                <i class="bi bi-pencil-fill"></i>
                            </button>
                            <button class="btn-delete-resa text-danger" data-groupe-id="${groupId}" title="Supprimer">
                                <i class="bi bi-trash-fill"></i>
                            </button>
                        </div>`;
                }

                // 2. En-tête avec Nom et Heure
                let contentHtml = `
                    <div class="tooltip-header">
                        <div>
                            <div class="tooltip-title">
                                ${escapeHtml(details.debut.substring(11, 16))} - ${escapeHtml(details.fin.substring(11, 16))}
                            </div>
                            <div class="small text-muted">
                                <i class="bi bi-person-circle me-1"></i>${escapeHtml(details.user_name)}
                            </div>
                        </div>
                        ${buttonsHtml}
                    </div>
                    <ul class="tooltip-list">
                `;

                // 3. Liste des items
                const itemsList = details.items || details.objets || [];
                if (itemsList.length > 0) {
                    itemsList.forEach(obj => {
                        contentHtml += `<li>• ${escapeHtml(String(obj.quantite))} x ${escapeHtml(obj.nom)}</li>`;
                    });
                } else {
                    contentHtml += '<li>Aucun matériel</li>';
                }

                contentHtml += '</ul>';
                tooltip.innerHTML = contentHtml;

                // --- ATTACHEMENT ÉVÉNEMENTS (Si boutons présents) ---
                if (details.can_edit) {
                    const editBtn = tooltip.querySelector('.btn-edit-resa');
                    if (editBtn) {
                        editBtn.addEventListener('click', function() {
                            openReservationModal(this.dataset.date, this.dataset.groupeId);
                        });
                    }

                    const deleteBtn = tooltip.querySelector('.btn-delete-resa');
                    if (deleteBtn) {
                        deleteBtn.addEventListener('click', function() {
                            groupIdToDelete = this.dataset.groupeId;
                            if (deleteModalInstance) deleteModalInstance.show();
                            else if(confirm("Supprimer ?")) performDeletion(groupIdToDelete);
                        });
                    }
                }

            } catch (error) {
                console.error(error);
                tooltip.innerHTML = '<div class="tooltip-error">Erreur de chargement</div>';
            }
        });

        item.addEventListener('mouseleave', function() {
            setTimeout(() => {
                if (!tooltip.matches(':hover')) {
                    tooltip.classList.remove('visible');
                    activeTooltip = null;
                }
            }, 100);
        });
    });

    tooltip.addEventListener('mouseleave', function() {
        tooltip.classList.remove('visible');
        activeTooltip = null;
    });

    // 2. BOUTON "NOUVELLE RÉSERVATION"
    const newResaBtn = document.getElementById('new-reservation-btn');
    if (newResaBtn) {
        newResaBtn.addEventListener('click', function() {
            const container = document.querySelector('.main-container');
            const pageDate = container ? container.dataset.date : new Date().toISOString().split('T')[0];
            openReservationModal(pageDate);
        });
    }

    // 3. FONCTION DE SUPPRESSION
    function performDeletion(groupId) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        if (confirmDeleteBtn) {
            confirmDeleteBtn.disabled = true;
            confirmDeleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        }

        fetch('/api/supprimer_reservation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ groupe_id: groupId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                if (deleteModalInstance) deleteModalInstance.hide();
                showToast("Réservation supprimée", "success");
                setTimeout(() => window.location.reload(), 500);
            } else {
                showToast(data.error || "Erreur lors de la suppression", "error");
                resetDeleteBtn();
            }
        })
        .catch(err => {
            console.error(err);
            showToast("Erreur de communication", "error");
            resetDeleteBtn();
        });
    }

    function resetDeleteBtn() {
        if (confirmDeleteBtn) {
            confirmDeleteBtn.disabled = false;
            confirmDeleteBtn.innerHTML = '<i class="bi bi-trash-fill me-2"></i>Supprimer';
        }
    }
});