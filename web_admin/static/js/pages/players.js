/**
 * Players Page
 */

let currentPage = 1;
let searchTerm = '';

async function renderPlayers() {
    const content = document.getElementById('pageContent');

    content.innerHTML = `
        <div class="fade-in">
            <div class="page-header">
                <h1 class="page-title">Player Management</h1>
                <p class="page-subtitle">Oyuncu listesi ve yönetimi</p>
            </div>

            <!-- Actions Bar -->
            <div class="card mb-2">
                <div style="display: flex; gap: 1rem; align-items: center;">
                    <input type="text" id="playerSearch" class="form-input" placeholder="Steam ID veya isim ile ara..." style="flex: 1;">
                    <button class="btn btn-primary" onclick="showAddPlayerModal()">
                        <span>➕</span>
                        <span>Oyuncu Ekle</span>
                    </button>
                </div>
            </div>

            <!-- Players Table -->
            <div class="card">
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Steam ID</th>
                                <th>İsim</th>
                                <th>Discord ID</th>
                                <th>Toplam Skor</th>
                                <th>K/D Oranı</th>
                                <th>Eklenme Tarihi</th>
                                <th>İşlemler</th>
                            </tr>
                        </thead>
                        <tbody id="playersTableBody">
                            <tr>
                                <td colspan="7" style="text-align: center; padding: 2rem;">
                                    <div class="loading-spinner"></div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div id="paginationContainer" style="padding: 1rem; text-align: center;"></div>
            </div>
        </div>
    `;

    // Add search listener
    document.getElementById('playerSearch').addEventListener('input', (e) => {
        searchTerm = e.target.value;
        currentPage = 1;
        loadPlayers();
    });

    // Load players
    await loadPlayers();
}

async function loadPlayers() {
    try {
        const response = await API.getPlayers(currentPage, 20, searchTerm);

        if (response.success) {
            renderPlayersTable(response.data);
            renderPagination(response.pagination);
        }
    } catch (error) {
        console.error('Error loading players:', error);
        document.getElementById('playersTableBody').innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: var(--color-error); padding: 2rem;">
                    Hata: ${error.message}
                </td>
            </tr>
        `;
    }
}

function renderPlayersTable(players) {
    const tbody = document.getElementById('playersTableBody');

    if (players.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 2rem; color: var(--color-text-secondary);">
                    Oyuncu bulunamadı
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = players.map(player => `
        <tr>
            <td><code>${player.steam_id}</code></td>
            <td>${player.name}</td>
            <td>${player.discord_id || '<span style="color: var(--color-text-muted);">-</span>'}</td>
            <td>${player.stats ? player.stats.total_score.toLocaleString() : '-'}</td>
            <td>${player.stats ? player.stats.total_kd_ratio.toFixed(2) : '-'}</td>
            <td>${player.created_at ? new Date(player.created_at).toLocaleDateString('tr-TR') : '-'}</td>
            <td>
                <button class="btn btn-secondary" onclick="viewPlayer('${player.steam_id}')" style="padding: 0.5rem 1rem; font-size: 0.75rem;">
                    👁️ Görüntüle
                </button>
                <button class="btn btn-danger" onclick="deletePlayer('${player.steam_id}')" style="padding: 0.5rem 1rem; font-size: 0.75rem; margin-left: 0.5rem;">
                    🗑️ Sil
                </button>
            </td>
        </tr>
    `).join('');
}

function renderPagination(pagination) {
    const container = document.getElementById('paginationContainer');

    if (pagination.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '<div style="display: flex; gap: 0.5rem; justify-content: center;">';

    for (let i = 1; i <= pagination.total_pages; i++) {
        const isActive = i === currentPage;
        html += `
            <button 
                class="btn ${isActive ? 'btn-primary' : 'btn-secondary'}" 
                onclick="changePage(${i})"
                style="padding: 0.5rem 1rem;">
                ${i}
            </button>
        `;
    }

    html += '</div>';
    container.innerHTML = html;
}

function changePage(page) {
    currentPage = page;
    loadPlayers();
}

function showAddPlayerModal() {
    // Simple prompt-based add (can be enhanced with modal)
    const steamId = prompt('Steam ID:');
    if (!steamId) return;

    const name = prompt('Oyuncu İsmi:');
    if (!name) return;

    const discordId = prompt('Discord ID (opsiyonel):');

    addPlayer({ steam_id: steamId, name: name, discord_id: discordId || null });
}

async function addPlayer(playerData) {
    try {
        const response = await API.addPlayer(playerData);
        if (response.success) {
            alert('Oyuncu başarıyla eklendi!');
            loadPlayers();
        }
    } catch (error) {
        alert('Hata: ' + error.message);
    }
}

async function viewPlayer(steamId) {
    try {
        const response = await API.getPlayer(steamId);
        if (response.success) {
            const player = response.data;
            alert(`
Oyuncu: ${player.name}
Steam ID: ${player.steam_id}
Discord ID: ${player.discord_id || '-'}

== İSTATİSTİKLER ==
Toplam Skor: ${player.stats?.total_score || 0}
Toplam Kill: ${player.stats?.total_kills || 0}
Toplam Death: ${player.stats?.total_deaths || 0}
K/D Oranı: ${player.stats?.total_kd_ratio?.toFixed(2) || 0}
            `);
        }
    } catch (error) {
        alert('Hata: ' + error.message);
    }
}

async function deletePlayer(steamId) {
    if (!confirm(`${steamId} Steam ID'li oyuncuyu silmek istediğinizden emin misiniz?`)) {
        return;
    }

    try {
        const response = await API.deletePlayer(steamId);
        if (response.success) {
            alert('Oyuncu silindi!');
            loadPlayers();
        }
    } catch (error) {
        alert('Hata: ' + error.message);
    }
}
