// static/js/modules/tour.js

// =================================================================
// CONFIGURATION DES ÉTAPES
// =================================================================
const steps = [
    {
        element: null,
        title: "Bienvenue sur Scientral ! 👋",
        content: "Prenons une minute pour découvrir votre nouvel outil de gestion de laboratoire. C'est parti !"
    },
    {
        element: "#search-wrapper-dropdown",
        title: "Recherche Intelligente 🔍",
        content: "Tapez le nom d'un objet ici pour le trouver instantanément, où que vous soyez dans l'application."
    },
    {
        element: "a[href*='/panier']",
        title: "Votre Panier 🛒",
        content: "C'est ici que vous retrouverez vos réservations en cours. La pastille rouge vous indique le nombre d'objets."
    },
    {
        element: "a[href*='/alertes']",
        title: "Centre d'Alertes 🔔",
        content: "Produits périmés, stock critique ou suggestions de commande : tout ce qui demande votre attention est ici."
    },
    {
        element: ".dashboard-container .row.g-4",
        title: "Tableau de Bord 📊",
        content: "Une vue d'ensemble complète : suggestions, budget, alertes et vos réservations à venir."
    },
    {
        element: ".footer-nav",
        title: "Besoin d'aide ? 🆘",
        content: "Retrouvez la documentation, le support technique et les mentions légales tout en bas de chaque page."
    }
];

// =================================================================
// VARIABLES D'ÉTAT
// =================================================================
let currentStep = 0;
const overlay = document.getElementById('tour-overlay');
const tooltip = document.getElementById('tour-tooltip');
const titleEl = document.getElementById('tour-title');
const contentEl = document.getElementById('tour-content');
const nextBtn = document.getElementById('tour-next-btn');
const skipBtn = document.getElementById('tour-skip-btn');

// =================================================================
// FONCTION PRINCIPALE (EXPORTÉE)
// =================================================================
export function startTour(force = false) {
    if (!overlay || !tooltip) {
        console.warn("Éléments du tour introuvables.");
        return;
    }

    if (!force && localStorage.getItem('labflow_tour_seen') === 'true') {
        return;
    }
    
    currentStep = 0;
    
    nextBtn.onclick = nextStep;
    skipBtn.onclick = endTour;
    
    overlay.classList.add('active');
    showStep();
}

// =================================================================
// LOGIQUE INTERNE
// =================================================================
function showStep() {
    const step = steps[currentStep];
    
    // Nettoyage
    document.querySelectorAll('.tour-highlight').forEach(el => el.classList.remove('tour-highlight'));
    
    // Contenu
    titleEl.textContent = step.title;
    contentEl.textContent = step.content;
    nextBtn.textContent = (currentStep === steps.length - 1) ? "C'est fini !" : "Suivant";

    // Positionnement
    if (step.element) {
        const target = document.querySelector(step.element);
        
        if (target) {
            target.classList.add('tour-highlight');
            
            // Scroll doux et centré
            target.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Calculs de position
            const rect = target.getBoundingClientRect();
            const tooltipRect = tooltip.getBoundingClientRect();
            
            // Position par défaut : En dessous, centré horizontalement
            let top = rect.bottom + 15;
            let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
            
            // --- CORRECTION INTELLIGENTE DES DÉBORDEMENTS ---
            
            // 1. Si ça dépasse en bas de l'écran -> On met au-dessus
            if (top + tooltipRect.height > window.innerHeight) {
                top = rect.top - tooltipRect.height - 15;
            }

            // 2. Si ça dépasse en haut de l'écran (ex: Tableau de bord trop haut) -> On force en dessous
            // (On ajoute window.scrollY pour avoir la position absolue dans la page)
            const absoluteTop = top + window.scrollY;
            const navbarHeight = 80; // Marge de sécurité pour le header fixe

            if (top < navbarHeight) {
                // Si le calcul "au-dessus" fait sortir la bulle en haut, on la remet en dessous
                // ou on la centre sur l'écran si l'élément est géant
                if (rect.height > window.innerHeight / 2) {
                    // Cas du grand tableau de bord : On centre la bulle sur l'écran
                    top = (window.innerHeight / 2) - (tooltipRect.height / 2);
                    tooltip.style.position = 'fixed'; // On fixe pour ce cas
                } else {
                    top = rect.bottom + 15;
                    tooltip.style.position = 'absolute';
                }
            } else {
                tooltip.style.position = 'absolute';
            }

            // 3. Si ça dépasse à gauche ou à droite
            if (left < 10) left = 10;
            if (left + tooltipRect.width > window.innerWidth) {
                left = window.innerWidth - tooltipRect.width - 10;
            }

            // Application
            // Si position est fixed (cas spécial), on n'ajoute pas scrollY
            if (tooltip.style.position === 'fixed') {
                tooltip.style.top = `${top}px`;
            } else {
                tooltip.style.top = `${top + window.scrollY}px`;
            }
            
            tooltip.style.left = `${left + window.scrollX}px`;
            tooltip.style.transform = 'none';
            
        } else {
            nextStep();
            return;
        }
    } else {
        // Étape centrée (Bienvenue)
        tooltip.style.position = 'fixed';
        tooltip.style.top = '50%';
        tooltip.style.left = '50%';
        tooltip.style.transform = 'translate(-50%, -50%)';
    }

    tooltip.classList.add('active');
}

function nextStep() {
    currentStep++;
    if (currentStep >= steps.length) {
        endTour();
    } else {
        showStep();
    }
}

function endTour() {
    overlay.classList.remove('active');
    tooltip.classList.remove('active');
    document.querySelectorAll('.tour-highlight').forEach(el => el.classList.remove('tour-highlight'));
    
    localStorage.setItem('labflow_tour_seen', 'true');

    // --- CORRECTION : REMONTER EN HAUT DE PAGE ---
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}