/**
 * Server Status Page
 */

let serverStatusInterval = null;

async function renderServer() {
    const content = document.getElementById('pageContent');

    content.innerHTML = `
        <div class="fade-in">
            <div class="page-header">
                <h1 class="page-title">Server Status</h1>
                <p class="page-subtitle">Sunucu durumu ve bilgileri</p>
            </div>

            <!-- Server Status Card -->
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Squad Server</h3>
                    <div>
                        <button class="btn btn-secondary" onclick="refreshServerStatus()">
                            🔄 Yenile
                        </button>
                    </div>
                </div>
                <div id="serverStatusContent" style="padding: 1rem;">
                    <div class="loading-spinner"></div>
                </div>
            </div>
        </div>
    `;

    await loadServerStatus();

    // Auto-refresh every 30 seconds
    if (serverStatusInterval) {
        clearInterval(serverStatusInterval);
    }
    serverStatusInterval = setInterval(loadServerStatus, 30000);
}

async function loadServerStatus() {
    try {
        const response = await API.getServerStatus();

        if (response.success) {
            renderServerStatus(response.data);
        }
    } catch (error) {
        console.error('Error loading server status:', error);
        document.getElementById('serverStatusContent').innerHTML = `
            <p style="color: var(--color-error);">Hata: ${error.message}</p>
        `;
    }
}

function renderServerStatus(status) {
    const container = document.getElementById('serverStatusContent');

    const statusColor = status.online ? 'var(--color-success)' : 'var(--color-error)';
    const statusText = status.online ? '🟢 Online' : '🔴 Offline';

    container.innerHTML = `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Durum</div>
                <div class="stat-value" style="color: ${statusColor};">${statusText}</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Oyuncu Sayısı</div>
                <div class="stat-value">${status.players}/${status.max_players}</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Harita</div>
                <div class="stat-value" style="font-size: 1.25rem;">${status.map}</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Sunucu Adı</div>
                <div class="stat-value" style="font-size: 1.25rem;">${status.server_name}</div>
            </div>
        </div>
        <p style="color: var(--color-text-muted); text-align: center; margin-top: 1rem; font-size: 0.875rem;">
            Son güncelleme: ${new Date().toLocaleTimeString('tr-TR')}
        </p>
    `;
}

function refreshServerStatus() {
    loadServerStatus();
}

// Cleanup interval when leaving page
function cleanupServerPage() {
    if (serverStatusInterval) {
        clearInterval(serverStatusInterval);
        serverStatusInterval = null;
    }
}
