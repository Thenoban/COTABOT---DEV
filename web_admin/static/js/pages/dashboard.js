/**
 * Dashboard Page
 */

async function renderDashboard() {
    const content = document.getElementById('pageContent');

    content.innerHTML = `
        <div class="fade-in">
            <div class="page-header">
                <h1 class="page-title">Dashboard</h1>
                <p class="page-subtitle">Genel bakış ve istatistikler</p>
            </div>

            <!-- Stats Cards -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-card-header">
                        <div>
                            <div class="stat-label">Toplam Oyuncu</div>
                            <div class="stat-value" id="totalPlayers">-</div>
                        </div>
                        <div class="stat-icon">👥</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-card-header">
                        <div>
                            <div class="stat-label">Aktif Etkinlik</div>
                            <div class="stat-value" id="activeEvents">-</div>
                        </div>
                        <div class="stat-icon">📅</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-card-header">
                        <div>
                            <div class="stat-label">Aktif Oyuncu (7 Gün)</div>
                            <div class="stat-value" id="activePlayers7d">-</div>
                        </div>
                        <div class="stat-icon">🎮</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-card-header">
                        <div>
                            <div class="stat-label">Training Maçları</div>
                            <div class="stat-value" id="trainingMatches">-</div>
                        </div>
                        <div class="stat-icon">🏆</div>
                    </div>
                </div>
            </div>

            <!-- Recent Activity Log -->
            <div class="card mt-3">
                <div class="card-header">
                    <h3 class="card-title">📝 Son Aktiviteler</h3>
                </div>
                <div id="recentActivityList" style="padding: 1rem;">
                    <div class="loading-spinner"></div>
                </div>
            </div>

            <!-- Activity Chart -->
            <div class="card mt-3">
                <div class="card-header">
                    <h3 class="card-title">Son 30 Günlük Aktivite</h3>
                </div>
                <div style="height: 300px; padding: 1rem;">
                    <canvas id="activityChart"></canvas>
                </div>
            </div>
        </div>
    `;

    // Load dashboard stats
    await loadDashboardStats();

    // Load recent activity
    await loadRecentActivity();

    // Load activity chart
    await loadActivityChart();
}

async function loadDashboardStats() {
    try {
        const response = await API.getDashboardStats();

        if (response.success) {
            const stats = response.data;
            document.getElementById('totalPlayers').textContent = stats.total_players;
            document.getElementById('activeEvents').textContent = stats.active_events;
            document.getElementById('activePlayers7d').textContent = stats.active_players_7d;
            document.getElementById('trainingMatches').textContent = stats.training_matches;
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

async function loadRecentActivity() {
    try {
        // Get recent player activities from activity logs
        const response = await API.getActivityChart(7); // Last 7 days
        const container = document.getElementById('recentActivityList');

        if (response.success && response.data.length > 0) {
            const activities = response.data
                .sort((a, b) => new Date(b.date) - new Date(a.date))
                .slice(0, 10); // Top 10 most recent

            container.innerHTML = activities.map(activity => {
                const activityDate = new Date(activity.date);
                const timeAgo = getTimeAgo(activityDate);

                return `
                    <div style="
                        padding: 0.75rem;
                        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    ">
                        <div>
                            <div style="color: var(--color-text-primary); margin-bottom: 0.25rem;">
                                ${activity.players > 0 ? `👥 ${activity.players} oyuncu aktif` : '💤 Aktivite yok'}
                            </div>
                            <div style="color: var(--color-text-secondary); font-size: 0.75rem;">
                                ${Math.round(activity.minutes / 60)} saat oyun süresi
                            </div>
                        </div>
                        <div style="color: var(--color-text-muted); font-size: 0.75rem; text-align: right;">
                            ${timeAgo}<br>
                            <span style="color: var(--color-text-secondary);">${activityDate.toLocaleDateString('tr-TR')}</span>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            container.innerHTML = '<p style="color: var(--color-text-secondary); text-align: center; padding: 2rem;">Son aktivite bulunamadı</p>';
        }
    } catch (error) {
        console.error('Error loading recent activity:', error);
        document.getElementById('recentActivityList').innerHTML =
            '<p style="color: var(--color-error); text-align: center; padding: 2rem;">Aktiviteler yüklenemedi</p>';
    }
}

function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < 60) return 'Az önce';
    if (seconds < 3600) return Math.floor(seconds / 60) + ' dakika önce';
    if (seconds < 86400) return Math.floor(seconds / 3600) + ' saat önce';
    if (seconds < 604800) return Math.floor(seconds / 86400) + ' gün önce';
    return Math.floor(seconds / 604800) + ' hafta önce';
}

async function loadActivityChart() {
    try {
        const response = await API.getActivityChart(30);

        if (response.success) {
            const data = response.data;

            const labels = data.map(d => new Date(d.date).toLocaleDateString('tr-TR', { month: 'short', day: 'numeric' }));
            const players = data.map(d => d.players);
            const minutes = data.map(d => Math.round(d.minutes / 60)); // Convert to hours

            createLineChart('activityChart', labels, [
                {
                    label: 'Oyuncu Sayısı',
                    data: players,
                    borderColor: 'rgb(102, 126, 234)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    yAxisID: 'y'
                },
                {
                    label: 'Toplam Saat',
                    data: minutes,
                    borderColor: 'rgb(0, 242, 254)',
                    backgroundColor: 'rgba(0, 242, 254, 0.1)',
                    yAxisID: 'y1'
                }
            ]);
        }
    } catch (error) {
        console.error('Error loading activity chart:', error);
    }
}
