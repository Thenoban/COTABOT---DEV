/**
 * Events Page - UPDATED
 */

async function renderEvents() {
    const content = document.getElementById('pageContent');

    content.innerHTML = `
        <div class="fade-in">
            <div class="page-header" style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 class="page-title">Events</h1>
                    <p class="page-subtitle">Etkinlik yönetimi</p>
                </div>
                <div style="display: flex; gap: var(--spacing-sm);">
                    <button id="exportEventsBtn" class="btn btn-secondary" title="Export Events">
                        <span>📥</span>
                        <span>Export</span>
                    </button>
                    <button id="createEventBtn" class="btn btn-primary">
                        <span>➕</span>
                        <span>Yeni Etkinlik</span>
                    </button>
                </div>
            </div>

            <!-- Search and Filter Bar -->
            <div class="card mb-2" style="padding: var(--spacing-md);">
                <div style="display: flex; gap: var(--spacing-md); align-items: center; flex-wrap: wrap;">
                    <input type="text" id="eventSearchInput" class="form-input" placeholder="🔍 Search events..." style="flex: 1; min-width: 250px;">
                    
                    <div style="display: flex; gap: var(--spacing-xs); flex-wrap: wrap;">
                        <button class="filter-chip active" data-filter="all">All</button>
                        <button class="filter-chip" data-filter="active">Active</button>
                        <button class="filter-chip" data-filter="upcoming">Upcoming</button>
                        <button class="filter-chip" data-filter="past">Past</button>
                    </div>
                </div>
            </div>

            <!-- Active Events -->
            <div class="card mb-2">
                <div class="card-header">
                    <h3 class="card-title">Aktif Etkinlikler</h3>
                </div>
                <div id="activeEventsList" style="padding: 1rem;">
                    <div class="loading-spinner"></div>
                </div>
            </div>

            <!-- All Events -->
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Tüm Etkinlikler</h3>
                    <span id="eventsCount" style="color: var(--color-text-secondary); font-size: 0.875rem;"></span>
                </div>
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Başlık</th>
                                <th>Tarih</th>
                                <th>Durum</th>
                                <th>Katılımcı</th>
                            </tr>
                        </thead>
                        <tbody id="eventsTableBody">
                            <tr>
                                <td colspan="5" style="text-align: center; padding: 2rem;">
                                    <div class="loading-spinner"></div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    // Setup event listeners
    document.getElementById('createEventBtn').addEventListener('click', showCreateEventDialog);
    document.getElementById('exportEventsBtn').addEventListener('click', exportEvents);

    // Setup search
    const searchInput = document.getElementById('eventSearchInput');
    searchInput.addEventListener('input', debounce((e) => {
        if (window.eventSearchFilter) {
            window.eventSearchFilter.search(e.target.value);
            renderEventsTable(window.eventSearchFilter.getData());
        }
    }, 300));

    // Setup filters
    document.querySelectorAll('.filter-chip').forEach(chip => {
        chip.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            e.target.classList.add('active');
            applyEventFilter(e.target.dataset.filter);
        });
    });

    await loadEvents();
}

async function loadEvents() {
    try {
        // Load active events
        const activeResponse = await API.getActiveEvents();
        if (activeResponse.success) {
            renderActiveEvents(activeResponse.data);
        }

        // Load all events
        const allResponse = await API.getEvents();
        if (allResponse.success) {
            // Initialize search/filter
            window.eventSearchFilter = new SearchFilter(
                allResponse.data,
                ['title', 'description']
            );
            renderEventsTable(allResponse.data);
            updateEventsCount(allResponse.data.length);
        }
    } catch (error) {
        console.error('Error loading events:', error);
        toast.error('Failed to load events');
    }
}

function renderActiveEvents(events) {
    const container = document.getElementById('activeEventsList');

    if (events.length === 0) {
        container.innerHTML = '<p style="color: var(--color-text-secondary);">Aktif etkinlik bulunamadı</p>';
        return;
    }

    container.innerHTML = events.map(event => `
        <div class="card" style="margin-bottom: 1rem;">
            <h4 style="margin-bottom: 0.5rem;">${event.title}</h4>
            <p style="color: var(--color-text-secondary); font-size: 0.875rem; margin-bottom: 0.5rem;">
                ${new Date(event.timestamp).toLocaleString('tr-TR')}
            </p>
            <p style="color: var(--color-text-secondary); font-size: 0.875rem;">
                👥 ${event.participants_count} katılımcı
            </p>
        </div>
    `).join('');
}

function renderEventsTable(events) {
    const tbody = document.getElementById('eventsTableBody');

    if (events.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 2rem; color: var(--color-text-secondary);">
                    Etkinlik bulunamadı
                </td>
            </tr>
        `;
        updateEventsCount(0);
        return;
    }

    tbody.innerHTML = events.map(event => `
        <tr class="event-row-clickable" onclick="showEventDetails(${event.event_id})" style="cursor: pointer;" title="Detayları görüntülemek için tıklayın">
            <td>${event.event_id}</td>
            <td>${event.title}</td>
            <td>${new Date(event.timestamp).toLocaleString('tr-TR')}</td>
            <td>
                <span style="color: ${event.active ? 'var(--color-success)' : 'var(--color-text-muted)'};">
                    ${event.active ? '✅ Aktif' : '❌ Pasif'}
                </span>
            </td>
            <td>${event.participants_count || 0}</td>
        </tr>
    `).join('');

    updateEventsCount(events.length);
}

