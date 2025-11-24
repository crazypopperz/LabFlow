document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('calendrier-container');
    if (!container) return;

    const monthYearElement = container.querySelector('#current-month-year');
    const gridElement = container.querySelector('.calendrier-grid');
    const prevBtn = container.querySelector('#prev-month-btn');
    const nextBtn = container.querySelector('#next-month-btn');

    let currentDate = new Date();

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

    async function renderCalendar(date) {
        const year = date.getFullYear();
        const month = date.getMonth();

        monthYearElement.textContent = date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
        gridElement.innerHTML = '';

        const joursSemaine = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
        joursSemaine.forEach(jour => {
            const dayHeader = document.createElement('div');
            // CORRECTION : Utilise la classe de votre CSS
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
            // CORRECTION : Utilise la classe de votre CSS
            emptyCell.className = 'day-cell other-month'; 
            gridElement.appendChild(emptyCell);
        }

        const reservations = await fetchReservations(year, month);
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        for (let day = 1; day <= daysInMonth; day++) {
            const dayCell = document.createElement('a');
            // CORRECTION : Utilise les classes de votre CSS
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

            // CORRECTION : Utilise la classe de votre CSS
            dayCell.innerHTML = `<div class="day-number">${day}</div>`; 

            const dateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            if (reservations[dateKey]) {
                const dot = document.createElement('div');
                // CORRECTION : Utilise la classe de votre CSS
                dot.className = 'activity-dot'; 
                dayCell.appendChild(dot);
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