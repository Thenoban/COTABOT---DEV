// Event detail modal functions
async function showEventDetails(eventId) {
    try {
        const response = await API.getEventParticipants(eventId);
        if (response.success) {
            // Track which event is currently being viewed for real-time updates
            window.currentEventDetailId = eventId;
            renderEventDetailModal(response);
        } else {
            toast.error('Failed to load event details');
        }
    } catch (error) {
        toast.error('Error loading event details: ' + error.message);
    }
}

function renderEventDetailModal(data) {
    const overlay = document.createElement('div');
    overlay.className = 'confirmation-overlay';

    const modal = document.createElement('div');
    modal.className = 'confirmation-dialog event-detail-modal';
    modal.style.maxWidth = '700px';
    modal.style.maxHeight = '80vh';
    modal.style.overflowY = 'auto';

    const { event, stats, participants } = data;

    modal.innerHTML = `
        \u003cdiv class="confirmation-title"\u003e📅 ${event.title}\u003c/div\u003e
        
        \u003c!-- Stats Section --\u003e
        \u003cdiv class="event-stats-grid"\u003e
            \u003cdiv class="stat-box"\u003e
                \u003cdiv class="stat-label"\u003eTotal Responded\u003c/div\u003e
                \u003cdiv class="stat-value"\u003e${stats.total_responded}\u003c/div\u003e
            \u003c/div\u003e
            \u003cdiv class="stat-box"\u003e
                \u003cdiv class="stat-label"\u003e✅ Joining\u003c/div\u003e
                \u003cdiv class="stat-value"\u003e${stats.join_count}\u003c/div\u003e
            \u003c/div\u003e
            \u003cdiv class="stat-box"\u003e
                \u003cdiv class="stat-label"\u003e❌ Declined\u003c/div\u003e
                \u003cdiv class="stat-value"\u003e${stats.decline_count}\u003c/div\u003e
            \u003c/div\u003e
            \u003cdiv class="stat-box"\u003e
                \u003cdiv class="stat-label"\u003e❔ Maybe\u003c/div\u003e
                \u003cdiv class="stat-value"\u003e${stats.maybe_count}\u003c/div\u003e
            \u003c/div\u003e
        \u003c/div\u003e
        
        \u003c!-- Participants Lists --\u003e
        ${renderParticipantSection('✅ Katılanlar', participants.joined, 'success')}
        ${renderParticipantSection('❌ Katılmayanlar', participants.declined, 'error', true)}
        ${renderParticipantSection('❔ Belki', participants.maybe, 'warning')}
        
        \u003cdiv class="confirmation-actions"\u003e
            \u003cbutton class="btn btn-primary close-btn"\u003eClose\u003c/button\u003e
        \u003c/div\u003e
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Close handlers
    modal.querySelector('.close-btn').addEventListener('click', () => {
        window.currentEventDetailId = null; // Clear tracking
        document.body.removeChild(overlay);
    });

    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            window.currentEventDetailId = null; // Clear tracking
            document.body.removeChild(overlay);
        }
    });
}

function renderParticipantSection(title, participants, type, showExcuse = false) {
    if (participants.length === 0) {
        return `
            \u003cdiv class="participant-section"\u003e
                \u003ch4 class="section-title"\u003e${title} (0)\u003c/h4\u003e
                \u003cp style="color: var(--color-text-secondary); font-size: 0.875rem;"\u003e
                    No participants
                \u003c/p\u003e
            \u003c/div\u003e
        `;
    }

    return `
        \u003cdiv class="participant-section"\u003e
            \u003ch4 class="section-title"\u003e${title} (${participants.length})\u003c/h4\u003e
            \u003cdiv class="participant-list"\u003e
                ${participants.map(p => `
                    \u003cdiv class="participant-item participant-${type}"\u003e
                        \u003cspan class="participant-name"\u003e${p.username}\u003c/span\u003e
                        ${showExcuse && p.excuse ?
            `\u003cspan class="participant-excuse"\u003e"${p.excuse}"\u003c/span\u003e` : ''}
                        ${p.responded_at ?
            `\u003cspan class="participant-time"\u003e${new Date(p.responded_at).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}\u003c/span\u003e` : ''}
                    \u003c/div\u003e
                `).join('')}
            \u003c/div\u003e
        \u003c/div\u003e
    `;
}

// Update event details modal with fresh data (partial update, no DOM recreation)
async function updateEventDetailsModal(event_id) {
    try {
        const response = await API.getEventParticipants(event_id);
        if (!response.success) {
            console.error('Failed to refresh event details:', response.error);
            return;
        }

        const modal = document.querySelector('.event-detail-modal');
        if (!modal) return;

        const { event, stats, participants } = response;

        // Update stats
        const statBoxes = modal.querySelectorAll('.stat-box .stat-value');
        if (statBoxes.length >= 4) {
            statBoxes[0].textContent = stats.total_responded;
            statBoxes[1].textContent = stats.join_count;
            statBoxes[2].textContent = stats.decline_count;
            statBoxes[3].textContent = stats.maybe_count;
        }

        // Update participant sections
        const sections = modal.querySelectorAll('.participant-section');
        if (sections.length >= 3) {
            // Update joined section
            sections[0].innerHTML = `
                \u003ch4 class="section-title"\u003e✅ Katılanlar (${participants.joined.length})\u003c/h4\u003e
                ${participants.joined.length > 0 ? `
                    \u003cdiv class="participant-list"\u003e
                        ${participants.joined.map(p => `
                            \u003cdiv class="participant-item participant-success"\u003e
                                \u003cspan class="participant-name"\u003e${p.username}\u003c/span\u003e
                                ${p.responded_at ?
                    `\u003cspan class="participant-time"\u003e${new Date(p.responded_at).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}\u003c/span\u003e` : ''}
                            \u003c/div\u003e
                        `).join('')}
                    \u003c/div\u003e
                ` : '\u003cp style="color: var(--color-text-secondary); font-size: 0.875rem;"\u003eNo participants\u003c/p\u003e'}
            `;

            // Update declined section
            sections[1].innerHTML = `
                \u003ch4 class="section-title"\u003e❌ Katılmayanlar (${participants.declined.length})\u003c/h4\u003e
                ${participants.declined.length > 0 ? `
                    \u003cdiv class="participant-list"\u003e
                        ${participants.declined.map(p => `
                            \u003cdiv class="participant-item participant-error"\u003e
                                \u003cspan class="participant-name"\u003e${p.username}\u003c/span\u003e
                                ${p.excuse ? `\u003cspan class="participant-excuse"\u003e"${p.excuse}"\u003c/span\u003e` : ''}
                                ${p.responded_at ?
                    `\u003cspan class="participant-time"\u003e${new Date(p.responded_at).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}\u003c/span\u003e` : ''}
                            \u003c/div\u003e
                        `).join('')}
                    \u003c/div\u003e
                ` : '\u003cp style="color: var(--color-text-secondary); font-size: 0.875rem;"\u003eNo participants\u003c/p\u003e'}
            `;

            // Update maybe section
            sections[2].innerHTML = `
                \u003ch4 class="section-title"\u003e❔ Belki (${participants.maybe.length})\u003c/h4\u003e
                ${participants.maybe.length > 0 ? `
                    \u003cdiv class="participant-list"\u003e
                        ${participants.maybe.map(p => `
                            \u003cdiv class="participant-item participant-warning"\u003e
                                \u003cspan class="participant-name"\u003e${p.username}\u003c/span\u003e
                                ${p.responded_at ?
                    `\u003cspan class="participant-time"\u003e${new Date(p.responded_at).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}\u003c/span\u003e` : ''}
                            \u003c/div\u003e
                        `).join('')}
                    \u003c/div\u003e
                ` : '\u003cp style="color: var(--color-text-secondary); font-size: 0.875rem;"\u003eNo participants\u003c/p\u003e'}
            `;
        }

        console.log('✅ Event details modal updated successfully');
    } catch (error) {
        console.error('Error updating event details modal:', error);
    }
}