function updateEventsCount(count) {
    const countEl = document.getElementById('eventsCount');
    if (countEl) {
        countEl.textContent = `${count} event${count !== 1 ? 's' : ''}`;
    }
}

function applyEventFilter(filterType) {
    if (!window.eventSearchFilter) return;

    window.eventSearchFilter.clearFilters();

    const now = new Date();

    switch (filterType) {
        case 'active':
            window.eventSearchFilter.applyFilter('active', event => event.active);
            break;
        case 'upcoming':
            window.eventSearchFilter.applyFilter('upcoming', event => {
                return new Date(event.timestamp) > now;
            });
            break;
        case 'past':
            window.eventSearchFilter.applyFilter('past', event => {
                return new Date(event.timestamp) < now;
            });
            break;
        case 'all':
        default:
            // No filter
            break;
    }

    renderEventsTable(window.eventSearchFilter.getData());
}

function exportEvents() {
    if (!window.eventSearchFilter) {
        toast.warning('No events to export');
        return;
    }

    const data = window.eventSearchFilter.getData();
    const timestamp = new Date().toISOString().split('T')[0];

    // Show export options
    const overlay = document.createElement('div');
    overlay.className = 'confirmation-overlay';

    const dialog = document.createElement('div');
    dialog.className = 'confirmation-dialog';

    dialog.innerHTML = `
        <div class="confirmation-title">📥 Export Events</div>
        <div class="confirmation-message">
            Choose export format for ${data.length} event(s)
        </div>
        <div class="confirmation-actions">
            <button class="btn btn-secondary cancel-btn">Cancel</button>
            <button class="btn btn-primary csv-btn">CSV</button>
            <button class="btn btn-primary json-btn">JSON</button>
        </div>
    `;

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    dialog.querySelector('.csv-btn').addEventListener('click', () => {
        exporter.exportToCSV(data, `events_${timestamp}.csv`);
        document.body.removeChild(overlay);
    });

    dialog.querySelector('.json-btn').addEventListener('click', () => {
        exporter.exportToJSON(data, `events_${timestamp}.json`);
        document.body.removeChild(overlay);
    });

    dialog.querySelector('.cancel-btn').addEventListener('click', () => {
        document.body.removeChild(overlay);
    });
}

// Event Creation Dialog
function showCreateEventDialog() {
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'confirmation-overlay';

    // Create dialog
    const dialog = document.createElement('div');
    dialog.className = 'confirmation-dialog';
    dialog.style.maxWidth = '500px';

    dialog.innerHTML = `
        <div class="confirmation-title">🎉 Yeni Etkinlik Oluştur</div>
        <div style="margin-bottom: 1.5rem;">
            <div class="form-group">
                <label class="form-label">Başlık *</label>
                <input type="text" id="eventTitle" class="form-input" placeholder="Etkinlik başlığı" required>
            </div>
            <div class="form-group">
                <label class="form-label">Açıklama</label>
                <textarea id="eventDescription" class="form-input" rows="3" placeholder="Etkinlik açıklaması"></textarea>
            </div>
            <div class="form-group">
                <label class="form-label">Tarih ve Saat *</label>
                <input type="datetime-local" id="eventDateTime" class="form-input" required>
            </div>
            <div class="form-group">
                <label class="form-label">Discord Kanal ID *</label>
                <input type="text" id="eventChannelId" class="form-input" placeholder="örn: 1234567890" required>
                <small style="color: var(--color-text-secondary); font-size: 0.75rem;">
                    Etkinlik duyurusunun atılacağı Discord kanal ID'si
                </small>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                    <input type="checkbox" id="eventMentionEveryone" checked>
                    <span>@everyone ile duyur</span>
                </label>
            </div>
        </div>
        <div class="confirmation-actions">
            <button class="btn btn-secondary cancel-btn">İptal</button>
            <button class="btn btn-primary create-btn">Oluştur ve Duyur</button>
        </div>
    `;

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    // Event listeners
    const createBtn = dialog.querySelector('.create-btn');
    const cancelBtn = dialog.querySelector('.cancel-btn');

    createBtn.addEventListener('click', async () => {
        const title = document.getElementById('eventTitle').value.trim();
        const description = document.getElementById('eventDescription').value.trim();
        const dateTime = document.getElementById('eventDateTime').value;
        const channelId = document.getElementById('eventChannelId').value.trim();
        const mentionEveryone = document.getElementById('eventMentionEveryone').checked;

        if (!title || !dateTime || !channelId) {
            alert('Başlık, tarih ve kanal ID zorunludur!');
            return;
        }

        try {
            const response = await API.createEvent({
                title,
                description,
                timestamp: new Date(dateTime).toISOString(),
                channel_id: channelId,
                mention_everyone: mentionEveryone
            });

            if (response.success) {
                document.body.removeChild(overlay);
                await loadEvents();
                toast.success(`Event "${title}" created and announced to Discord!`);
            } else {
                toast.error('Failed to create event: ' + (response.error || 'Unknown error'));
            }
        } catch (error) {
            toast.error('Error: ' + error.message);
        }
    });

    cancelBtn.addEventListener('click', () => {
        document.body.removeChild(overlay);
    });

    // Click outside to close
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            document.body.removeChild(overlay);
        }
    });
}
