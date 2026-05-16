
# fix_recurrence.py
# Réintègre le module de récurrence perdu lors du merge du 5 avril

# 1. Injecter le bloc récurrence dans _modals.html après le select salle
modals = open('templates/_modals.html', encoding='utf-8').read()

old = """                        </div>
                        <div id="availableItems">"""

recurrence_block = """                        </div>

                        <!-- Récurrence -->
                        <div class="mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="recurrenceToggle">
                                <label class="form-check-label fw-bold small text-uppercase text-muted" for="recurrenceToggle">
                                    <i class="bi bi-arrow-repeat me-1"></i>Répéter
                                </label>
                            </div>
                            <div id="recurrenceOptions" style="display:none;" class="mt-2 p-3 bg-white rounded-3 border">
                                <div class="mb-2">
                                    <label class="form-label small fw-bold">Fréquence</label>
                                    <select class="form-select form-select-sm" id="recurrenceType">
                                        <option value="hebdo">Chaque semaine</option>
                                        <option value="quotidien_ouvre">Chaque jour ouvré</option>
                                        <option value="bi_hebdo">Toutes les 2 semaines</option>
                                        <option value="mensuel">Chaque mois</option>
                                    </select>
                                </div>
                                <div class="mb-2">
                                    <label class="form-label small fw-bold">Fin de répétition</label>
                                    <div class="d-flex gap-3 mb-2">
                                        <div class="form-check">
                                            <input class="form-check-input" type="radio" name="recurrenceLimite" id="limiteDate" value="date" checked>
                                            <label class="form-check-label small" for="limiteDate">Jusqu'au...</label>
                                        </div>
                                        <div class="form-check">
                                            <input class="form-check-input" type="radio" name="recurrenceLimite" id="limiteOccurrences" value="occurrences">
                                            <label class="form-check-label small" for="limiteOccurrences">Nombre de répétitions</label>
                                        </div>
                                    </div>
                                    <input type="date" id="recurrenceDateFin" class="form-control form-control-sm">
                                    <input type="number" id="recurrenceNbOccurrences" class="form-control form-control-sm"
                                        style="display:none;" min="2" max="52" value="4">
                                    <div class="text-muted small mt-1" id="occurrencesHelp" style="display:none;">
                                        <i class="bi bi-info-circle me-1"></i>Inclut la réservation en cours. Ex: 4 = aujourd'hui + 3 répétitions.
                                    </div>
                                </div>
                                <div id="recurrencePreview" class="small text-primary fst-italic mt-1"></div>
                            </div>
                        </div>

                        <div id="availableItems">"""

if old in modals:
    modals = modals.replace(old, recurrence_block)
    open('templates/_modals.html', 'w', encoding='utf-8').write(modals)
    print("OK — récurrence injectée dans _modals.html")
else:
    print("ERREUR _modals.html — bloc non trouvé")
    idx = modals.find('availableItems')
    print(repr(modals[idx-100:idx+50]))

# 2. Injecter les fonctions récurrence dans booking-modal.js
js = open('static/js/modules/booking-modal.js', encoding='utf-8').read()

recurrence_js = """
// ============================================================
// RÉCURRENCE
// ============================================================
function initRecurrence() {
    const toggle = document.getElementById('recurrenceToggle');
    const options = document.getElementById('recurrenceOptions');
    const limiteDate = document.getElementById('limiteDate');
    const limiteOcc = document.getElementById('limiteOccurrences');
    const dateFinInput = document.getElementById('recurrenceDateFin');
    const nbOccInput = document.getElementById('recurrenceNbOccurrences');
    if (!toggle) return;

    toggle.addEventListener('change', () => {
        options.style.display = toggle.checked ? 'block' : 'none';
        updateRecurrencePreview();
    });

    document.querySelectorAll('input[name="recurrenceLimite"]').forEach(radio => {
        radio.addEventListener('change', () => {
            dateFinInput.style.display = limiteDate.checked ? 'block' : 'none';
            nbOccInput.style.display = limiteOcc.checked ? 'block' : 'none';
            const help = document.getElementById('occurrencesHelp');
            if (help) help.style.display = limiteOcc.checked ? 'block' : 'none';
            updateRecurrencePreview();
        });
    });

    dateFinInput.addEventListener('change', updateRecurrencePreview);
    nbOccInput.addEventListener('input', () => {
        const help = document.getElementById('occurrencesHelp');
        if (help) help.style.display = nbOccInput.style.display !== 'none' ? 'block' : 'none';
        updateRecurrencePreview();
    });
    document.getElementById('recurrenceType')?.addEventListener('change', updateRecurrencePreview);
}

function updateRecurrencePreview() {
    const preview = document.getElementById('recurrencePreview');
    if (!preview) return;
    const type = document.getElementById('recurrenceType')?.value;
    const limiteDate = document.getElementById('limiteDate')?.checked;
    const dateFin = document.getElementById('recurrenceDateFin')?.value;
    const nbOcc = document.getElementById('recurrenceNbOccurrences')?.value;
    const labels = {
        'hebdo': 'chaque semaine',
        'quotidien_ouvre': 'chaque jour ouvré',
        'bi_hebdo': 'toutes les 2 semaines',
        'mensuel': 'chaque mois'
    };
    let text = 'Réservation répétée ' + (labels[type] || '');
    if (limiteDate && dateFin) text += ' jusqu\\'au ' + dateFin;
    else if (!limiteDate && nbOcc) text += ' pendant ' + nbOcc + ' occurrences';
    preview.textContent = text;
}

function getRecurrenceData() {
    const toggle = document.getElementById('recurrenceToggle');
    if (!toggle?.checked) return null;
    const limiteDate = document.getElementById('limiteDate')?.checked;
    return {
        type: document.getElementById('recurrenceType')?.value,
        date_fin: limiteDate ? document.getElementById('recurrenceDateFin')?.value : null,
        nb_occurrences: !limiteDate ? parseInt(document.getElementById('recurrenceNbOccurrences')?.value) : null
    };
}

"""

old_dom = "document.addEventListener('DOMContentLoaded', initBookingModal);"

if old_dom in js:
    js = js.replace(old_dom, recurrence_js + old_dom)
    # Ajouter initRecurrence() dans initBookingModal
    js = js.replace('    setupDelegatedEvents();\n}', '    setupDelegatedEvents();\n    initRecurrence();\n}')
    open('static/js/modules/booking-modal.js', 'w', encoding='utf-8').write(js)
    print("OK — fonctions récurrence injectées dans booking-modal.js")
else:
    print("ERREUR booking-modal.js — DOMContentLoaded non trouvé")
