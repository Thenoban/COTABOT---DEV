/**
 * Reports Page
 */

async function renderReports() {
    const content = document.getElementById('pageContent');

    content.innerHTML = `
        <div class="fade-in">
            <div class="page-header">
                <h1 class="page-title">Reports</h1>
                <p class="page-subtitle">Raporlar ve başarılar</p>
            </div>

            <!-- Hall of Fame -->
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">🏆 Hall of Fame</h3>
                </div>
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Kategori</th>
                                <th>Oyuncu</th>
                                <th>Değer</th>
                                <th>Tarih</th>
                            </tr>
                        </thead>
                        <tbody id="hallOfFameBody">
                            <tr>
                                <td colspan="4" style="text-align: center; padding: 2rem;">
                                    <div class="loading-spinner"></div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    await loadHallOfFame();
}

async function loadHallOfFame() {
    try {
        const response = await API.getHallOfFame();

        if (response.success) {
            const tbody = document.getElementById('hallOfFameBody');

            if (response.data.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="4" style="text-align: center; padding: 2rem; color: var(--color-text-secondary);">
                            Hall of Fame kaydı bulunamadı
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = response.data.map(record => `
                <tr>
                    <td>${formatRecordType(record.record_type)}</td>
                    <td>${record.player_name || '-'}</td>
                    <td><strong>${record.value.toLocaleString()}</strong></td>
                    <td>${record.achieved_at ? new Date(record.achieved_at).toLocaleDateString('tr-TR') : '-'}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading Hall of Fame:', error);
        document.getElementById('hallOfFameBody').innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; color: var(--color-error); padding: 2rem;">
                    Hata: ${error.message}
                </td>
            </tr>
        `;
    }
}

function formatRecordType(type) {
    const types = {
        'highest_weekly_score': '📈 En Yüksek Haftalık Skor',
        'highest_monthly_score': '📊 En Yüksek Aylık Skor',
        'highest_kd': '🎯 En Yüksek K/D',
        'most_kills': '⚔️ En Çok Kill',
        'most_revives': '💉 En Çok Revive'
    };
    return types[type] || type;
}
