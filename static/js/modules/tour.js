const tourSteps = [
    {
        element: '#btn-gerer-armoires', // Sélecteur CSS du bouton "Gérer les Armoires"
        title: 'Étape 1 : Les Armoires',
        content: 'Bienvenue ! Pour commencer, vous devez créer au moins une "armoire". C\'est l\'emplacement physique où sera rangé votre matériel.'
    },
    {
        element: '#btn-gerer-categories', // Sélecteur CSS du bouton "Gérer les Catégories"
        title: 'Étape 2 : Les Catégories',
        content: 'Excellent ! Maintenant, créez une "catégorie" pour classer vos objets (par exemple : Verrerie, Produits chimiques, Matériel électrique...).'
    },
    {
        element: '#btn-inventaire-complet', // Sélecteur CSS du bouton "Inventaire Complet"
        title: 'Prêt à commencer !',
        content: 'Parfait ! Vous avez maintenant tout ce qu\'il faut. Cliquez sur "Inventaire Complet" pour ajouter votre premier objet.'
    }
];

let currentStep = 0;

// On récupère les éléments HTML du tutoriel
const overlay = document.getElementById('tour-overlay');
const tooltip = document.getElementById('tour-tooltip');
const titleEl = document.getElementById('tour-title');
const contentEl = document.getElementById('tour-content');
const nextBtn = document.getElementById('tour-next-btn');
const skipBtn = document.getElementById('tour-skip-btn');

function showStep(stepIndex) {
    // On retire la surbrillance de l'étape précédente
    document.querySelectorAll('.tour-highlight').forEach(el => el.classList.remove('tour-highlight'));

    if (stepIndex >= tourSteps.length) {
        endTour();
        return;
    }

    const step = tourSteps[stepIndex];
    const targetElement = document.querySelector(step.element);

    if (!targetElement) {
        console.warn(`Élément du tutoriel non trouvé : ${step.element}`);
        endTour();
        return;
    }

    // On met à jour le contenu du tooltip
    titleEl.textContent = step.title;
    contentEl.textContent = step.content;

    // On affiche les éléments
    overlay.style.display = 'block';
    tooltip.style.display = 'block';

    // On met l'élément cible en surbrillance
    targetElement.classList.add('tour-highlight');

    // On positionne le tooltip à côté de l'élément
    const targetRect = targetElement.getBoundingClientRect();
    tooltip.style.top = `${targetRect.bottom + 10}px`;
    tooltip.style.left = `${targetRect.left}px`;
}

function endTour() {
    overlay.style.display = 'none';
    tooltip.style.display = 'none';
    document.querySelectorAll('.tour-highlight').forEach(el => el.classList.remove('tour-highlight'));
    // Optionnel : on pourrait envoyer une requête au serveur pour marquer le tutoriel comme "vu"
}

// On attache les événements aux boutons
nextBtn.addEventListener('click', () => {
    currentStep++;
    showStep(currentStep);
});

skipBtn.addEventListener('click', endTour);

// On exporte la fonction pour la démarrer depuis une autre page
export function startTour() {
    currentStep = 0;
    showStep(currentStep);
}