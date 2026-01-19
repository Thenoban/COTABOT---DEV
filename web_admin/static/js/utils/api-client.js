/**
 * API Client - Handles all API requests
 */

// API Configuration
const API_BASE_URL = window.location.origin;
let API_KEY = localStorage.getItem('cotabot_api_key') || '';
let CURRENT_ENVIRONMENT = localStorage.getItem('current_environment') || 'DEV';

// Set API Key
function setApiKey(key) {
    API_KEY = key;
    localStorage.setItem('cotabot_api_key', key);
}

// Get API Key
function getApiKey() {
    return API_KEY;
}

// Clear API Key (Logout)
function clearApiKey() {
    API_KEY = '';
    localStorage.removeItem('cotabot_api_key');
}

// Environment Management
function getCurrentEnvironment() {
    return CURRENT_ENVIRONMENT;
}

function setCurrentEnvironment(env) {
    CURRENT_ENVIRONMENT = env;
    localStorage.setItem('current_environment', env);
}

// Generic API Request Function
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    // Add API key to headers if available
    if (API_KEY) {
        headers['X-API-Key'] = API_KEY;
    }

    // Add environment header
    headers['X-Environment'] = CURRENT_ENVIRONMENT;

    const config = {
        ...options,
        headers,
        credentials: 'include' // Important for session cookies
    };

    try {
        const response = await fetch(url, config);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'API request failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// API Methods
const API = {
    // Auth
    login: (apiKey) => apiRequest('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ api_key: apiKey })
    }),

    // Dashboard
    getDashboardStats: () => apiRequest('/api/stats/dashboard'),
    getActivityChart: (days = 30) => apiRequest(`/api/stats/activity-chart?days=${days}`),

    // Players
    getPlayers: (page = 1, pageSize = 20, search = '') => {
        let url = `/api/players?page=${page}&page_size=${pageSize}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        return apiRequest(url);
    },
    getPlayer: (steamId) => apiRequest(`/api/players/${steamId}`),
    addPlayer: (playerData) => apiRequest('/api/players', {
        method: 'POST',
        body: JSON.stringify(playerData)
    }),
    updatePlayer: (steamId, playerData) => apiRequest(`/api/players/${steamId}`, {
        method: 'PUT',
        body: JSON.stringify(playerData)
    }),
    deletePlayer: (steamId) => apiRequest(`/api/players/${steamId}`, {
        method: 'DELETE'
    }),

    // Events
    getEvents: () => apiRequest('/api/events'),
    getActiveEvents: () => apiRequest('/api/events/active'),
    getEventParticipants: (eventId) => apiRequest(`/api/events/${eventId}/participants`),
    createEvent: (eventData) => apiRequest('/api/events', {
        method: 'POST',
        body: JSON.stringify(eventData)
    }),

    // Reports
    getHallOfFame: () => apiRequest('/api/reports/hall-of-fame'),

    // Server
    getServerStatus: () => apiRequest('/api/server/status'),

    //Environment Management
    getEnvironment: () => apiRequest('/api/environment'),
    switchEnvironment: (environment) => apiRequest('/api/environment/switch', {
        method: 'POST',
        body: JSON.stringify({ environment })
    }),
    listEnvironments: () => apiRequest('/api/environments'),

    // Activity Log
    getRecentActivity: (limit = 20) => apiRequest(`/api/activity/recent?limit=${limit}`)
};
