/**
 * Cotabot Web Admin Panel - Main App
 */

// Page Renderers Map
const pages = {
    dashboard: renderDashboard,
    players: renderPlayers,
    events: renderEvents,
    reports: renderReports,
    server: renderServer,
    settings: renderSettings
};

// Current Page
let currentPageName = 'dashboard';

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is logged in
    const apiKey = getApiKey();

    if (!apiKey) {
        showLoginScreen();
    } else {
        showMainApp();
    }

    // Setup login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // Setup navigation
    setupNavigation();

    // Setup environment selector
    setupEnvironmentSelector();

    // Handle hash changes
    window.addEventListener('hashchange', handleHashChange);

    // Initial page load
    if (apiKey) {
        handleHashChange();
        updatePageTitle();
    }
});

// Login Handler
async function handleLogin(e) {
    e.preventDefault();

    const apiKeyInput = document.getElementById('apiKeyInput');
    const apiKey = apiKeyInput.value.trim();
    const errorDiv = document.getElementById('loginError');

    if (!apiKey) {
        errorDiv.textContent = 'API key gereklidir';
        errorDiv.classList.remove('hidden');
        return;
    }

    try {
        const response = await API.login(apiKey);

        if (response.success) {
            setApiKey(apiKey);
            showMainApp();
        } else {
            errorDiv.textContent = response.error || 'Giriş başarısız';
            errorDiv.classList.remove('hidden');
        }
    } catch (error) {
        errorDiv.textContent = 'Hata: ' + error.message;
        errorDiv.classList.remove('hidden');
    }
}

// Show Login Screen
function showLoginScreen() {
    document.getElementById('loginScreen').classList.remove('hidden');
    document.getElementById('mainApp').classList.add('hidden');
}

// Show Main App
function showMainApp() {
    document.getElementById('loginScreen').classList.add('hidden');
    document.getElementById('mainApp').classList.remove('hidden');

    // Initialize SocketIO for real-time updates
    initSocketIO();

    // Load initial page
    setTimeout(() => {
        handleHashChange();
    }, 100);
}

// Setup Navigation
function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();

            // Update active state
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Navigate to page
            const page = link.getAttribute('data-page');
            navigateToPage(page);
        });
    });
}

// Navigate to Page
function navigateToPage(pageName) {
    // Clean up previous page
    if (currentPageName === 'server') {
        cleanupServerPage();
    }

    currentPageName = pageName;

    // Render page
    if (pages[pageName]) {
        pages[pageName]();
    } else {
        renderNotFound();
    }

    // Update URL hash
    window.location.hash = pageName;
}

// Handle Hash Change
function handleHashChange() {
    const hash = window.location.hash.slice(1) || 'dashboard';

    // Update active nav link
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        const page = link.getAttribute('data-page');
        if (page === hash) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // Navigate
    navigateToPage(hash);
}

// Render Not Found
function renderNotFound() {
    const content = document.getElementById('pageContent');
    content.innerHTML = `
        <div class="fade-in" style="text-align: center; padding: 4rem;">
            <h1 style="font-size: 4rem; margin-bottom: 1rem;">404</h1>
            <p style="color: var(--color-text-secondary); margin-bottom: 2rem;">Sayfa bulunamadı</p>
            <a href="#dashboard" class="btn btn-primary">Ana Sayfaya Dön</a>
        </div>
    `;
}

// Utility: Format Date
function formatDate(dateString) {
    return new Date(dateString).toLocaleString('tr-TR');
}

// Utility: Format DateTime
function formatDateTime(dateString) {
    return new Date(dateString).toLocaleString('tr-TR');
}

// ============================================
// ENVIRONMENT MANAGEMENT
// ============================================

// Setup Environment Selector
function setupEnvironmentSelector() {
    const selector = document.getElementById('environmentSelect');
    const badge = document.getElementById('environmentBadge');

    if (!selector) return;

    // Set initial value
    const currentEnv = getCurrentEnvironment();
    selector.value = currentEnv;
    updateEnvironmentBadge(currentEnv);
    showEnvironmentWarning(currentEnv);

    // Handle environment change
    selector.addEventListener('change', async (e) => {
        const newEnv = e.target.value;
        const currentEnv = getCurrentEnvironment();

        if (newEnv === currentEnv) return;

        // Show confirmation for LIVE
        if (newEnv === 'LIVE') {
            showConfirmation(
                '⚠️ Production Ortamına Geçiş',
                'LIVE ortamına geçmek üzeresiniz. Bu ortamdaki değişiklikler gerçek verileri etkiler. Emin misiniz?',
                async () => {
                    await switchToEnvironment(newEnv);
                },
                () => {
                    // Reset selector to current env
                    selector.value = currentEnv;
                }
            );
        } else {
            await switchToEnvironment(newEnv);
        }
    });
}

// Switch to Environment
async function switchToEnvironment(newEnv) {
    try {
        // Call API to switch environment
        await API.switchEnvironment(newEnv);

        // Update local state
        setCurrentEnvironment(newEnv);

        // Update UI
        updateEnvironmentBadge(newEnv);
        updatePageTitle();
        showEnvironmentWarning(newEnv);

        // Reload current page to fetch new environment data
        if (currentPageName && pages[currentPageName]) {
            pages[currentPageName]();
        }
    } catch (error) {
        console.error('Environment switch failed:', error);
        alert('Ortam değiştirme başarısız: ' + error.message);
        // Reset selector
        document.getElementById('environmentSelect').value = getCurrentEnvironment();
    }
}

// Update Environment Badge
function updateEnvironmentBadge(env) {
    const badge = document.getElementById('environmentBadge');
    if (!badge) return;

    // Update classes
    badge.className = 'environment-badge';
    badge.classList.add(env === 'DEV' ? 'env-dev' : 'env-live');

    // Update content
    const icon = env === 'DEV' ? '🔧' : '🚀';
    badge.innerHTML = `
        <span>${icon}</span>
        <span>${env}</span>
    `;
}

// Update Page Title
function updatePageTitle() {
    const env = getCurrentEnvironment();
    document.title = `Cotabot Admin - ${env}`;
}

// Show Environment Warning
function showEnvironmentWarning(env) {
    // Remove existing warning if any
    const existingWarning = document.querySelector('.environment-warning-banner');
    if (existingWarning) {
        existingWarning.remove();
    }

    // Add warning for LIVE
    if (env === 'LIVE') {
        const content = document.getElementById('pageContent');
        if (!content) return;

        const warning = document.createElement('div');
        warning.className = 'environment-warning-banner';
        warning.innerHTML = `
            <span style="font-size: 1.5rem;">⚠️</span>
            <span><strong>Production Ortamındasınız!</strong> Yapacağınız değişiklikler gerçek verileri etkiler.</span>
        `;

        content.insertBefore(warning, content.firstChild);
    }
}
