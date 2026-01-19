/**
 * Keyboard Shortcuts System
 * Power user keyboard shortcuts
 */

class KeyboardShortcuts {
    constructor() {
        this.shortcuts = {};
        this.enabled = true;
        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));
    }

    register(key, description, handler) {
        this.shortcuts[key.toLowerCase()] = { description, handler };
    }

    handleKeyPress(e) {
        if (!this.enabled) return;

        // Ignore if typing in input/textarea
        if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
            // Allow ESC to exit inputs
            if (e.key === 'Escape') {
                e.target.blur();
                return;
            }
            return;
        }

        const key = this.getKeyCombo(e);
        const shortcut = this.shortcuts[key];

        if (shortcut) {
            e.preventDefault();
            shortcut.handler(e);
        }
    }

    getKeyCombo(e) {
        const parts = [];
        if (e.ctrlKey) parts.push('ctrl');
        if (e.altKey) parts.push('alt');
        if (e.shiftKey) parts.push('shift');
        parts.push(e.key.toLowerCase());
        return parts.join('+');
    }

    disable() {
        this.enabled = false;
    }

    enable() {
        this.enabled = true;
    }

    showHelp() {
        const overlay = document.createElement('div');
        overlay.className = 'confirmation-overlay';

        const dialog = document.createElement('div');
        dialog.className = 'confirmation-dialog';
        dialog.style.maxWidth = '600px';

        const shortcuts = Object.entries(this.shortcuts)
            .map(([key, { description }]) => `
                <tr>
                    <td style="padding: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <code style="background: var(--color-bg-tertiary); padding: 0.25rem 0.5rem; border-radius: 4px;">${key}</code>
                    </td>
                    <td style="padding: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.05); color: var(--color-text-secondary);">
                        ${description}
                    </td>
                </tr>
            `).join('');

        dialog.innerHTML = `
            <div class="confirmation-title">⌨️ Keyboard Shortcuts</div>
            <div style="max-height: 400px; overflow-y: auto; margin: 1rem 0;">
                <table style="width: 100%;">
                    ${shortcuts}
                </table>
            </div>
            <div class="confirmation-actions">
                <button class="btn btn-primary close-btn">Close</button>
            </div>
        `;

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        dialog.querySelector('.close-btn').addEventListener('click', () => {
            document.body.removeChild(overlay);
        });

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
            }
        });
    }
}

// Global shortcuts instance
const shortcuts = new KeyboardShortcuts();

// Register default shortcuts
shortcuts.register('?', 'Show keyboard shortcuts', () => shortcuts.showHelp());
shortcuts.register('/', 'Focus search', () => {
    const search = document.getElementById('eventSearchInput') ||
        document.querySelector('input[type="text"]');
    if (search) search.focus();
});
shortcuts.register('escape', 'Close dialogs/modals', () => {
    const overlay = document.querySelector('.confirmation-overlay');
    if (overlay) overlay.remove();
});
shortcuts.register('ctrl+s', 'Save (if in form)', (e) => {
    e.preventDefault();
    toast.info('Auto-save not implemented');
});
shortcuts.register('ctrl+k', 'Search/Command palette', () => {
    toast.info('Command palette coming soon!');
});
