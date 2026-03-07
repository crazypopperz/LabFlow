import { openReservationModal } from './booking-modal.js';
import { escapeHtml } from './cart-utils.js';
import { showToast } from './toast.js';

// ============================================================
// CONFIGURATION
// ============================================================
function getConfig() {
    const container = document.querySelector('.main-container');
    const startStr = container?.dataset.planningDebut || '08:00';
    const endStr = container?.dataset.planningFin || '18:00';
    const [startH, startM] = startStr.split(':').map(Number);
    const [endH, endM] = endStr.split(':').map(Number);
    return {
        startTotal: startH * 60 + startM,
        endTotal: endH * 60 + endM,
        startStr, endStr
    };
}

// ============================================================
// GÉNÉRATION DE LA GRILLE
// ============================================================
function renderGrid(config) {
    const container = document.getElementById('daily-grid-container');
    if (!container) return;

    const totalMinutes = config.endTotal - config.startTotal;
    const slotHeight = 60; // px par heure

    let html = '<div class="daily-grid" style="position: relative;">';

    // Lignes horaires
    for (let t = config.startTotal; t <= config.endTotal; t += 60) {
        const h = Math.floor(t / 60);
        const m = t % 60;
        const topPx = ((t - config.startTotal) / 60) * slotHeight;
        const label = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
        html += `
            <div class="schedule-row" style="position: absolute; top: ${topPx}px; left: 0; right: 0; height: ${slotHeight}px; display: flex; border-bottom: 1px solid #f0f0f0;">
                <div class="time-col" style="width: 70px; min-width: 70px; padding: 4px 8px; color: #888; font-size: 0.8rem;">${label}</div>
                <div class="events-col" style="flex: 1; position: relative; border-left: 1px solid #e0e0e0;"></div>
            </div>`;
    }

    // Zone événements superposée
    html += `<div id="events-layer" style="position: absolute; top: 0; left: 70px; right: 0; bottom: 0; pointer-events: none;"></div>`;
    html += '</div>';

    const totalHeight = ((config.endTotal - config.startTotal) / 60) * slotHeight + slotHeight;
    container.style.minHeight = `${totalHeight}px`;
    container.innerHTML = html;
}

// ============================================================
// RENDU DES ÉVÉNEMENTS
// ============================================================
function renderEvents(config) {
    const layer = document.getElementById('events-layer');
    if (!layer) return;

    const rawData = document.getElementById('reservations-data');
    if (!rawData) return;

    let reservations = [];
    try { reservations = JSON.parse(rawData.textContent); } catch (e) { return; }

    const slotHeight = 60;
    const uniqueGroupes = {};
    reservations.forEach(r => { uniqueGroupes[r.groupe_id] = r; });

    Object.values(uniqueGroupes).forEach(resa => {
        const [dH, dM] = resa.debut.split(':').map(Number);
        const [fH, fM] = resa.fin.split(':').map(Number);
        const debutTotal = dH * 60 + dM;
        const finTotal = fH * 60 + fM;

        // Clipper aux bornes du planning
        const clippedDebut = Math.max(debutTotal, config.startTotal);
        const clippedFin = Math.min(finTotal, config.endTotal);
        if (clippedDebut >= clippedFin) return;

        const topPx = ((clippedDebut - config.startTotal) / 60) * slotHeight;
        const heightPx = ((clippedFin - clippedDebut) / 60) * slotHeight;

        const el = document.createElement('div');
        el.className = 'event-item start';
        el.dataset.groupeId = resa.groupe_id;
        el.style.cssText = `
            position: absolute;
            top: ${topPx}px;
            left: 4px;
            right: 4px;
            height: ${Math.max(heightPx - 2, 20)}px;
            background: #3b82f6;
            color: white;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 0.8rem;
            cursor: pointer;
            pointer-events: all;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            z-index: 10;
        `;
        el.innerHTML = `
			<strong>${resa.debut} - ${resa.fin}</strong>
			<span style="display:block;">${escapeHtml(resa.nom_utilisateur)}</span>
			${resa.salle ? `<span style="display:block;font-size:0.75em;opacity:0.85;"><i class="bi bi-building me-1"></i>${escapeHtml(resa.salle)}</span>` : ''}
		`;
        layer.appendChild(el);
    });
}

