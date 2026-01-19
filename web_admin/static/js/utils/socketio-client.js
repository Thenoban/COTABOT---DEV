/**
 * SocketIO Client for Real-Time Updates
 */

let socket = null;
let isConnected = false;

// Initialize SocketIO connection
function initSocketIO() {
    if (socket) {
        console.log('SocketIO already initialized');
        return;
    }

    // Connect to the same host
    socket = io({
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 5
    });

    // Connection handlers
    socket.on('connect', () => {
        console.log('✅ SocketIO connected:', socket.id);
        isConnected = true;
    });

    socket.on('disconnect', (reason) => {
        console.log('❌ SocketIO disconnected:', reason);
        isConnected = false;
    });

    socket.on('connect_error', (error) => {
        console.error('SocketIO connection error:', error);
        isConnected = false;
    });

    socket.on('server_message', (data) => {
        console.log('Server message:', data);
    });

    // Event participant update handler
    socket.on('event_participant_update', (data) => {
        console.log('📡 Event participant update received:', data);
        handleEventParticipantUpdate(data);
    });

    console.log('SocketIO client initialized');
}

// Handle event participant updates
function handleEventParticipantUpdate(data) {
    const { event_id, action, user_id, username, status } = data;

    // Show toast notification
    const actionText = status === 'attendee' ? 'joined' :
        status === 'declined' ? 'declined' : 'marked maybe';
    toast.info(`${username} ${actionText} event #${event_id}`);

    // If we're on the events page, refresh the data
    if (window.location.hash === '#events') {
        // Refresh active events if visible
        API.getActiveEvents().then(response => {
            if (response.success) {
                renderActiveEvents(response.data);
            }
        });

        // Refresh events table if visible
        API.getEvents().then(response => {
            if (response.success && window.eventSearchFilter) {
                window.eventSearchFilter = new SearchFilter(
                    response.data,
                    ['title', 'description']
                );
                renderEventsTable(window.eventSearchFilter.getData());
            }
        });
    }

    // If event details modal is open for this event, refresh it
    refreshEventDetailsIfOpen(event_id);
}

// Refresh event details modal if it's currently open
function refreshEventDetailsIfOpen(event_id) {
    // Check if there's an event detail modal currently displayed
    const modals = document.querySelectorAll('.event-detail-modal');
    if (modals.length === 0) return;

    // Get the event_id from the modal if possible
    // We need to track which event is currently being viewed
    if (window.currentEventDetailId === event_id) {
        // Perform partial update instead of recreating modal
        updateEventDetailsModal(event_id);
    }
}

// Get SocketIO instance
function getSocket() {
    return socket;
}

// Check connection status
function isSocketConnected() {
    return isConnected;
}
