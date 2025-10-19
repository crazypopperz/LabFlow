document.addEventListener('DOMContentLoaded', function() {
    // On sélectionne les éléments HTML dont on a besoin
    const fileInput = document.getElementById('fichier_excel');
    const dropZone = document.getElementById('drop-zone');
    
    // On vérifie que les éléments existent avant de continuer
    if (!fileInput || !dropZone) {
        return; 
    }

    const fileMsg = dropZone.querySelector('.file-msg');
    const originalMsg = fileMsg.innerHTML;

    // On écoute l'événement 'change' sur le champ de fichier
    fileInput.addEventListener('change', function() {
        if (this.files && this.files.length > 0) {
            // Si un fichier est sélectionné, on met à jour le message et le style
            fileMsg.innerHTML = `Fichier sélectionné : <strong>${this.files[0].name}</strong>`;
            dropZone.classList.add('file-selected');
        } else {
            // Si la sélection est annulée, on revient à l'état initial
            fileMsg.innerHTML = originalMsg;
            dropZone.classList.remove('file-selected');
        }
    });
});