// ============================================================
// TOOLTIP
// ============================================================
function initTooltip() {
    const tooltip = document.getElementById('reservation-tooltip');
    if (!tooltip) return;
    let activeTooltip = null;

    const deleteModalEl = document.getElementById('deleteConfirmModal');
    let deleteModalInstance = null;
    let groupIdToDelete = null;
    let confirmDeleteBtn = null;

    if (deleteModalEl) {
        deleteModalInstance = new bootstrap.Modal(deleteModalEl);
        confirmDeleteBtn = document.getElementById('btnConfirmDeleteAction');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', () => {
                if (groupIdToDelete) performDeletion(groupIdToDelete);
            });
        }
    }

    document.addEventListener('mouseover', async function(e) {
        const item = e.target.closest('.event-item');
        if (!item) return;
        const groupId = item.dataset.groupeId;
        if (!groupId) return;

		const rect = item.getBoundingClientRect();
		const tooltipLeft = rect.right + window.scrollX + 8;
		const tooltipTop = rect.top + window.scrollY;
		tooltip.style.left = `${Math.min(tooltipLeft, window.innerWidth - 320)}px`;
		tooltip.style.top = `${tooltipTop}px`;
        tooltip.innerHTML = '<div class="tooltip-loading"><div class="spinner-border spinner-border-sm"></div> Chargement...</div>';
        tooltip.classList.add('visible');
        activeTooltip = groupId;

        try {
            const response = await fetch(`/api/reservation_details/${groupId}`);
            if (!response.ok) throw new Error('Erreur réseau');
            const details = await response.json();
            if (activeTooltip !== groupId) return;

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

            let contentHtml = `
                <div class="tooltip-header">
                    <div>
                        <div class="tooltip-title">
                            ${escapeHtml(details.debut.substring(11, 16))} - ${escapeHtml(details.fin.substring(11, 16))}
                        </div>
                        <div class="small text-muted">
                            <i class="bi bi-person-circle me-1"></i>${escapeHtml(details.user_name)}
                        </div>
						${details.salle ? `<div class="small text-muted"><i class="bi bi-building me-1"></i>${escapeHtml(details.salle)}</div>` : ''}
                    </div>
                    ${buttonsHtml}
                </div>
                <ul class="tooltip-list">`;

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
                        else if (confirm("Supprimer ?")) performDeletion(groupIdToDelete);
                    });
                }
            }
        } catch (error) {
            console.error(error);
            tooltip.innerHTML = '<div class="tooltip-error">Erreur de chargement</div>';
        }
    });

    document.addEventListener('mouseout', function(e) {
        const item = e.target.closest('.event-item');
        if (!item) return;
        setTimeout(() => {
            if (!tooltip.matches(':hover')) {
                tooltip.classList.remove('visible');
                activeTooltip = null;
            }
        }, 300);
    });

    tooltip.addEventListener('mouseleave', function() {
        tooltip.classList.remove('visible');
        activeTooltip = null;
    });

    function performDeletion(groupId) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.disabled = true;
            confirmDeleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        }
        fetch('/api/supprimer_reservation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
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

        function resetDeleteBtn() {
            if (confirmDeleteBtn) {
                confirmDeleteBtn.disabled = false;
                confirmDeleteBtn.innerHTML = '<i class="bi bi-trash-fill me-2"></i>Supprimer';
            }
        }
    }
}

// ============================================================
// BOUTON NOUVELLE RÉSERVATION
// ============================================================
function initNewReservationBtn() {
    const btn = document.getElementById('new-reservation-btn');
    if (!btn) return;
    btn.addEventListener('click', function() {
        const container = document.querySelector('.main-container');
        const pageDate = container ? container.dataset.date : new Date().toISOString().split('T')[0];
        openReservationModal(pageDate);
    });
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    const config = getConfig();
    renderGrid(config);
    renderEvents(config);
    initTooltip();
    initNewReservationBtn();
});