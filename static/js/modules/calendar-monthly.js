document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('calendrier-container');
    if (!container) return;

    const monthYearElement = container.querySelector('#current-month-year');
    const gridElement = container.querySelector('.calendrier-grid');
    const prevBtn = container.querySelector('#prev-month-btn');
    const nextBtn = container.querySelector('#next-month-btn');

    let currentDate = new Date();
    let dayTooltip = null;

    async function fetchReservations(year, month) {
        try {
            const response = await fetch(`/api/reservations_par_mois/${year}/${month + 1}`);
            if (!response.ok) throw new Error('Erreur réseau.');
            return await response.json();
        } catch (error) {
            console.error(error);
            return {};
        }
    }

    // Créer le tooltip pour les jours
    function createDayTooltip() {
        if (!dayTooltip) {
            dayTooltip = document.createElement('div');
            dayTooltip.className = 'day-tooltip';
            dayTooltip.style.display = 'none';
            document.body.appendChild(dayTooltip);
        }
        return dayTooltip;
    }

    // Afficher le tooltip avec les réservations du jour
    async function showDayTooltip(dateKey, cellElement) {
        const tooltip = createDayTooltip();
        
        tooltip.innerHTML = '<div class="tooltip-loading">Chargement...</div>';
        tooltip.style.display = 'block';
        positionTooltip(tooltip, cellElement);

        try {
            const response = await fetch(`/api/reservations_jour/${dateKey}`);
            if (!response.ok) throw new Error('Erreur');
            
            const data = await response.json();
            const reservations = data.reservations || [];

            const count = reservations.length;
			const label = count > 1 ? 'réservations' : 'réservation';
			let html = `<div class="day-tooltip-header"><strong>${count} ${label}</strong></div>`;
            html += '<ul class="day-tooltip-list">';
            
            reservations.slice(0, 5).forEach(r => {
                html += `<li><span class="res-user">${r.nom_utilisateur}</span> <span class="res-time">${r.heure_debut} - ${r.heure_fin}</span></li>`;
            });
            
            if (reservations.length > 5) {
                html += `<li class="more-indicator">+ ${reservations.length - 5} autre(s)...</li>`;
            }
            
            html += '</ul><div class="day-tooltip-footer">Cliquer pour voir le détail</div>';
            
            tooltip.innerHTML = html;
            positionTooltip(tooltip, cellElement);
        } catch (error) {
            tooltip.innerHTML = '<div class="tooltip-error">Erreur de chargement</div>';
        }
    }

    // Positionner le tooltip
    function positionTooltip(tooltip, cellElement) {
        const cellRect = cellElement.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        
        let top = cellRect.bottom + 10;
        let left = cellRect.left + (cellRect.width / 2) - (tooltipRect.width / 2);

        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }
        if (left < 10) {
            left = 10;
        }
        if (top + tooltipRect.height > window.innerHeight - 10) {
            top = cellRect.top - tooltipRect.height - 10;
        }

        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;
    }

    // Masquer le tooltip
    function hideDayTooltip() {
        if (dayTooltip) {
            dayTooltip.style.display = 'none';
        }
    }

    async function renderCalendar(date) {
        const year = date.getFullYear();
        const month = date.getMonth();

        monthYearElement.textContent = date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
        gridElement.innerHTML = '';

        const joursSemaine = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
        joursSemaine.forEach(jour => {
            const dayHeader = document.createElement('div');
            dayHeader.className = 'day-name';
            dayHeader.textContent = jour;
            gridElement.appendChild(dayHeader);
        });

        const firstDayOfMonth = new Date(year, month, 1);
        const lastDayOfMonth = new Date(year, month + 1, 0);
        const daysInMonth = lastDayOfMonth.getDate();
        let dayOfWeek = firstDayOfMonth.getDay();
        dayOfWeek = (dayOfWeek === 0) ? 6 : dayOfWeek - 1;

        for (let i = 0; i < dayOfWeek; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.className = 'day-cell other-month';
            gridElement.appendChild(emptyCell);
        }

        const reservations = await fetchReservations(year, month);
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        for (let day = 1; day <= daysInMonth; day++) {
            const dayCell = document.createElement('a');
            dayCell.className = 'day-cell';

            const currentDateInLoop = new Date(year, month, day);
            currentDateInLoop.setHours(0, 0, 0, 0);

            if (currentDateInLoop.getTime() === today.getTime()) {
                dayCell.classList.add('today');
            }

            if (currentDateInLoop < today) {
                dayCell.classList.add('past-day');
            } else {
                dayCell.classList.add('can-reserve');
                const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                dayCell.href = `/jour/${dateStr}`;
            }

            dayCell.innerHTML = `<div class="day-number">${day}</div>`;

            const dateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            
            if (reservations[dateKey]) {
                const count = reservations[dateKey];
                
                // Badge avec nombre au lieu du point
                const badge = document.createElement('div');
                badge.className = 'reservation-badge';
                badge.textContent = count;
                badge.dataset.count = count;
                dayCell.appendChild(badge);

                // Event listeners pour le tooltip
                let hideTimeout;
                
                dayCell.addEventListener('mouseenter', (e) => {
                    clearTimeout(hideTimeout);
                    showDayTooltip(dateKey, dayCell);
                });

                dayCell.addEventListener('mouseleave', () => {
                    hideTimeout = setTimeout(() => {
                        if (dayTooltip && !dayTooltip.matches(':hover')) {
                            hideDayTooltip();
                        }
                    }, 300);
                });

                if (dayTooltip) {
                    dayTooltip.addEventListener('mouseenter', () => {
                        clearTimeout(hideTimeout);
                    });

                    dayTooltip.addEventListener('mouseleave', () => {
                        hideDayTooltip();
                    });
                }
            }

            gridElement.appendChild(dayCell);
        }
    }

    prevBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar(currentDate);
    });

    nextBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar(currentDate);
    });

    renderCalendar(currentDate);
});