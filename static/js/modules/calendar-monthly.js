import { openReservationModal } from './booking-modal.js';

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('calendrier-container');
    if (!container) return;

    const monthYearElement = container.querySelector('#current-month-year');
    const gridElement = container.querySelector('.calendrier-grid');
    const prevBtn = container.querySelector('#prev-month-btn');
    const nextBtn = container.querySelector('#next-month-btn');

    let currentDate = new Date();
    let dayTooltip = null;

    // --- 1. API : Récupérer les chiffres du mois ---
    async function fetchReservations(year, month) {
        try {
            // month + 1 car JS est 0-indexé, Python 1-indexé
            const response = await fetch(`/api/reservations_par_mois/${year}/${month + 1}`);
            if (!response.ok) return {};
            return await response.json();
        } catch (error) {
            console.error("Erreur calendrier:", error);
            return {};
        }
    }

    // --- 2. TOOLTIP : Création et Affichage ---
    function createDayTooltip() {
        if (!dayTooltip) {
            dayTooltip = document.createElement('div');
            dayTooltip.className = 'day-tooltip';
            dayTooltip.style.display = 'none';
            document.body.appendChild(dayTooltip);
        }
        return dayTooltip;
    }

    async function showDayTooltip(dateKey, cellElement) {
        const tooltip = createDayTooltip();
        
        // Loader
        tooltip.innerHTML = '<div class="p-2 text-center"><div class="spinner-border spinner-border-sm text-light"></div></div>';
        tooltip.style.display = 'block';
        positionTooltip(tooltip, cellElement);

        try {
            // Appel à la route que tu as déjà : /api/reservations_jour/<date>
            const response = await fetch(`/api/reservations_jour/${dateKey}`);
            if (!response.ok) throw new Error('Erreur');
            
            const data = await response.json();
            const reservations = data.reservations || [];

            if (reservations.length === 0) {
                hideDayTooltip();
                return;
            }

            // Construction du contenu
            let html = `<div class="day-tooltip-header">${reservations.length} réservation(s)</div>`;
            html += '<ul class="day-tooltip-list">';
            
            reservations.slice(0, 5).forEach(r => {
                html += `<li><strong>${r.nom_utilisateur}</strong> <span class="opacity-75">${r.heure_debut}-${r.heure_fin}</span></li>`;
            });
            
            if (reservations.length > 5) {
                html += `<li class="text-center fst-italic small">+ ${reservations.length - 5} autres...</li>`;
            }
            html += '</ul>';
            
            tooltip.innerHTML = html;
            positionTooltip(tooltip, cellElement); // Repositionner après chargement du contenu
        } catch (error) {
            tooltip.innerHTML = '<div class="p-2 text-danger small">Erreur chargement</div>';
        }
    }

    function positionTooltip(tooltip, cellElement) {
        const rect = cellElement.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        
        // Centré au-dessus de la case
        let top = rect.top - tooltipRect.height - 8;
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);

        tooltip.style.top = `${top + window.scrollY}px`;
        tooltip.style.left = `${left + window.scrollX}px`;
    }

    function hideDayTooltip() {
        if (dayTooltip) dayTooltip.style.display = 'none';
    }

    // --- 3. RENDU DU CALENDRIER ---
    async function renderCalendar(date) {
        const year = date.getFullYear();
        const month = date.getMonth();

        monthYearElement.textContent = date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
        monthYearElement.style.textTransform = 'capitalize';
        
        gridElement.innerHTML = '<div class="text-center w-100 py-5"><div class="spinner-border text-primary"></div></div>';

        const reservations = await fetchReservations(year, month);
        
        // Date du jour (sans les heures pour comparaison stricte)
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        gridElement.innerHTML = '';

        // En-têtes
        ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'].forEach(d => {
            gridElement.innerHTML += `<div class="cal-header">${d}</div>`;
        });

        // Cases vides
        const firstDay = new Date(year, month, 1).getDay();
        const startDay = (firstDay === 0 ? 6 : firstDay - 1);
        for (let i = 0; i < startDay; i++) {
            gridElement.innerHTML += `<div class="cal-day empty"></div>`;
        }

        // Jours
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        for (let day = 1; day <= daysInMonth; day++) {
            // Date de la case en cours de construction
            const currentDayDate = new Date(year, month, day);
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            
            const count = reservations[dateStr] || 0;
            const isToday = currentDayDate.getTime() === today.getTime();
            const isPast = currentDayDate < today; // Vérification jour passé

            const cell = document.createElement('div');
            
            // Classes CSS conditionnelles
            let classes = 'cal-day';
            if (isToday) classes += ' today';
            if (isPast) classes += ' past-day'; // CSS à ajouter pour griser
            cell.className = classes;
            
            // Badge HTML
            let badgeHtml = '';
            if (count > 0) {
                let colorClass = count > 4 ? 'bg-danger' : (count > 2 ? 'bg-warning text-dark' : 'bg-info text-dark');
                badgeHtml = `<div class="reservation-badge ${colorClass}">${count} réserv.</div>`;
            }

            // Bouton "+" (Uniquement si jour futur ou aujourd'hui)
            let btnHtml = '';
            if (!isPast) {
                btnHtml = `
                    <button class="btn btn-sm btn-light btn-add-fast position-absolute top-0 end-0 m-1" 
                            style="display:none; width:24px; height:24px; padding:0;"
                            title="Réserver">
                        <i class="bi bi-plus"></i>
                    </button>
                `;
            }

            cell.innerHTML = `
                <div class="day-number">${day}</div>
                <div class="day-content">${badgeHtml}</div>
                ${btnHtml}
            `;

            // Événements (Clics désactivés pour le passé, sauf pour voir le détail si y'a des résas)
            if (!isPast || count > 0) {
                cell.addEventListener('click', () => window.location.href = `/jour/${dateStr}`);
            } else {
                cell.style.cursor = 'default';
            }

            // Gestion du bouton "+" (Seulement si pas passé)
            if (!isPast) {
                const btn = cell.querySelector('.btn-add-fast');
                
                cell.addEventListener('mouseenter', () => {
                    if(btn) btn.style.display = 'flex';
                });
                cell.addEventListener('mouseleave', () => {
                    if(btn) btn.style.display = 'none';
                });

                if (btn) {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        openReservationModal(dateStr);
                    });
                }
            }

            // Tooltip au survol (Toujours actif même pour le passé pour voir l'historique)
            if (count > 0) {
                let timer;
                cell.addEventListener('mouseenter', () => {
                    clearTimeout(timer);
                    showDayTooltip(dateStr, cell);
                });
                cell.addEventListener('mouseleave', () => {
                    timer = setTimeout(hideDayTooltip, 200);
                });
            }

            gridElement.appendChild(cell);
        }
    }

    // Navigation
    prevBtn.addEventListener('click', () => { currentDate.setMonth(currentDate.getMonth() - 1); renderCalendar(currentDate); });
    nextBtn.addEventListener('click', () => { currentDate.setMonth(currentDate.getMonth() + 1); renderCalendar(currentDate); });

    renderCalendar(currentDate);
});