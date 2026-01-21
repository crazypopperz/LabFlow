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
// SYSTÈME DE NOTIFICATIONS (TOASTS)
// =================================================================
function showToast(message, type = 'success') {
    const container = document.querySelector('.toast-container');
    if (!container) return;

    let icon = 'bi-check-circle-fill';
    let toastClass = 'text-bg-success'; // Vert par défaut

    if (type === 'error' || type === 'danger') {
        icon = 'bi-exclamation-triangle-fill';
        toastClass = 'text-bg-danger'; // Rouge
    } else if (type === 'info') {
        icon = 'bi-info-circle-fill';
        toastClass = 'text-bg-primary'; // Bleu
    } else if (type === 'warning') {
        icon = 'bi-exclamation-circle-fill';
        toastClass = 'text-bg-warning'; // Jaune/Orange
    }

    const html = `
        <div class="toast ${toastClass} align-items-center border-0 fade show" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center gap-3" style="padding: 12px 16px;">
                    <i class="bi ${icon} fs-4"></i>
                    <div style="font-size: 1rem;">
                        ${message}
                    </div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', html);
    
    const toastElement = container.lastElementChild;
    
    // Auto-destruction
    setTimeout(() => {
        if (toastElement && document.body.contains(toastElement)) {
            toastElement.classList.remove('show');
            setTimeout(() => toastElement.remove(), 500);
        }
    }, 4500);
    
    // Clic croix
    const closeBtn = toastElement.querySelector('.btn-close');
    if(closeBtn) closeBtn.addEventListener('click', () => toastElement.remove());
}

// =================================================================
// POINT D'ENTRÉE UNIQUE
// =================================================================
document.addEventListener("DOMContentLoaded", function () {
    // --- SUPPRESSION ICI : updateCartIcon() a été retiré ---
    
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

			const apiUrl = `/api/inventaire?${params.toString()}`;

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

        // --- MODALE DE DANGER ---
        const openModalButton = e.target.closest('.btn-open-danger-modal, .delete-btn, .btn-delete-objet');
		if (openModalButton) {
			e.preventDefault();

            const dangerModalElement = document.getElementById('dangerModal');
            if (!dangerModalElement) return;
            
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
            return;
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
			const modalId = trigger.dataset.modalTrigger;
			const modal = document.getElementById(modalId);
			if (!modal) return;
			
			if (trigger.dataset.modalTitle) {
				const modalTitle = modal.querySelector('#' + modalId + '-title span');
				if (modalTitle) modalTitle.textContent = trigger.dataset.modalTitle;
			}
			if (trigger.dataset.modalMessage) {
				const modalMessage = modal.querySelector('#' + modalId + '-message');
				if (modalMessage) modalMessage.textContent = trigger.dataset.modalMessage;
			}
			modal.style.display = 'flex';
			
			if (modalId === 'cloture-impossible-modal') {
				const anneeScolaire = trigger.dataset.anneeScolaire;
				const anneeFin = trigger.dataset.anneeFin;
				modal.querySelector('#cloture-impossible-annee').textContent = anneeScolaire;
				modal.querySelector('#cloture-impossible-date').textContent = `le 01/06/${anneeFin}`;
			}

			if (modalId === 'add-object-modal') {
				const addObjectModalElement = document.getElementById('addObjectModal'); // Correction ID
				if (!addObjectModalElement) return;
				
				const addObjectModalInstance = bootstrap.Modal.getOrCreateInstance(addObjectModalElement);
				const form = addObjectModalElement.querySelector('form');
				const modalTitle = addObjectModalElement.querySelector('.modal-title');
				const submitBtn = form.querySelector('button[type="submit"]');
				const imagePreviewContainer = addObjectModalElement.querySelector('#image-preview-container');
				const imagePreview = imagePreviewContainer?.querySelector('img');
				
				const objetId = trigger.dataset.objetId;
				
				if (objetId) {
					// --- MODE MODIFICATION ---
					modalTitle.textContent = "Modifier l'objet";
					form.action = `/modifier_objet/${objetId}`;
					
					// 1. Récupération des données brutes
                    const rawImg = trigger.dataset.imageUrl || '';
                    const rawFds = trigger.dataset.fdsUrl || '';

                    // 2. Pré-remplissage des champs standards
                    const fields = {
                        'nom': trigger.dataset.nom,
                        'quantite': trigger.dataset.quantite,
                        'seuil': trigger.dataset.seuil,
                        'date_peremption': trigger.dataset.datePeremption,
                        'armoire_id': trigger.dataset.armoireId,
                        'categorie_id': trigger.dataset.categorieId
                    };
                    
                    for (const [fieldId, rawValue] of Object.entries(fields)) {
                        const input = form.querySelector(`#${fieldId}`);
                        if (input) {
                            let value = rawValue;
                            if (value === 'None' || value === null || value === undefined) value = '';
                            input.value = value;
                        }
                    }

                    // 3. GESTION INTELLIGENTE DES ONGLETS (IMAGE)
                    const tabImgFile = new bootstrap.Tab(document.querySelector('#pills-file-tab'));
                    const tabImgUrl = new bootstrap.Tab(document.querySelector('#pills-url-tab'));
                    const inputImgUrl = form.querySelector('#image_url');
                    const inputImgFile = form.querySelector('#image');

                    if (rawImg.startsWith('http')) {
                        tabImgUrl.show();
                        if (inputImgUrl) inputImgUrl.value = rawImg;
                        if (inputImgFile) inputImgFile.value = '';
                    } else {
                        tabImgFile.show();
                        if (inputImgUrl) inputImgUrl.value = '';
                    }

                    // 4. GESTION INTELLIGENTE DES ONGLETS (FDS)
                    const btnTabFdsFile = document.querySelector('button[data-bs-target="#nav-file-fds"]');
                    const btnTabFdsUrl = document.querySelector('button[data-bs-target="#nav-url-fds"]');
                    const inputFdsUrl = form.querySelector('#fds_url');
                    const inputFdsFile = form.querySelector('input[name="fds_file"]');

                    if (rawFds.startsWith('http')) {
                        if (btnTabFdsUrl) new bootstrap.Tab(btnTabFdsUrl).show();
                        if (inputFdsUrl) inputFdsUrl.value = rawFds;
                        if (inputFdsFile) inputFdsFile.value = '';
                    } else {
                        if (btnTabFdsFile) new bootstrap.Tab(btnTabFdsFile).show();
                        if (inputFdsUrl) inputFdsUrl.value = '';
                    }
					
					// 5. Aperçu Image
					if (rawImg && imagePreview && imagePreviewContainer) {
						if (rawImg.startsWith('http')) {
							imagePreview.src = rawImg;
						} else {
							imagePreview.src = `/static/${rawImg}`;
						}
						imagePreviewContainer.style.display = 'block';
					} else if (imagePreviewContainer) {
						imagePreviewContainer.style.display = 'none';
					}
					
					if (submitBtn) {
						submitBtn.textContent = 'Mettre à jour';
						submitBtn.className = 'btn btn-primary';
					}
					
				} else {
					// --- MODE AJOUT ---
					modalTitle.textContent = "Ajouter un nouvel objet";
					form.action = document.body.dataset.addUrl || '/ajouter_objet';
					form.reset();
					if (imagePreviewContainer) imagePreviewContainer.style.display = 'none';
					if (submitBtn) {
						submitBtn.textContent = 'Enregistrer l\'objet';
						submitBtn.className = 'btn btn-success';
					}
				}
				
				addObjectModalInstance.show();
				setupPexelsSearch();
				return;
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
				
                // Gestion Logo URL
                const logo = trigger.dataset.logo;
                const urlInput = document.getElementById('edit_logo_url_input');
                if (logo && logo.startsWith('http')) {
                    urlInput.value = logo;
                } else {
                    urlInput.value = '';
                }
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
				if (form) form.reset();
				const dateInput = modal.querySelector('#date_depense');
				if (dateInput) dateInput.value = new Date().toISOString().split('T')[0];
				const fournisseurSelect = modal.querySelector('#fournisseur_id');
				if (fournisseurSelect) fournisseurSelect.disabled = false;
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
    // SECTION 4 : RECHERCHE GLOBALE (HEADER) - VERSION FINALE AVEC FLAG
    // =======================================================================
    const globalSearchInput = document.getElementById('globalSearchInput');
    const resultsContainer = document.getElementById('globalSearchResults');
    const searchWrapper = document.getElementById('search-wrapper-dropdown');
    const clearBtn = document.getElementById('clear-btn-dropdown');

    if (globalSearchInput && resultsContainer && searchWrapper) {
        let searchTimeoutHeader;
        let searchController = null;
        let hasValidResults = false; // ✅ Nouveau flag d'état

        // ---------------------------------------------------------
        // 1. GESTION VISUELLE (FOCUS)
        // ---------------------------------------------------------
        globalSearchInput.addEventListener('focus', () => {
            searchWrapper.classList.add('focused');
            globalSearchInput.classList.add('expanded');
            
            // On ne réaffiche que si on a des résultats valides en mémoire
            // et que l'input n'a pas changé entre temps
            if (globalSearchInput.value.trim().length >= 2 && hasValidResults) {
                resultsContainer.style.display = 'block';
                resultsContainer.classList.add('visible');
            }
        });

        // ---------------------------------------------------------
        // 2. GESTION DE LA FRAPPE (INPUT)
        // ---------------------------------------------------------
        globalSearchInput.addEventListener('input', function(e) {
            const query = e.target.value.trim();
            
            if (searchTimeoutHeader) clearTimeout(searchTimeoutHeader);

            // Gestion bouton croix
            if (clearBtn) {
                if (query.length > 0) clearBtn.classList.add('visible');
                else clearBtn.classList.remove('visible');
            }

            // Nettoyage si trop court
            if (query.length < 2) {
                resultsContainer.classList.remove('visible');
                resultsContainer.style.display = 'none';
                hasValidResults = false; // ✅ Reset du flag
                return;
            }

            searchTimeoutHeader = setTimeout(() => {
                if (searchController) searchController.abort();
                searchController = new AbortController();
                const signal = searchController.signal;

                // UI Chargement
                resultsContainer.style.display = 'block';
                resultsContainer.classList.add('visible');
                resultsContainer.innerHTML = '<div class="search-status"><div class="spinner-border spinner-border-sm text-white me-2"></div>Recherche...</div>';
                // On ne met pas hasValidResults à true ici, on attend la réponse

                fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal })
                    .then(response => {
                        if (!response.ok) throw new Error('Erreur réseau');
                        return response.json();
                    })
                    .then(json => {
                        const data = Array.isArray(json) ? json : (json.data || []);

                        if (data.length === 0) {
                            resultsContainer.innerHTML = '<div class="search-status">Aucun résultat trouvé.</div>';
                            // On considère "0 résultat" comme un état valide (l'utilisateur peut vouloir revoir ça)
                            hasValidResults = true; 
                        } else {
                            let html = '';
                            data.forEach(item => {
                                const rawImage = item.image || item.image_url;
                                let imgUrl = 'https://via.placeholder.com/40?text=IMG';

                                if (rawImage) {
                                    imgUrl = rawImage.startsWith('http') ? rawImage : `/static/${rawImage}`;
                                }

                                const armoire = item.armoire || 'Sans armoire';
                                const quantite = item.quantite !== undefined ? item.quantite : '?';

                                html += `
                                    <a href="/objet/${item.id}" class="search-result-item">
                                        <img src="${imgUrl}" alt="${item.nom}" class="search-result-img">
                                        <div class="search-result-info">
                                            <h6>${item.nom}</h6>
                                            <small>${armoire} • Qté: ${quantite}</small>
                                        </div>
                                    </a>
                                `;
                            });
                            resultsContainer.innerHTML = html;
                            hasValidResults = true; // ✅ Résultats chargés avec succès
                        }
                    })
                    .catch(error => {
                        if (error.name === 'AbortError') {
                            console.log('Recherche annulée');
                        } else {
                            console.error('Erreur JS recherche:', error);
                            resultsContainer.innerHTML = '<div class="search-status text-danger">Erreur technique.</div>';
                            hasValidResults = false; // ✅ En cas d'erreur, on ne veut pas réafficher ça au focus
                        }
                    });
            }, 300);
        });

        // ---------------------------------------------------------
        // 3. BOUTON CLEAR
        // ---------------------------------------------------------
        if (clearBtn) {
            clearBtn.addEventListener('click', function() {
                globalSearchInput.value = '';
                clearBtn.classList.remove('visible');
                resultsContainer.classList.remove('visible');
                resultsContainer.style.display = 'none';
                globalSearchInput.focus();
                
                hasValidResults = false; // ✅ Reset du flag
                
                if (searchTimeoutHeader) clearTimeout(searchTimeoutHeader);
                if (searchController) searchController.abort();
            });
        }

        // ---------------------------------------------------------
        // 4. FERMETURE AU CLIC EXTÉRIEUR
        // ---------------------------------------------------------
        document.addEventListener('click', function(e) {
            if (!searchWrapper.contains(e.target)) {
                searchWrapper.classList.remove('focused');
                globalSearchInput.classList.remove('expanded');
                resultsContainer.classList.remove('visible');
                resultsContainer.style.display = 'none';
                // Note : On ne reset PAS hasValidResults ici, 
                // pour permettre de réafficher les résultats si on re-clique dans l'input
            }
        });
    }
	
	
    
	
	// =================================================================
	// SECTION 6 : ANIMATION DE LA CLOCHE D'ALERTE
	// =================================================================
	const alertIcon = document.getElementById('alert-icon-link');
	if (alertIcon) {
		const alertCount = parseInt(alertIcon.dataset.alertCount, 10);

		if (alertCount >= 3) {
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
	// GESTION MODALE AJOUT/MODIF (VERSION FINALE & INFAILLIBLE)
	// =================================================================
	const addObjectModalElement = document.getElementById('addObjectModal');
	if (addObjectModalElement) {
		addObjectModalElement.addEventListener('show.bs.modal', function (event) {
			const button = event.relatedTarget; 
			if (!button) return;
			
			const form = addObjectModalElement.querySelector('form');
			const modalTitle = addObjectModalElement.querySelector('.modal-title');
			const submitBtn = form.querySelector('button[type="submit"]');
			
            // --- RÉCUPÉRATION PAR ID (PLUS FIABLE) ---
			const imagePreviewContainer = document.getElementById('image-preview-container');
			const imagePreview = document.getElementById('image-preview');
            const fdsStatusDiv = document.getElementById('fds-current-status');
            const fdsLinkBtn = document.getElementById('fds-current-link');
            const fdsTypeLabel = document.getElementById('fds-current-type');
            const fdsHelpText = document.getElementById('fds-help-text');

            // =========================================================
            // 1. LE GRAND NETTOYAGE (RESET FORCÉ)
            // =========================================================
            console.log("🧹 Nettoyage de la modale...");

            // Reset Image
            if (imagePreviewContainer) imagePreviewContainer.style.display = 'none';
            if (imagePreview) imagePreview.src = '';
            
            // Reset FDS (C'est ici que ça coinçait avant)
            if (fdsStatusDiv) {
                fdsStatusDiv.style.display = 'none'; // On cache la barre verte
                fdsStatusDiv.classList.remove('d-flex'); // On retire la classe flex au cas où
            }
            if (fdsLinkBtn) fdsLinkBtn.href = '#';
            if (fdsTypeLabel) fdsTypeLabel.textContent = '';
            if (fdsHelpText) fdsHelpText.innerHTML = 'Ajoutez un fichier ou un lien pour la sécurité.';
            
            // Reset Onglets (Retour sur le 1er onglet par défaut)
            const tabImgFile = new bootstrap.Tab(document.querySelector('#pills-file-tab'));
            if (tabImgFile) tabImgFile.show();
            
            const btnTabFdsFile = document.querySelector('button[data-bs-target="#nav-file-fds"]');
            if (btnTabFdsFile) new bootstrap.Tab(btnTabFdsFile).show();

            // Reset Inputs cachés et visibles
            form.reset(); 
            const inputImgUrl = form.querySelector('#image_url');
            const inputFdsUrl = form.querySelector('#fds_url');
            if (inputImgUrl) inputImgUrl.value = '';
            if (inputFdsUrl) inputFdsUrl.value = '';
            // =========================================================
			
			const objetId = button.dataset.objetId;
			
			if (objetId) {
				// --- MODE MODIFICATION ---
				modalTitle.textContent = "Modifier l'objet";
				form.action = `/modifier_objet/${objetId}`;
				
				// Données brutes
				const rawImg = (button.dataset.imageUrl || '').trim();
				const rawFds = (button.dataset.fdsUrl || '').trim();
                
                // --- AJOUT CMR : Récupération de la donnée ---
                const isCmr = button.dataset.isCmr === 'on';
                
                console.log(`Objet ID: ${objetId}, FDS: ${rawFds}, CMR: ${isCmr}`); // Debug

				// Remplissage Champs Standards
				const fields = {
					'nom': button.dataset.nom,
					'quantite': button.dataset.quantite,
					'seuil': button.dataset.seuil,
					'date_peremption': button.dataset.datePeremption,
					'armoire_id': button.dataset.armoireId,
					'categorie_id': button.dataset.categorieId
				};
				
				for (const [fieldId, rawValue] of Object.entries(fields)) {
					const input = form.querySelector(`#${fieldId}`);
					if (input) {
                        let value = rawValue;
                        if (value === 'None' || value === null || value === undefined) value = '';
						input.value = value;
					}
				}

                // --- AJOUT CMR : Cocher la case ---
                const cmrCheckbox = document.getElementById('is_cmr');
                if (cmrCheckbox) {
                    cmrCheckbox.checked = isCmr;
                }

				// Gestion Image
                const tabImgUrl = new bootstrap.Tab(document.querySelector('#pills-url-tab'));
                if (rawImg.startsWith('http')) {
                    tabImgUrl.show();
                    if (inputImgUrl) inputImgUrl.value = rawImg;
                }
				
				if (rawImg && rawImg !== 'None' && imagePreview) {
					imagePreview.src = rawImg.startsWith('http') ? rawImg : `/static/${rawImg}`;
					imagePreviewContainer.style.display = 'block';
				}
				
                // --- GESTION FDS (LOGIQUE CORRIGÉE) ---
                // On n'affiche la barre verte QUE si une FDS existe vraiment
                if (rawFds && rawFds !== 'None' && fdsStatusDiv) {
                    console.log("✅ FDS détectée, affichage de la barre verte.");
                    fdsStatusDiv.style.display = 'flex'; // On réaffiche
                    
                    if (fdsHelpText) {
                        fdsHelpText.innerHTML = '<i class="bi bi-info-circle me-1"></i>Une FDS est active. Utilisez ces champs uniquement pour la <strong>remplacer</strong>.';
                    }

                    if (rawFds.startsWith('http')) {
                        fdsTypeLabel.textContent = 'Lien Web Externe';
                        fdsLinkBtn.href = rawFds;
                        
                        const btnTabFdsUrl = document.querySelector('button[data-bs-target="#nav-url-fds"]');
                        if (btnTabFdsUrl) new bootstrap.Tab(btnTabFdsUrl).show();
                        if (inputFdsUrl) inputFdsUrl.value = rawFds;
                    } else {
                        fdsTypeLabel.textContent = 'Fichier PDF Hébergé';
                        fdsLinkBtn.href = `/static/${rawFds}`;
                    }
                }

				if (submitBtn) {
					submitBtn.textContent = 'Mettre à jour';
					submitBtn.className = 'btn btn-primary';
				}
				
			} else {
				// --- MODE AJOUT ---
				modalTitle.textContent = "Ajouter un nouvel objet";
				form.action = document.body.dataset.addUrl || '/ajouter_objet';
				
				if (submitBtn) {
					submitBtn.textContent = 'Enregistrer l\'objet';
					submitBtn.className = 'btn btn-success';
				}
			}
			
			if (typeof setupPexelsSearch === 'function') setupPexelsSearch();
		});
	}
	
	// =================================================================
    // SECTION 14 : MODALE DE SUGGESTION DE COMMANDE (BOOTSTRAP 5)
    // =================================================================
    const suggestionModal = document.getElementById('suggestionModal');
    if (suggestionModal) {
        const suggestionModalInstance = new bootstrap.Modal(suggestionModal);
        
        const objetNomElement = document.getElementById('suggestion-objet-nom');
        const objetIdInput = document.getElementById('suggestion-objet-id');
        const quantityInput = document.getElementById('suggestion-quantity-input');
        const commentaireInput = document.getElementById('suggestion-commentaire');
        const confirmBtn = document.getElementById('suggestion-confirm-btn');

        // 1. OUVERTURE ET CALCUL
        document.addEventListener('click', function(e) {
            const btnSuggest = e.target.closest('.btn-suggest');
            if (btnSuggest) {
                e.preventDefault();
                
                // Récupération des données depuis le bouton HTML
                const objetId = btnSuggest.dataset.objetId;
                const objetNom = btnSuggest.dataset.objetNom;
                
                // Conversion en nombre (le || 0 évite le NaN si l'attribut est vide)
                const stockActuel = parseInt(btnSuggest.dataset.stock) || 0;
                const seuilAlerte = parseInt(btnSuggest.dataset.seuil) || 0;
                
                console.log(`Calcul suggestion : Stock=${stockActuel}, Seuil=${seuilAlerte}`); // Debug console

                // Remplissage UI
                if (objetNomElement) objetNomElement.textContent = objetNom;
                if (objetIdInput) objetIdInput.value = objetId;
                
                // --- CALCUL INTELLIGENT ---
                let proposition = 1; // Valeur par défaut
                
                // Si on est en dessous ou égal au seuil (et que le seuil est défini)
                if (stockActuel <= seuilAlerte && seuilAlerte > 0) {
                    // Objectif : Remonter à 2x le seuil (stock de sécurité)
                    const cible = seuilAlerte * 2;
                    proposition = cible - stockActuel;
                    
                    // Sécurité : on commande au moins 1, et idéalement au moins 5 si c'est du consommable
                    if (proposition < 1) proposition = 1;
                }
                
                if (quantityInput) quantityInput.value = proposition;
                
                // Placeholder contextuel
                if (commentaireInput) {
                    commentaireInput.value = '';
                    if (stockActuel <= seuilAlerte && seuilAlerte > 0) {
                        commentaireInput.placeholder = `Stock critique (${stockActuel}/${seuilAlerte}). Réassort conseillé.`;
                    } else {
                        commentaireInput.placeholder = "Pourquoi cette commande ?";
                    }
                }
                
                suggestionModalInstance.show();
                
                // Focus sur le champ quantité
                setTimeout(() => {
                    if (quantityInput) { quantityInput.focus(); quantityInput.select(); }
                }, 300);
            }
        });

        // 2. RESET FERMETURE
        suggestionModal.addEventListener('hidden.bs.modal', function() {
            if (quantityInput) quantityInput.value = '';
            if (commentaireInput) commentaireInput.value = '';
            if (confirmBtn) {
                confirmBtn.classList.remove('loading');
                confirmBtn.disabled = false;
            }
        });

        // 3. ENVOI (Utilise showToast pour l'affichage propre)
        if (confirmBtn) {
            confirmBtn.addEventListener('click', async function() {
                const objetId = objetIdInput.value;
                const quantite = parseInt(quantityInput.value);
                const commentaire = commentaireInput.value.trim();
                
                if (!quantite || quantite < 1) {
                    quantityInput.classList.add('is-invalid');
                    return;
                }
                quantityInput.classList.remove('is-invalid');
                
                confirmBtn.classList.add('loading');
                confirmBtn.disabled = true;
                
                try {
                    const response = await fetch('/api/suggerer_commande', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({
                            objet_id: objetId,
                            quantite: quantite,
                            commentaire: commentaire
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        // C'EST ICI QUE L'AFFICHAGE SE JOUE
                        // On utilise showToast (la bulle) et non showInfoModal (le truc moche)
                        if (typeof showToast === 'function') {
                            showToast(result.message || 'Suggestion envoyée !', 'success');
                        } else {
                            alert(result.message); // Fallback si showToast n'existe pas
                        }
                        
                        suggestionModalInstance.hide();
                        setTimeout(() => window.location.reload(), 1500);
                    } else {
                        if (typeof showToast === 'function') {
                            showToast(result.error || 'Erreur serveur', 'error');
                        } else {
                            alert(result.error);
                        }
                    }
                } catch (error) {
                    console.error('Erreur:', error);
                    if (typeof showToast === 'function') {
                        showToast('Erreur de connexion', 'error');
                    }
                } finally {
                    confirmBtn.classList.remove('loading');
                    confirmBtn.disabled = false;
                }
            });
        }
    }
    setupPexelsSearch();
	
	// =================================================================
    // SECTION 15 : ANIMATION BREADCRUMB (FIL D'ARIANE)
    // =================================================================
    const breadcrumbLinks = document.querySelectorAll('.breadcrumb-link');
    
    if (breadcrumbLinks.length > 0) {
        breadcrumbLinks.forEach(link => {
            link.addEventListener('mouseenter', function() {
                const separator = this.nextElementSibling;
                if (separator && separator.classList.contains('breadcrumb-separator')) {
                    separator.style.transform = 'scale(1.3) rotate(20deg)';
                    separator.style.color = '#667eea';
                    separator.style.fontWeight = 'bold';
                }
            });
            
            link.addEventListener('mouseleave', function() {
                const separator = this.nextElementSibling;
                if (separator && separator.classList.contains('breadcrumb-separator')) {
                    separator.style.transform = 'scale(1) rotate(0deg)';
                    separator.style.color = '#d1d5db';
                    separator.style.fontWeight = '300';
                }
            });
        });
    }
	
	// =================================================================
    // SECTION 16 : BOUTON RETOUR HAUT (Back To Top)
    // =================================================================
    const backToTopBtn = document.getElementById('backToTopBtn');
    
    if (backToTopBtn) {
        // 1. Gestion de l'apparition au scroll
        window.addEventListener('scroll', () => {
            if (window.scrollY > 300) { // Apparaît après 300px de descente
                backToTopBtn.classList.add('show');
            } else {
                backToTopBtn.classList.remove('show');
            }
        });

        // 2. Action de remontée fluide
        backToTopBtn.addEventListener('click', (e) => {
            e.preventDefault();
            window.scrollTo({
                top: 0,
                behavior: 'smooth' // C'est ça qui fait l'effet "Premium"
            });
        });
    }
});