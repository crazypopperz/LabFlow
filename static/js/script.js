// =================================================================
// FONCTION GLOBALE POUR AFFICHER LA MODALE D'INFORMATION
// =================================================================
function showInfoModal(title, message) {
    const modal = document.getElementById('info-modal');
    if (modal) {
        const modalTitle = modal.querySelector('#info-modal-title span');
        const modalText = modal.querySelector('#info-modal-text');
        if (modalTitle && modalText) {
            modalTitle.textContent = title;
            modalText.textContent = message;
            modal.style.display = 'flex';
        }
    }
}

// =================================================================
// POINT D'ENTRÉE UNIQUE : TOUT LE CODE EST DANS CE BLOC
// =================================================================
document.addEventListener("DOMContentLoaded", function () {

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    // =================================================================
	// SECTION 1 : LOGIQUE DE TRI ET PAGINATION DYNAMIQUE (AJAX)
	// =================================================================
	const dynamicContent = document.getElementById('dynamic-content');
	if (dynamicContent) {
		const searchInput = document.getElementById('search-input');
		const armoireFilter = document.getElementById('filtre-armoire');
		const categorieFilter = document.getElementById('filtre-categorie');
		const etatFilter = document.getElementById('filtre-etat');
		let searchTimeout;

		function fetchDynamicContent(page = 1, sortBy = null, direction = null) {
			const currentSortBy = sortBy || dynamicContent.dataset.sortBy || 'nom';
			const currentDirection = direction || dynamicContent.dataset.direction || 'asc';
			
			// --- DÉBUT DE LA CORRECTION ---
			// On crée un objet pour gérer tous les paramètres de l'URL
			const params = new URLSearchParams({
				page: page,
				sort_by: currentSortBy,
				direction: currentDirection
			});

			// On ajoute les filtres s'ils ont une valeur
			if (searchInput && searchInput.value) {
				params.set('q', searchInput.value);
			}
			if (armoireFilter && armoireFilter.value) {
				params.set('armoire', armoireFilter.value);
			}
			if (categorieFilter && categorieFilter.value) {
				params.set('categorie', categorieFilter.value);
			}
			if (etatFilter && etatFilter.value) {
				params.set('etat', etatFilter.value);
			}

			// On construit l'URL finale avec TOUS les paramètres
			const apiUrl = `/api/inventaire/?${params.toString()}`;

			fetch(apiUrl)
			.then(response => response.json())
			.then(data => {
				dynamicContent.innerHTML = data.html;
				dynamicContent.dataset.sortBy = currentSortBy;
				dynamicContent.dataset.direction = currentDirection;
			})
			.catch(error => {
				console.error("Erreur lors de la mise à jour du contenu:", error);
				dynamicContent.innerHTML = "<p>Erreur de chargement des données. Cette fonctionnalité est peut-être en cours de migration.</p>";
			});
		}

		function debounceFetch() {
			clearTimeout(searchTimeout);
			searchTimeout = setTimeout(() => fetchDynamicContent(1), 300);
		}

		if (searchInput) searchInput.addEventListener('input', debounceFetch);
		if (armoireFilter) armoireFilter.addEventListener('change', () => fetchDynamicContent(1));
		if (categorieFilter) categorieFilter.addEventListener('change', () => fetchDynamicContent(1));
		if (etatFilter) etatFilter.addEventListener('change', () => fetchDynamicContent(1));
	}
	
	// =================================================================
    // GESTIONNAIRE D'ÉVÉNEMENTS GLOBAL POUR TOUS LES CLICS
    // =================================================================
	document.body.addEventListener('click', function(e) {

        // --- Logique de la Section 1 (Pagination et Tri) ---
        if (dynamicContent) {
            const pageLink = e.target.closest('.page-link');
			if (pageLink) {
				e.preventDefault();
				const url = new URL(pageLink.href);
				const page = url.searchParams.get('page');
				if (page) fetchDynamicContent(page);
			}
			
			const sortLink = e.target.closest('.sortable a');
			if (sortLink) {
				e.preventDefault();
				const url = new URL(sortLink.href);
				const sortBy = url.searchParams.get('sort_by');
				const direction = url.searchParams.get('direction');
				fetchDynamicContent(1, sortBy, direction);
			}
        }

        // --- Logique de la Section 4 (Édition des cartes) ---
        const editBtn = e.target.closest('.edit-btn');
        if (editBtn) {
            const card = editBtn.closest('.item-card');
            card.querySelector('.card-info').style.display = 'none';
            card.querySelector('.card-actions').style.display = 'none';
            card.querySelector('.edit-mode').style.display = 'flex';
            card.querySelector('.edit-input').focus();
        }

        const saveBtn = e.target.closest('.save-btn');
        if (saveBtn) {
            const card = saveBtn.closest('.item-card');
            const input = card.querySelector('.edit-input');
            const isArmoiresPage = window.location.pathname.includes('gestion_armoires');
            const fetchURL = isArmoiresPage ? '/admin/modifier_armoire' : '/admin/modifier_categorie';

            fetch(fetchURL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ id: saveBtn.dataset.id, nom: input.value })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    card.querySelector('.card-title').textContent = data.nouveau_nom;
                    card.querySelector('.cancel-btn').click();
                } else {
                    showInfoModal('Erreur', data.error);
                }
            });
        }

        const cancelBtn = e.target.closest('.cancel-btn');
        if (cancelBtn) {
            const card = cancelBtn.closest('.item-card');
            card.querySelector('.edit-mode').style.display = 'none';
            card.querySelector('.card-info').style.display = '';
            card.querySelector('.card-actions').style.display = '';
            card.querySelector('.edit-input').value = card.querySelector('.card-title').textContent.trim();
        }

        // --- Logique de la Section 5 (Gestion des modales) ---
        const closeBtn = e.target.closest('.modal-overlay .close-btn, .modal-overlay .btn-cancel');
        const overlay = e.target.closest('.modal-overlay');
        if (closeBtn || (overlay && e.target === overlay)) {
            const modalToClose = e.target.closest('.modal-overlay');
            if (modalToClose) modalToClose.style.display = 'none';
            return;
        }

        const trigger = e.target.closest('[data-modal-trigger]');
		if (trigger) {
			const modalId = trigger.dataset.modalTrigger;
			const modal = document.getElementById(modalId);
			if (!modal) {
				console.error(`Modale non trouvée avec l'ID : ${modalId}`);
				return;
			}
			
			if (trigger.dataset.modalTitle) {
				const modalTitle = modal.querySelector('#' + modalId + '-title span');
				if (modalTitle) modalTitle.textContent = trigger.dataset.modalTitle;
			}
			if (trigger.dataset.modalMessage) {
				const modalMessage = modal.querySelector('#' + modalId + '-message');
				if (modalMessage) modalMessage.textContent = trigger.dataset.modalMessage;
			}
			modal.style.display = 'flex';

			const form = modal.querySelector('form');
			if (form) {
				if (trigger.dataset.actionUrl) {
					form.action = trigger.dataset.actionUrl;
				}
			}
			
			if (modalId === 'cloture-impossible-modal') {
				const anneeScolaire = trigger.dataset.anneeScolaire;
				const anneeFin = trigger.dataset.anneeFin;
				modal.querySelector('#cloture-impossible-annee').textContent = anneeScolaire;
				modal.querySelector('#cloture-impossible-date').textContent = `le 01/06/${anneeFin}`;
			}

			if (modalId === 'add-object-modal') {
				const modalTitle = modal.querySelector('#modal-objet-title');
				const modalSubmitBtn = modal.querySelector('#modal-submit-btn');
				const imagePreviewContainer = modal.querySelector('#image-preview-container');
				const iconTemplate = document.getElementById('modal-icon-template');

				if (trigger.dataset.objetId) {
					modalTitle.innerHTML = '';
					if (iconTemplate) modalTitle.appendChild(iconTemplate.cloneNode(true));
					modalTitle.appendChild(document.createTextNode(" Modifier l'objet"));
					modalSubmitBtn.textContent = "Mettre à jour";
					form.action = `/modifier_objet/${trigger.dataset.objetId}`;
					form.querySelector('#nom').value = trigger.dataset.nom || '';
					form.querySelector('#quantite').value = trigger.dataset.quantite || '';
					form.querySelector('#seuil').value = trigger.dataset.seuil || '';
					form.querySelector('#date_peremption').value = trigger.dataset.datePeremption || '';
					form.querySelector('#armoire_id').value = trigger.dataset.armoireId || '';
					form.querySelector('#categorie_id').value = trigger.dataset.categorieId || '';
					const imageUrl = trigger.dataset.imageUrl;
					form.querySelector('#image_url').value = imageUrl || '';

					if (imageUrl) {
						imagePreviewContainer.querySelector('img').src = imageUrl;
						imagePreviewContainer.style.display = 'block';
					} else {
						imagePreviewContainer.style.display = 'none';
					}
				} else {
					modalTitle.innerHTML = '';
					if (iconTemplate) modalTitle.appendChild(iconTemplate.cloneNode(true));
					modalTitle.appendChild(document.createTextNode(" Ajouter un nouvel objet"));
					modalSubmitBtn.textContent = "Enregistrer l'objet";
					form.action = document.body.dataset.addUrl;
					form.reset();
					imagePreviewContainer.style.display = 'none';
				}
				setupPexelsSearch();
			}

			if (trigger.dataset.formUsername) {
				modal.querySelectorAll('#username, #username-placeholder, #username-to-match').forEach(el => {
					el.textContent = trigger.dataset.formUsername;
				});
			}
			if (modalId === 'edit-email-modal' && trigger.dataset.formEmail) {
				form.querySelector('#email').value = trigger.dataset.formEmail;
			}
			if (modalId === 'edit-fournisseur-modal') {
				form.querySelector('#edit_nom').value = trigger.dataset.formNom || '';
				form.querySelector('#edit_site_web').value = trigger.dataset.formSite_web || '';
			}
			if (modalId === 'delete-user-modal') {
				const username = trigger.dataset.formUsername;
				form.dataset.username = username;
				modal.querySelector('#username-to-match').textContent = username;
				modal.querySelector('#username-placeholder').textContent = username;
				modal.querySelector('#delete-confirm-input').value = '';
				modal.querySelector('#delete-error-message').textContent = '';
			}
			if (modalId === 'budget-modal') {
				form.querySelector('#annee').value = trigger.dataset.formAnnee || new Date().getFullYear();
				form.querySelector('#montant_initial').value = trigger.dataset.formMontantInitial || '0.00';
			}
			if (modalId === 'edit-depense-modal') {
				const depenseId = trigger.dataset.depenseId;
				form.action = `/admin/budget/modifier_depense/${depenseId}`;
				form.querySelector('#edit_date_depense').value = trigger.dataset.formDateDepense;
				form.querySelector('#edit_fournisseur_id').value = trigger.dataset.formFournisseurId;
				form.querySelector('#edit_contenu').value = trigger.dataset.formContenu;
				form.querySelector('#edit_montant').value = trigger.dataset.formMontant;
				const estBonAchatCheckbox = form.querySelector('#edit_est_bon_achat');
				estBonAchatCheckbox.checked = trigger.dataset.formEstBonAchat == '1';
				estBonAchatCheckbox.dispatchEvent(new Event('change'));
			}
			if (modalId === 'echeance-modal') {
				const modalTitle = modal.querySelector('#echeance-modal-title');
				const submitBtn = modal.querySelector('#echeance-submit-btn');
				const traiteGroup = modal.querySelector('#traite-group');
				const echeanceId = trigger.dataset.echeanceId;
				if (echeanceId) {
					modalTitle.textContent = "Modifier une échéance";
					submitBtn.textContent = "Enregistrer les modifications";
					form.action = `/admin/echeances/modifier/${echeanceId}`;
					form.querySelector('#intitule').value = trigger.dataset.formIntitule;
					form.querySelector('#date_echeance').value = trigger.dataset.formDateEcheance;
					form.querySelector('#details').value = trigger.dataset.formDetails;
					traiteGroup.style.display = 'flex';
					form.querySelector('#traite').checked = trigger.dataset.formTraite == '1';
				} else {
					modalTitle.textContent = "Ajouter une échéance";
					submitBtn.textContent = "Enregistrer";
					form.action = document.body.dataset.urlAjoutEcheance;
					form.reset();
					traiteGroup.style.display = 'none';
				}
			}
			if (modalId === 'reset-licence-modal') {
				const passwordInput = modal.querySelector('#admin_password_confirm');
				if (passwordInput) passwordInput.value = '';
			}
		}

        // --- Logique de la Section 14 (Confirmation de suppression) ---
        const openModalButton = e.target.closest('.btn-open-danger-modal, .delete-btn, .btn-delete-objet');
		if (openModalButton) {
			e.preventDefault();
			const modal = document.getElementById('danger-modal');
			if (!modal) return;
			let message = "Êtes-vous sûr de vouloir effectuer cette action ?";
			let actionUrl = "#";
			if (openModalButton.matches('.btn-open-danger-modal')) {
				message = openModalButton.dataset.message;
				actionUrl = openModalButton.dataset.action;
			} else if (openModalButton.matches('.btn-delete-objet')) {
				const form = openModalButton.closest('form');
				message = `Êtes-vous sûr de vouloir supprimer l'objet <strong>'${openModalButton.dataset.objetNom}'</strong> ?<br>Cette action est irréversible.`;
				actionUrl = form.action;
			} else if (openModalButton.matches('.delete-btn')) {
				const form = openModalButton.closest('.delete-form-interactive');
				const itemName = form.dataset.itemName || 'cet élément';
				const itemType = form.dataset.itemType || 'élément';
				message = `Êtes-vous sûr de vouloir supprimer ${itemType === 'armoire' ? "l'armoire" : "la catégorie"} "${itemName}" ? Cette action est définitive.`;
				actionUrl = form.action;
			}
			const modalText = modal.querySelector('#danger-modal-text');
			const modalForm = modal.querySelector('#danger-modal-form');
			if (modalText) modalText.innerHTML = message;
			if (modalForm) modalForm.action = actionUrl;
			modal.style.display = 'flex';
		}
		
		// --- Logique de la Section 15 (Copie de l'ID) ---
        const instanceIdCode = e.target.closest('#instance-id-code');
		if (instanceIdCode) {
			navigator.clipboard.writeText(instanceIdCode.textContent)
			.then(() => {
				const originalText = instanceIdCode.textContent;
				instanceIdCode.textContent = 'Copié !';
				setTimeout(() => { instanceIdCode.textContent = originalText; }, 1500);
			})
			.catch(err => {
				console.error('Erreur de copie : ', err);
				showInfoModal("Erreur", "Impossible de copier l'identifiant.");
			});
		}

        // --- Logique de la Section 18 (Clôture de budget) ---
        const clotureBtn = e.target.closest('#cloture-budget-btn');
		if (clotureBtn) {
			const form = document.getElementById('cloture-budget-form');
			const modal = document.getElementById('cloture-budget-modal');
			const anneeSpan = document.getElementById('cloture-budget-annee');
			const confirmBtn = document.getElementById('confirm-cloture-btn');
			if (form && modal && anneeSpan && confirmBtn) {
				anneeSpan.textContent = form.dataset.annee;
				confirmBtn.onclick = () => { form.submit(); };
				modal.style.display = 'flex';
			}
		}
    });
	
	// =================================================================
	// GESTIONNAIRES D'ÉVÉNEMENTS NON-CLIC (input, change, submit)
	// =================================================================

    // --- Section 2 (Cases à cocher) ---
	document.body.addEventListener('change', function(e) {
		// On vérifie si l'élément cliqué est une de nos cases à cocher
		if (e.target.matches('.commande-checkbox, .traite-checkbox')) {
			const checkbox = e.target;
			const isCommande = checkbox.matches('.commande-checkbox');
			
			// On détermine la bonne URL et le bon corps de requête
			const url = isCommande 
				? `/inventaire/maj_commande/${checkbox.dataset.id}` 
				: `/inventaire/api/maj_traite/${checkbox.dataset.id}`;
				
			const body = isCommande 
				? { en_commande: checkbox.checked } 
				: { traite: checkbox.checked };

			// On lance l'appel à l'API
			fetch(url, {
				method: "POST",
				headers: { 
					"Content-Type": "application/json",
					"X-CSRFToken": csrfToken // Assure-toi que csrfToken est défini en haut de ton script
				},
				body: JSON.stringify(body)
			})
			.then(response => {
				// Première étape : on vérifie si la communication a réussi
				if (!response.ok) {
					throw new Error('La réponse du serveur n\'est pas valide.');
				}
				// Si c'est bon, on lit la réponse JSON
				return response.json();
			})
			.then(data => {
				// Deuxième étape : on analyse la réponse JSON
				if (data.success) {
					// Si le serveur confirme le succès, on met à jour l'interface
					checkbox.closest('tr').classList.toggle('acquitte', checkbox.checked);
				} else {
					// Si le serveur signale une erreur, on affiche un message et on annule le changement
					showInfoModal("Erreur", data.error || "Une erreur est survenue.");
					checkbox.checked = !checkbox.checked;
				}
			})
			.catch(error => {
				// Cette partie s'exécute si la communication a échoué (pas de réseau, erreur 500, etc.)
				console.error('Erreur Fetch:', error);
				showInfoModal("Erreur de Communication", "Impossible de contacter le serveur.");
				checkbox.checked = !checkbox.checked; // On annule le changement
			});
		}
	});

    // --- Section 3 (Recherche globale) ---
    const globalSearchInput = document.getElementById("recherche-objet");
    const resultsContainer = document.getElementById("search-results-container");
    if (globalSearchInput) {
        let searchTimeoutHeader;
        globalSearchInput.addEventListener("input", function () {
            const query = this.value.trim();
            clearTimeout(searchTimeoutHeader);
            if(resultsContainer) {
                resultsContainer.innerHTML = '';
                resultsContainer.style.display = 'none';
            }
            if (query.length < 2) return;
            searchTimeoutHeader = setTimeout(() => {
                fetch(`/api/rechercher?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    if(resultsContainer) {
                        resultsContainer.innerHTML = '';
                        if (data.length > 0) {
                            const list = document.createElement('ul');
                            list.className = 'search-results-list';
                            data.forEach(item => {
                                const li = document.createElement('li');
                                const a = document.createElement('a');
                                a.href = `/objet/${item.id}`;
                                const nameSpan = document.createElement('span');
                                nameSpan.textContent = item.nom;
                                const contextSmall = document.createElement('small');
                                contextSmall.className = 'search-result-context';
                                contextSmall.textContent = `Armoire: ${item.armoire_nom} / Catégorie: ${item.categorie_nom}`;
                                a.appendChild(nameSpan);
                                a.appendChild(contextSmall);
                                li.appendChild(a);
                                list.appendChild(li);
                            });
                            resultsContainer.appendChild(list);
                            resultsContainer.style.display = 'block';
                        } else {
                            resultsContainer.innerHTML = '<div style="padding: 10px; color: #6c7a89;">Aucun résultat trouvé.</div>';
                            resultsContainer.style.display = 'block';
                        }
                    }
                })
                .catch(error => {
                    console.error("Erreur de recherche:", error);
                    if(resultsContainer) {
                        resultsContainer.innerHTML = '<div style="padding: 10px; color: #dc3545;">Erreur de recherche.</div>';
                        resultsContainer.style.display = 'block';
                    }
                });
            }, 300);
        });
    }
	
    // --- Section 6 (Disparition des messages flash) ---
    document.querySelectorAll('.flash').forEach(function (flashMessage) {
        setTimeout(() => {
            flashMessage.style.opacity = '0';
            setTimeout(() => { flashMessage.remove(); }, 500);
        }, 5000);
    });

    // --- Section 7 (Déplacement en masse) ---
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
	if (selectAllCheckbox) {
		const objetCheckboxes = document.querySelectorAll('.objet-checkbox');
		const bulkActionSection = document.getElementById('bulk-action-section');
		const bulkMoveBtn = document.getElementById('bulk-move-btn');
		const moveDestination = document.getElementById('move-destination');
		function toggleBulkActionSection() {
			const anyChecked = document.querySelector('.objet-checkbox:checked');
			if(bulkActionSection) bulkActionSection.style.display = anyChecked ? 'flex' : 'none';
		}
		selectAllCheckbox.addEventListener('change', function () {
			objetCheckboxes.forEach(checkbox => { checkbox.checked = this.checked; });
			toggleBulkActionSection();
		});
		objetCheckboxes.forEach(checkbox => {
			checkbox.addEventListener('change', function () {
				if (!this.checked) selectAllCheckbox.checked = false;
				toggleBulkActionSection();
			});
		});
		if(bulkMoveBtn) {
            bulkMoveBtn.addEventListener('click', function () {
                const selectedObjectIds = Array.from(objetCheckboxes).filter(cb => cb.checked).map(cb => cb.dataset.id);
                if (selectedObjectIds.length === 0) {
                    showInfoModal("Aucune Sélection", "Veuillez sélectionner au moins un objet à déplacer.");
                    return;
                }
                const destinationId = moveDestination.value;
                const pathname = window.location.pathname;
                const typeDestination = pathname.includes('/armoire/') ? 'armoire' : (pathname.includes('/categorie/') ? 'categorie' : '');
                if (!typeDestination) {
                    showInfoModal("Action Impossible", "Action de déplacement non disponible sur cette page.");
                    return;
                }
                fetch('/api/deplacer_objets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                    body: JSON.stringify({
                        objet_ids: selectedObjectIds,
                        destination_id: destinationId,
                        type_destination: typeDestination
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.reload();
                    } else {
                        showInfoModal("Erreur", "Erreur lors du déplacement des objets : " + (data.error || 'Erreur inconnue'));
                    }
                })
                .catch(error => {
                    console.error("Erreur lors du déplacement en masse :", error);
                    showInfoModal("Erreur de Communication", "Une erreur est survenue lors de la communication avec le serveur.");
                });
            });
        }
	}
	
	// =================================================================
	// SECTION : ANIMATION DE LA CLOCHE D'ALERTE
	// =================================================================
	const alertIcon = document.getElementById('alert-icon-link');
	if (alertIcon) {
		// On lit le nombre d'alertes depuis l'attribut data-*
		const alertCount = parseInt(alertIcon.dataset.alertCount, 10);

		// On ajoute les classes en fonction du nombre
		if (alertCount > 5) { // Seuil pour l'alerte "haute" (rouge + animation)
			alertIcon.classList.add('has-alerts-high');
		} else if (alertCount > 0) { // Seuil pour l'alerte "moyenne" (orange)
			alertIcon.classList.add('has-alerts-medium');
		}
	}

    // --- Section 9 (Filtre de kit) ---
    const kitObjetSearch = document.getElementById('kit-objet-search');
    if (kitObjetSearch) {
        const availableObjectsTable = document.getElementById('available-objects-table');
        const rows = availableObjectsTable.querySelectorAll('tbody tr');
        kitObjetSearch.addEventListener('input', function () {
            const searchTerm = this.value.toLowerCase();
            rows.forEach(row => {
                const nomObjet = row.querySelector('td:first-child').textContent.toLowerCase();
                row.style.display = nomObjet.includes(searchTerm) ? '' : 'none';
            });
        });
    }

    // --- Section 10 (Rapports) ---
    const formRapportsGrid = document.querySelector('.form-rapports-grid');
    if (formRapportsGrid) {
        const dateDebutInput = formRapportsGrid.querySelector('#date_debut');
        const dateFinInput = formRapportsGrid.querySelector('#date_fin');
        const today = new Date().toISOString().split('T')[0];
        if (!dateFinInput.value) dateFinInput.value = today;
        dateDebutInput.addEventListener('change', () => {
            if (dateDebutInput.value) {
                dateFinInput.min = dateDebutInput.value;
                if (dateFinInput.value < dateDebutInput.value) dateFinInput.value = dateDebutInput.value;
            }
        });
    }

    // --- Section 12 (Export budget) ---
    const dateDebutExport = document.getElementById('date_debut_export');
    if (dateDebutExport) {
        const dateFinExport = document.getElementById('date_fin_export');
        const pdfLink = document.getElementById('export-pdf-link');
        const excelLink = document.getElementById('export-excel-link');
        function updateExportLinks() {
            const dateDebut = dateDebutExport.value;
            const dateFin = dateFinExport.value;
            const exportUrl = '/admin/exporter_budget';
            const paramsPdf = new URLSearchParams({ format: 'pdf', date_debut: dateDebut, date_fin: dateFin });
            pdfLink.href = `${exportUrl}?${paramsPdf.toString()}`;
            const paramsExcel = new URLSearchParams({ format: 'excel', date_debut: dateDebut, date_fin: dateFin });
            excelLink.href = `${exportUrl}?${paramsExcel.toString()}`;
        }
        dateDebutExport.addEventListener('change', updateExportLinks);
        dateFinExport.addEventListener('change', updateExportLinks);
        updateExportLinks();
    }

    // --- Section 13 (Modale dépense) ---
    const depenseModal = document.getElementById('depense-modal');
    if (depenseModal) {
        const bonAchatCheckbox = depenseModal.querySelector('#est_bon_achat');
        const fournisseurSelect = depenseModal.querySelector('#fournisseur_id');
        bonAchatCheckbox.addEventListener('change', function () {
            fournisseurSelect.disabled = this.checked;
            if (this.checked) fournisseurSelect.value = '';
        });
    }
    const editDepenseModal = document.getElementById('edit-depense-modal');
    if (editDepenseModal) {
        const bonAchatCheckbox = editDepenseModal.querySelector('#edit_est_bon_achat');
        const fournisseurSelect = editDepenseModal.querySelector('#edit_fournisseur_id');
        bonAchatCheckbox.addEventListener('change', function () {
            fournisseurSelect.disabled = this.checked;
            if (this.checked) fournisseurSelect.value = '';
        });
    }

    // --- Section 16 (Page Admin) ---
	const importDbInput = document.getElementById('fichier-db');
	if (importDbInput) {
		importDbInput.addEventListener('change', function () {
			if (this.files.length > 0) this.form.submit();
		});
	}
	const resetLicenceForm = document.getElementById('reset-licence-form');
	if (resetLicenceForm) {
		resetLicenceForm.addEventListener('submit', function (event) {
			const confirmation = confirm('Êtes-vous sûr de vouloir réinitialiser la licence ? L\'application repassera en mode GRATUIT limité à 50 objets.');
			if (!confirmation) event.preventDefault();
		});
	}
	const deleteUserModal = document.getElementById('delete-user-modal');
	if (deleteUserModal) {
		const deleteForm = deleteUserModal.querySelector('form');
		const confirmInput = deleteUserModal.querySelector('#delete-confirm-input');
		const errorMessage = deleteUserModal.querySelector('#delete-error-message');
		deleteForm.addEventListener('submit', function(event) {
			if (confirmInput.value.trim() !== this.dataset.username) {
				event.preventDefault(); 
				errorMessage.textContent = 'Le nom de l\'utilisateur ne correspond pas.';
				confirmInput.focus();
			} else {
				errorMessage.textContent = '';
			}
		});
	}

    // --- Section 17 (Upload logo) ---
    const editLogoInput = document.getElementById('edit_logo');
    if (editLogoInput) {
        const editLogoFilename = document.getElementById('edit-logo-filename');
        const defaultText = editLogoFilename.textContent;
        editLogoInput.addEventListener('change', function() {
            editLogoFilename.textContent = this.files.length > 0 ? this.files[0].name : defaultText;
        });
    }

	// =================================================================
	// LOGIQUE POUR LA RECHERCHE D'IMAGES PEXELS
	// =================================================================
    function setupPexelsSearch() {
        const pexelsSearchButton = document.getElementById('btn-search-pexels');
        const pexelsResultsContainer = document.getElementById('pexels-results');
        const imageUrlInput = document.getElementById('image_url');
        const imageNameInput = document.getElementById('nom');
        const imagePreview = document.getElementById('image-preview');
        const imagePreviewContainer = document.getElementById('image-preview-container');

        if (!pexelsSearchButton || pexelsSearchButton.dataset.listenerAttached) return;
        
        pexelsSearchButton.dataset.listenerAttached = 'true';

        pexelsSearchButton.addEventListener('click', async () => {
            const query = imageNameInput.value.trim();
            if (!query) {
                alert("Veuillez d'abord entrer un nom pour l'objet à rechercher.");
                return;
            }
            pexelsResultsContainer.innerHTML = '<p>Recherche en cours...</p>';
            pexelsResultsContainer.style.display = 'block';
            try {
                const response = await fetch(`/api/search-images?q=${encodeURIComponent(query)}`);
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'La recherche a échoué.');
                }
                const images = await response.json();
                pexelsResultsContainer.innerHTML = '';
                if (images.length === 0) {
                    pexelsResultsContainer.innerHTML = '<p>Aucune image trouvée.</p>';
                } else {
                    images.forEach(image => {
                        const imgElement = document.createElement('img');
                        imgElement.src = image.small_url;
                        imgElement.classList.add('pexels-image');
                        imgElement.alt = `Photo par ${image.photographer}`;
                        imgElement.title = `Photo par ${image.photographer}`;
                        imgElement.addEventListener('click', () => {
                            imageUrlInput.value = image.large_url;
                            imagePreview.src = image.large_url;
                            imagePreviewContainer.style.display = 'block';
                            pexelsResultsContainer.style.display = 'none';
                        });
                        pexelsResultsContainer.appendChild(imgElement);
                    });
                }
            } catch (error) {
                pexelsResultsContainer.innerHTML = `<p style="color: red;">Erreur : ${error.message}</p>`;
            }
        });

        imageUrlInput.addEventListener('input', () => {
            const url = imageUrlInput.value.trim();
            if (url) {
                imagePreview.src = url;
                imagePreviewContainer.style.display = 'block';
            } else {
                imagePreviewContainer.style.display = 'none';
            }
        });
    }

    // On appelle la fonction une première fois au cas où.
    setupPexelsSearch();

});