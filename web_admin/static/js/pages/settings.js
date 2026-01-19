/**
 * Settings Page
 */

async function renderSettings() {
    const content = document.getElementById('pageContent');

    content.innerHTML = `
        <div class="fade-in">
            <div class="page-header">
                <h1 class="page-title">Settings</h1>
                <p class="page-subtitle">Ayarlar ve yapılandırma</p>
            </div>

            <!-- API Info -->
            <div class="card mb-2">
                <div class="card-header">
                    <h3 class="card-title">🔑 API Bilgileri</h3>
                </div>
                <div style="padding: 1rem;">
                    <div class="form-group">
                        <label class="form-label">API Key (Kayıtlı)</label>
                        <input type="text" class="form-input" value="${getApiKey()}" readonly>
                    </div>
                    <button class="btn btn-danger" onclick="logout()">
                        <span>🚪</span>
                        <span>Çıkış Yap</span>
                    </button>
                </div>
            </div>

            <!-- Database Info -->
            <div class="card mb-2">
                <div class="card-header">
                    <h3 class="card-title">💾 Veritabanı</h3>
                </div>
                <div style="padding: 1rem;">
                    <p style="color: var(--color-text-secondary); margin-bottom: 1rem;">
                        Web panel, Discord bot ile aynı veritabanını kullanmaktadır: <code>cotabot_dev.db</code>
                    </p>
                    <p style="color: var(--color-text-muted); font-size: 0.875rem;">
                        ⚠️ Veritabanı yedekleme işlemleri için Discord bot'u kullanabilirsiniz.
                    </p>
                </div>
            </div>

            <!-- About -->
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">ℹ️ Hakkında</h3>
                </div>
                <div style="padding: 1rem;">
                    <h4 style="margin-bottom: 0.5rem;">Cotabot Web Admin Panel</h4>
                    <p style="color: var(--color-text-secondary); margin-bottom: 1rem;">
                        Modern web tabanlı admin paneli
                    </p>
                    <p style="color: var(--color-text-muted); font-size: 0.875rem;">
                        Version: 1.0.0<br>
                        Created with ❤️ for Squad community
                    </p>
                </div>
            </div>
        </div>
    `;
}

function logout() {
    if (!confirm('Çıkış yapmak istediğinizden emin misiniz?')) {
        return;
    }

    clearApiKey();
    location.reload();
}
