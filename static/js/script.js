// =================================================================
// FONCTION GLOBALE POUR AFFICHER LA MODALE D'INFORMATION
// =================================================================
function updateCartIcon() {
    const badge = document.getElementById('cart-count-badge');
    if (!badge) return;
    
    const cart = JSON.parse(sessionStorage.getItem('reservationCart')) || {};
    const cartCount = Object.keys(cart).length;
    
    if (cartCount > 0) {
        // Formatage du nombre (99+ si > 99)
        badge.textContent = cartCount > 99 ? '99+' : cartCount;
        
        // Ajout de classes CSS selon la quantité
        badge.classList.toggle('large', cartCount > 99);
        
        badge.style.display = 'flex';
    } else {
        badge.style.display = 'none';
    }
}

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
	updateCartIcon();
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
			const params = new URLSearchParams({
				page: page,
				sort_by: currentSortBy,
				direction: currentDirection
			});

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
    // SECTION 2 : GESTIONNAIRE D'ÉVÉNEMENTS GLOBAL POUR TOUS LES CLICS
    // =================================================================
	document.body.addEventListener('click', function(e) {
		
        // --- Logique pour le contenu dynamique (Pagination & Tri) ---
        const dynamicContentContainer = e.target.closest('#dynamic-content');
        if (dynamicContentContainer) {
            const pageLink = e.target.closest('.page-link');
			if (pageLink) {
				e.preventDefault();
				const url = new URL(pageLink.href);
				const page = url.searchParams.get('page');
				if (page) fetchDynamicContent(page);
                return; // On arrête le traitement ici
			}
			
			const sortLink = e.target.closest('.sortable a');
			if (sortLink) {
				e.preventDefault();
				const url = new URL(sortLink.href);
				const sortBy = url.searchParams.get('sort_by');
				const direction = url.searchParams.get('direction');
				if (sortBy && direction) fetchDynamicContent(1, sortBy, direction);
                return; // On arrête le traitement ici
			}
        }

        // --- DÉBUT DE LA CORRECTION POUR LA MODALE DE DANGER ---
        const openModalButton = e.target.closest('.btn-open-danger-modal, .delete-btn, .btn-delete-objet');
		if (openModalButton) {
			e.preventDefault();

            const dangerModalElement = document.getElementById('dangerModal');
            if (!dangerModalElement) {
                console.error("L'élément de la modale de danger (#dangerModal) est introuvable.");
                return;
            }
            
            // On utilise la méthode Bootstrap pour éviter les conflits
            const dangerModal = bootstrap.Modal.getOrCreateInstance(dangerModalElement);

			const modalText = dangerModalElement.querySelector('#dangerModalText');
			const modalForm = dangerModalElement.querySelector('#dangerModalForm');

            let message = "Êtes-vous sûr de vouloir effectuer cette action ?";
			let actionUrl = "#";

			if (openModalButton.matches('.btn-delete-objet')) {
				const form = openModalButton.closest('form');
				message = `Êtes-vous sûr de vouloir supprimer l'objet <strong>'${openModalButton.dataset.objetNom}'</strong> ?<br>Cette action est irréversible.`;
				actionUrl = form ? form.action : '#';
			} else if (openModalButton.matches('.delete-btn')) {
				const form = openModalButton.closest('.delete-form-interactive');
				const itemName = form.dataset.itemName || 'cet élément';
				message = `Êtes-vous sûr de vouloir supprimer l'élément "${itemName}" ? Cette action est définitive.`;
				actionUrl = form ? form.action : '#';
			}
			
			if (modalText) modalText.innerHTML = message;
			if (modalForm) modalForm.action = actionUrl;
			
            dangerModal.show();
            return; // On arrête le traitement ici
		}

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

		const closeBtn = e.target.closest('.modal-overlay .close-btn, .modal-overlay .btn-cancel');
		const overlay = e.target.closest('.modal-overlay');
		if (closeBtn || (overlay && e.target === overlay)) {
			const modalToClose = e.target.closest('.modal-overlay');
			if (modalToClose) modalToClose.style.display = 'none';
			return;
		}

		const trigger = e.target.closest('[data-modal-trigger]');
		if (trigger) {
			console.log("Élément déclencheur trouvé (trigger) :", trigger);
			const modalId = trigger.dataset.modalTrigger;
			console.log("Tentative d'ouverture de la modale avec l'ID :", modalId);

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
				const form = modal.querySelector('#edit-fournisseur-form');
				const id = trigger.dataset.id;
				
				form.action = `/admin/fournisseurs/modifier/${id}`;
				form.querySelector('#edit_nom').value = trigger.dataset.nom;
				form.querySelector('#edit_site_web').value = trigger.dataset.siteWeb;
				form.querySelector('#edit_logo_url').value = trigger.dataset.logoUrl;
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
			if (modalId === 'depense-modal') {
				const form = modal.querySelector('form');
				if (form) {
					form.reset();
				}

				const dateInput = modal.querySelector('#date_depense');
				if (dateInput) {
					dateInput.value = new Date().toISOString().split('T')[0];
				}

				const fournisseurSelect = modal.querySelector('#fournisseur_id');
				if (fournisseurSelect) {
					fournisseurSelect.disabled = false;
				}
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
	// SECTION 3 : GESTIONNAIRES D'ÉVÉNEMENTS NON-CLIC (input, change, submit)
	// =================================================================
	document.body.addEventListener('change', function(e) {
		if (e.target.matches('.commande-checkbox, .traite-checkbox')) {
			const checkbox = e.target;
			const isCommande = checkbox.matches('.commande-checkbox');
			const url = isCommande 
				? `/maj_commande/${checkbox.dataset.id}` 
				: `/maj_traite/${checkbox.dataset.id}`;
				
			const body = isCommande 
				? { en_commande: checkbox.checked } 
				: { traite: checkbox.checked };

			fetch(url, {
				method: "POST",
				headers: { 
					"Content-Type": "application/json",
					"X-CSRFToken": csrfToken
				},
				body: JSON.stringify(body)
			})
			.then(response => {
				if (!response.ok) {
					throw new Error('La réponse du serveur n\'est pas valide.');
				}
				return response.json();
			})
			.then(data => {
				if (data.success) {
					checkbox.closest('tr').classList.toggle('acquitte', checkbox.checked);
				} else {
					showInfoModal("Erreur", data.error || "Une erreur est survenue.");
					checkbox.checked = !checkbox.checked;
				}
			})
			.catch(error => {
				console.error('Erreur Fetch:', error);
				showInfoModal("Erreur de Communication", "Impossible de contacter le serveur.");
				checkbox.checked = !checkbox.checked;
			});
		}
	});

	// =======================================================================
	// SECTION 4 : RECHERCHE GLOBALE
	// =======================================================================
    const globalSearchInput = document.getElementById("recherche-objet");
    const resultsContainer = document.getElementById("search-results-container");

    if (globalSearchInput && resultsContainer) {
        let searchTimeoutHeader;
        globalSearchInput.addEventListener("input", function () {
            const query = this.value.trim();
            clearTimeout(searchTimeoutHeader);
            
            resultsContainer.innerHTML = '';
            resultsContainer.style.display = 'none';
            
            if (query.length < 2) return;

            searchTimeoutHeader = setTimeout(() => {
                fetch(`/api/rechercher?q=${encodeURIComponent(query)}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Erreur réseau.');
                    }
                    return response.json();
                })
                .then(data => {
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
                    } else {
                        // LE MESSAGE QUE VOUS VOULEZ
                        resultsContainer.innerHTML = '<div class="search-no-results">Cet objet n\'existe pas dans la base.</div>';
                    }
                    resultsContainer.style.display = 'block';
                })
                .catch(error => {
                    console.error("Erreur de recherche:", error);
                    resultsContainer.innerHTML = '<div class="search-error">Erreur de recherche.</div>';
                    resultsContainer.style.display = 'block';
                });
            }, 300);
        });

        document.addEventListener('click', (e) => {
            if (!resultsContainer.contains(e.target) && e.target !== globalSearchInput) {
                resultsContainer.style.display = 'none';
            }
        });
    }

    // =====================================================================
	// SECTION 5 : GESTION DEPLACEMENT EN MASSE
	// =====================================================================
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
	// SECTION 6 : ANIMATION DE LA CLOCHE D'ALERTE
	// =================================================================
	const alertIcon = document.getElementById('alert-icon-link');
	if (alertIcon) {
		const alertCount = parseInt(alertIcon.dataset.alertCount, 10);

		if (alertCount > 3) {
			alertIcon.classList.add('has-alerts-high');
		} else if (alertCount > 0) {
			alertIcon.classList.add('has-alerts-medium');
		}
	}

    // ==================================================================
	// SECTION 7 : FILTRE DE kit
	// ==================================================================
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

    // ===================================================================
	// SECTION 8 : Rapports
	// ===================================================================
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

    // ===================================================================
	// SECTION 9 : EXPORT DU BUDGET
	// ===================================================================
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

    // ====================================================================
	// SECTION 10 : MODALE DES DEPENSES
	// ====================================================================
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

    // =======================================================================
	// SECTION 11 : FONCTIONS ADMIN DB LICENCE GEST UTILISATEUR
	// =======================================================================
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

    // =======================================================================
	// SECTION 12 : UPLOAD LOGO
	// =======================================================================
    const editLogoInput = document.getElementById('edit_logo');
    if (editLogoInput) {
        const editLogoFilename = document.getElementById('edit-logo-filename');
        const defaultText = editLogoFilename.textContent;
        editLogoInput.addEventListener('change', function() {
            editLogoFilename.textContent = this.files.length > 0 ? this.files[0].name : defaultText;
        });
    }

	// =================================================================
	// SECTION 13 : LOGIQUE POUR LA RECHERCHE D'IMAGES PEXELS
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
	
	// =================================================================
	// NOUVELLE SECTION : GESTION DE LA MODALE D'AJOUT/MODIFICATION D'OBJET
	// =================================================================
	const addObjectModalElement = document.getElementById('addObjectModal');
	if (addObjectModalElement) {
		addObjectModalElement.addEventListener('show.bs.modal', function (event) {
			const button = event.relatedTarget; // Le bouton qui a ouvert la modale
			
			// Sécurité : vérifier que le bouton existe bien
			if (!button) {
				console.error("Aucun bouton déclencheur trouvé pour la modale");
				return;
			}
			
			const form = addObjectModalElement.querySelector('form');
			const modalTitle = addObjectModalElement.querySelector('.modal-title');
			const submitBtn = form.querySelector('button[type="submit"]');
			const imagePreviewContainer = addObjectModalElement.querySelector('#image-preview-container');
			const imagePreview = imagePreviewContainer?.querySelector('img');
			
			// On vérifie si on est en mode "Modification"
			const objetId = button.dataset.objetId;
			
			if (objetId) {
				// --- MODE MODIFICATION ---
				console.log("Mode MODIFICATION - Objet ID:", objetId);
				
				modalTitle.textContent = "Modifier l'objet";
				form.action = `/modifier_objet/${objetId}`;
				
				// Pré-remplissage des champs avec validation
				const fields = {
					'nom': button.dataset.nom,
					'quantite': button.dataset.quantite,
					'seuil': button.dataset.seuil,
					'date_peremption': button.dataset.datePeremption,
					'armoire_id': button.dataset.armoireId,
					'categorie_id': button.dataset.categorieId,
					'image_url': button.dataset.imageUrl,
					'fds_url': button.dataset.fdsUrl
				};
				
				// Remplissage sécurisé de tous les champs
				for (const [fieldId, value] of Object.entries(fields)) {
					const input = form.querySelector(`#${fieldId}`);
					if (input) {
						input.value = value || '';
					} else {
						console.warn(`Champ #${fieldId} introuvable dans le formulaire`);
					}
				}
				
				// Gestion de l'aperçu d'image
				const imageUrl = button.dataset.imageUrl;
				if (imageUrl && imagePreview && imagePreviewContainer) {
					imagePreview.src = imageUrl;
					imagePreviewContainer.style.display = 'block';
				} else if (imagePreviewContainer) {
					imagePreviewContainer.style.display = 'none';
				}
				
				// Bouton de soumission
				if (submitBtn) {
					submitBtn.textContent = 'Mettre à jour';
					submitBtn.className = 'btn btn-primary'; // Optionnel : changer le style
				}
				
			} else {
				// --- MODE AJOUT ---
				console.log("Mode AJOUT - Nouveau objet");
				
				modalTitle.textContent = "Ajouter un nouvel objet";
				
				// URL d'ajout depuis data-attribute ou URL par défaut
				form.action = document.body.dataset.addUrl || '/ajouter_objet';
				
				// Réinitialisation complète du formulaire
				form.reset();
				
				// Masquer l'aperçu d'image
				if (imagePreviewContainer) {
					imagePreviewContainer.style.display = 'none';
				}
				
				// Bouton de soumission
				if (submitBtn) {
					submitBtn.textContent = 'Enregistrer l\'objet';
					submitBtn.className = 'btn btn-success'; // Optionnel : changer le style
				}
			}
			
			// Initialisation de la recherche Pexels
			if (typeof setupPexelsSearch === 'function') {
				setupPexelsSearch();
			} else {
				console.warn("setupPexelsSearch n'est pas définie");
			}
		});
	}

    setupPexelsSearch();
});