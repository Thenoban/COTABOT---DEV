/**
 * Confirmation Dialog Utility
 */

function showConfirmation(title, message, onConfirm, onCancel) {
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'confirmation-overlay';

    // Create dialog
    const dialog = document.createElement('div');
    dialog.className = 'confirmation-dialog';

    dialog.innerHTML = `
        <div class="confirmation-title">${title}</div>
        <div class="confirmation-message">${message}</div>
        <div class="confirmation-actions">
            <button class="btn btn-secondary cancel-btn">İptal</button>
            <button class="btn btn-primary confirm-btn">Onayla</button>
        </div>
    `;

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    // Event listeners
    const confirmBtn = dialog.querySelector('.confirm-btn');
    const cancelBtn = dialog.querySelector('.cancel-btn');

    confirmBtn.addEventListener('click', () => {
        document.body.removeChild(overlay);
        if (onConfirm) onConfirm();
    });

    cancelBtn.addEventListener('click', () => {
        document.body.removeChild(overlay);
        if (onCancel) onCancel();
    });

    // Click outside to close
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            document.body.removeChild(overlay);
            if (onCancel) onCancel();
        }
    });
}
