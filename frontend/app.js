/**
 * PriceAlert Pro - Real-Time Trading Dashboard
 * Modern vanilla JavaScript application with WebSocket integration
 */

// ============================================
// CONFIGURATION
// ============================================
const CONFIG = {
    API_URL: 'http://localhost:8000',
    WS_URL: 'ws://localhost:8000/prices/ws',
    RECONNECT_DELAY: 3000,
    PRICE_UPDATE_ANIMATION_DURATION: 300,
};

// ============================================
// STATE MANAGEMENT
// ============================================
const state = {
    user: null,
    token: null,
    alerts: [],
    prices: {},
    ws: null,
    isConnected: false,
    activeFilter: 'all',
};

// Instrument metadata with categories
const INSTRUMENTS = {
    // Crypto
    BTC: { name: 'Bitcoin', category: 'crypto', icon: '₿' },
    ETH: { name: 'Ethereum', category: 'crypto', icon: 'Ξ' },
    SOL: { name: 'Solana', category: 'crypto', icon: 'S' },
    XRP: { name: 'Ripple', category: 'crypto', icon: 'X' },
    ADA: { name: 'Cardano', category: 'crypto', icon: 'A' },
    DOGE: { name: 'Dogecoin', category: 'crypto', icon: 'Ð' },
    DOT: { name: 'Polkadot', category: 'crypto', icon: '●' },
    AVAX: { name: 'Avalanche', category: 'crypto', icon: 'A' },
    LINK: { name: 'Chainlink', category: 'crypto', icon: '⬡' },
    MATIC: { name: 'Polygon', category: 'crypto', icon: 'M' },
    LTC: { name: 'Litecoin', category: 'crypto', icon: 'Ł' },
    UNI: { name: 'Uniswap', category: 'crypto', icon: '🦄' },
    ATOM: { name: 'Cosmos', category: 'crypto', icon: '⚛' },

    // Stocks
    APPLE: { name: 'Apple Inc.', category: 'stocks', icon: '' },
    MICROSOFT: { name: 'Microsoft', category: 'stocks', icon: 'M' },
    GOOGLE: { name: 'Alphabet', category: 'stocks', icon: 'G' },
    AMAZON: { name: 'Amazon', category: 'stocks', icon: 'A' },
    NVIDIA: { name: 'NVIDIA', category: 'stocks', icon: 'N' },
    META: { name: 'Meta', category: 'stocks', icon: 'M' },
    TESLA: { name: 'Tesla', category: 'stocks', icon: 'T' },
    RELIANCE: { name: 'Reliance', category: 'stocks', icon: 'R' },
    TCS: { name: 'TCS', category: 'stocks', icon: 'T' },
    INFOSYS: { name: 'Infosys', category: 'stocks', icon: 'I' },

    // Indices
    NIFTY50: { name: 'NIFTY 50', category: 'indices', icon: 'N' },
    SENSEX: { name: 'SENSEX', category: 'indices', icon: 'S' },
    SP500: { name: 'S&P 500', category: 'indices', icon: 'S' },
    NASDAQ: { name: 'NASDAQ', category: 'indices', icon: 'N' },
    DOWJONES: { name: 'Dow Jones', category: 'indices', icon: 'D' },
    BANKNIFTY: { name: 'Bank NIFTY', category: 'indices', icon: 'B' },

    // Commodities
    GOLD: { name: 'Gold', category: 'commodities', icon: 'Au' },
    SILVER: { name: 'Silver', category: 'commodities', icon: 'Ag' },
    CRUDE_OIL: { name: 'Crude Oil', category: 'commodities', icon: '🛢' },
    NATURAL_GAS: { name: 'Natural Gas', category: 'commodities', icon: '⛽' },
};

// ============================================
// UTILITY FUNCTIONS
// ============================================
function formatPrice(price, symbol = '') {
    if (!price && price !== 0) return '--';

    // Determine formatting based on price magnitude and category
    const info = INSTRUMENTS[symbol];
    const isCrypto = info?.category === 'crypto';

    if (price >= 1000) {
        return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } else if (price >= 1) {
        return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
    } else {
        return price.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 8 });
    }
}

function formatChange(change) {
    if (!change && change !== 0) return '--';
    const prefix = change >= 0 ? '+' : '';
    return `${prefix}${change.toFixed(2)}%`;
}

function formatTime(date) {
    return new Date(date).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============================================
// API FUNCTIONS
// ============================================
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }

    try {
        const response = await fetch(`${CONFIG.API_URL}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || 'Request failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

async function login(email, password) {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${CONFIG.API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(error.detail);
    }

    const data = await response.json();
    state.token = data.access_token;
    localStorage.setItem('token', data.access_token);

    await fetchUserProfile();
    await fetchAlerts();

    return data;
}

async function register(email, password, phone) {
    return apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, phone }),
    });
}

async function fetchUserProfile() {
    try {
        const user = await apiRequest('/auth/me');
        state.user = user;
        updateUserUI();
    } catch (error) {
        logout();
    }
}

async function fetchAlerts() {
    try {
        state.alerts = await apiRequest('/alerts');
        renderAlerts();
        updateStatsUI();
    } catch (error) {
        console.error('Failed to fetch alerts:', error);
    }
}

async function createAlert(alertData) {
    const alert = await apiRequest('/alerts', {
        method: 'POST',
        body: JSON.stringify(alertData),
    });
    state.alerts.unshift(alert);
    renderAlerts();
    updateStatsUI();
    return alert;
}

async function deleteAlert(alertId) {
    await apiRequest(`/alerts/${alertId}`, { method: 'DELETE' });
    state.alerts = state.alerts.filter(a => a.id !== alertId);
    renderAlerts();
    updateStatsUI();
}

async function toggleAlert(alertId) {
    const alert = await apiRequest(`/alerts/${alertId}/toggle`, { method: 'POST' });
    const index = state.alerts.findIndex(a => a.id === alertId);
    if (index !== -1) {
        state.alerts[index] = alert;
        renderAlerts();
    }
    return alert;
}

function logout() {
    state.user = null;
    state.token = null;
    state.alerts = [];
    localStorage.removeItem('token');
    updateUserUI();
    renderAlerts();
}

// ============================================
// WEBSOCKET CONNECTION
// ============================================
function connectWebSocket() {
    if (state.ws?.readyState === WebSocket.OPEN) return;

    state.ws = new WebSocket(CONFIG.WS_URL);

    state.ws.onopen = () => {
        console.log('WebSocket connected');
        state.isConnected = true;
        updateConnectionStatus(true);
    };

    state.ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);

            if (data.type === 'snapshot') {
                // Initial price snapshot
                Object.entries(data.prices).forEach(([symbol, priceData]) => {
                    state.prices[symbol] = priceData;
                });
                renderPriceGrid();
            } else if (data.type === 'heartbeat') {
                // Keep-alive, ignore
            } else if (data.symbol) {
                // Individual price update
                const oldPrice = state.prices[data.symbol]?.price;
                state.prices[data.symbol] = data;
                updatePriceCard(data.symbol, data, oldPrice);
            }
        } catch (error) {
            console.error('WebSocket message error:', error);
        }
    };

    state.ws.onclose = () => {
        console.log('WebSocket disconnected');
        state.isConnected = false;
        updateConnectionStatus(false);

        // Reconnect after delay
        setTimeout(connectWebSocket, CONFIG.RECONNECT_DELAY);
    };

    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function sendWebSocketMessage(message) {
    if (state.ws?.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify(message));
    }
}

// ============================================
// UI RENDERING
// ============================================
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connectionStatus');
    const dotEl = statusEl.querySelector('.status-dot');
    const textEl = statusEl.querySelector('.status-text');

    if (connected) {
        statusEl.classList.add('connected');
        textEl.textContent = 'Live';
    } else {
        statusEl.classList.remove('connected');
        textEl.textContent = 'Reconnecting...';
    }
}

function updateUserUI() {
    const userMenu = document.getElementById('userMenu');

    if (state.user) {
        userMenu.innerHTML = `
            <div class="user-info">
                <div class="user-avatar">${state.user.email[0].toUpperCase()}</div>
                <button class="btn btn-ghost btn-sm" id="logoutBtn">Logout</button>
            </div>
        `;
        document.getElementById('logoutBtn').addEventListener('click', logout);
    } else {
        userMenu.innerHTML = `<button class="btn btn-primary" id="loginBtn">Sign In</button>`;
        document.getElementById('loginBtn').addEventListener('click', () => openModal('authModal'));
    }
}

function updateStatsUI() {
    const activeAlertsEl = document.getElementById('activeAlerts');
    const triggeredEl = document.getElementById('triggeredToday');

    const activeCount = state.alerts.filter(a => a.active).length;
    const triggeredCount = state.alerts.reduce((sum, a) => sum + (a.triggered_count || 0), 0);

    activeAlertsEl.textContent = activeCount;
    triggeredEl.textContent = triggeredCount;
}

function renderPriceGrid() {
    const grid = document.getElementById('priceGrid');
    const filter = state.activeFilter;

    // Get prices to display
    let pricesToShow = Object.entries(state.prices);

    if (filter !== 'all') {
        pricesToShow = pricesToShow.filter(([symbol]) => {
            const info = INSTRUMENTS[symbol];
            return info?.category === filter;
        });
    }

    if (pricesToShow.length === 0) {
        grid.innerHTML = `
            <div class="loading-state">
                <div class="loader"></div>
                <span>Waiting for price data...</span>
            </div>
        `;
        return;
    }

    grid.innerHTML = pricesToShow.map(([symbol, data]) => createPriceCardHTML(symbol, data)).join('');

    // Add click handlers
    grid.querySelectorAll('.price-card').forEach(card => {
        card.addEventListener('click', () => {
            const symbol = card.dataset.symbol;
            openCreateAlertModal(symbol);
        });
    });
}

function createPriceCardHTML(symbol, data) {
    const info = INSTRUMENTS[symbol] || { name: symbol, category: 'other', icon: symbol[0] };
    const price = data.price || 0;
    const change = calculatePriceChange(symbol);
    const isPositive = change >= 0;

    return `
        <div class="price-card ${isPositive ? 'positive' : 'negative'}" data-symbol="${symbol}">
            <div class="price-header">
                <div class="price-symbol">
                    <div class="symbol-icon ${info.category}">${info.icon}</div>
                    <div class="symbol-info">
                        <h4>${symbol}</h4>
                        <span>${info.name}</span>
                    </div>
                </div>
                <div class="change-badge">${formatChange(change)}</div>
            </div>
            <div class="price-chart">${generateMiniChart(symbol, isPositive)}</div>
            <div class="price-value">$${formatPrice(price, symbol)}</div>
            <div class="price-meta">
                <span>${info.category.toUpperCase()}</span>
                <span>${data.timestamp ? formatTime(data.timestamp) : '--:--:--'}</span>
            </div>
        </div>
    `;
}

function updatePriceCard(symbol, data, oldPrice) {
    const card = document.querySelector(`.price-card[data-symbol="${symbol}"]`);
    if (!card) return;

    const priceEl = card.querySelector('.price-value');
    const change = calculatePriceChange(symbol);
    const isPositive = change >= 0;

    // Update classes
    card.classList.remove('positive', 'negative');
    card.classList.add(isPositive ? 'positive' : 'negative');

    // Update price with flash animation
    priceEl.textContent = `$${formatPrice(data.price, symbol)}`;
    priceEl.classList.add('price-update');
    setTimeout(() => priceEl.classList.remove('price-update'), CONFIG.PRICE_UPDATE_ANIMATION_DURATION);

    // Update change badge
    const changeEl = card.querySelector('.change-badge');
    changeEl.textContent = formatChange(change);

    // Update time
    const timeEl = card.querySelector('.price-meta span:last-child');
    timeEl.textContent = data.timestamp ? formatTime(data.timestamp) : '--:--:--';
}

function calculatePriceChange(symbol) {
    // Simulate change for demo (in production, this would come from the API)
    return (Math.random() - 0.48) * 10;
}

function generateMiniChart(symbol, isPositive) {
    // Generate SVG sparkline
    const points = [];
    let y = 20;
    for (let i = 0; i < 20; i++) {
        y += (Math.random() - 0.5) * 8;
        y = Math.max(5, Math.min(35, y));
        points.push(`${i * 14},${y}`);
    }

    const color = isPositive ? '#22C55E' : '#EF4444';

    return `
        <svg width="100%" height="40" viewBox="0 0 280 40" preserveAspectRatio="none">
            <defs>
                <linearGradient id="gradient-${symbol}" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" style="stop-color:${color};stop-opacity:0.3"/>
                    <stop offset="100%" style="stop-color:${color};stop-opacity:0"/>
                </linearGradient>
            </defs>
            <polyline
                fill="none"
                stroke="${color}"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                points="${points.join(' ')}"
            />
            <polygon
                fill="url(#gradient-${symbol})"
                points="${points.join(' ')} 280,40 0,40"
            />
        </svg>
    `;
}

function renderAlerts() {
    const list = document.getElementById('alertsList');

    if (!state.user) {
        list.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                    <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                </svg>
                <h3>Sign in to create alerts</h3>
                <p>Track prices and get notified instantly</p>
            </div>
        `;
        return;
    }

    if (state.alerts.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                    <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                </svg>
                <h3>No alerts yet</h3>
                <p>Create your first price alert to get started</p>
            </div>
        `;
        return;
    }

    list.innerHTML = state.alerts.map(alert => createAlertCardHTML(alert)).join('');

    // Add event listeners
    list.querySelectorAll('.alert-toggle').forEach(toggle => {
        toggle.addEventListener('click', async (e) => {
            const alertId = parseInt(e.target.closest('.alert-card').dataset.alertId);
            await toggleAlert(alertId);
        });
    });

    list.querySelectorAll('.alert-delete').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const alertId = parseInt(e.target.closest('.alert-card').dataset.alertId);
            if (confirm('Delete this alert?')) {
                await deleteAlert(alertId);
                showToast('Alert deleted', 'success');
            }
        });
    });
}

function createAlertCardHTML(alert) {
    const info = INSTRUMENTS[alert.symbol] || { name: alert.symbol, category: 'other' };
    const currentPrice = state.prices[alert.symbol]?.price;

    const conditionIcons = {
        above: '<polyline points="18 15 12 9 6 15"/>',
        below: '<polyline points="6 9 12 15 18 9"/>',
        crosses: '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
        range: '<rect x="3" y="8" width="18" height="8" rx="2"/>',
    };

    return `
        <div class="alert-card" data-alert-id="${alert.id}">
            <div class="alert-info">
                <div class="alert-icon ${alert.condition}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        ${conditionIcons[alert.condition] || conditionIcons.above}
                    </svg>
                </div>
                <div class="alert-details">
                    <h4>${alert.symbol} <span style="color: var(--text-muted); font-weight: 400;">${info.name}</span></h4>
                    <div class="alert-condition">
                        <span>${alert.condition.toUpperCase()}</span>
                        <span class="target">$${formatPrice(alert.target_price, alert.symbol)}</span>
                        ${currentPrice ? `<span style="color: var(--text-muted);">• Current: $${formatPrice(currentPrice, alert.symbol)}</span>` : ''}
                    </div>
                </div>
            </div>
            <div class="alert-actions">
                <button class="alert-toggle ${alert.active ? 'active' : ''}" title="${alert.active ? 'Disable' : 'Enable'}"></button>
                <button class="alert-delete" title="Delete">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                </button>
            </div>
        </div>
    `;
}

// ============================================
// MODALS
// ============================================
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

function openCreateAlertModal(symbol = '') {
    if (!state.user) {
        openModal('authModal');
        showToast('Please sign in to create alerts', 'info');
        return;
    }

    const symbolSelect = document.getElementById('alertSymbol');
    if (symbol) {
        symbolSelect.value = symbol;
        updateSelectedPrice(symbol);
    }

    openModal('alertModal');
}

function updateSelectedPrice(symbol) {
    const priceEl = document.getElementById('selectedPrice');
    const priceData = state.prices[symbol];

    if (priceData) {
        priceEl.innerHTML = `Current price: <span class="value">$${formatPrice(priceData.price, symbol)}</span>`;
    } else {
        priceEl.textContent = 'Price data loading...';
    }
}

// ============================================
// TOAST NOTIFICATIONS
// ============================================
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');

    const icons = {
        success: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
        error: '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
        info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${icons[type] || icons.info}
        </svg>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============================================
// UPDATE CLOCK
// ============================================
function updateClock() {
    const timeEl = document.getElementById('marketTime');
    timeEl.textContent = formatTime(new Date());
}

// ============================================
// EVENT LISTENERS
// ============================================
function initEventListeners() {
    // Filter tabs
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            state.activeFilter = e.target.dataset.filter;
            renderPriceGrid();
        });
    });

    // Create alert button
    document.getElementById('createAlertBtn').addEventListener('click', () => openCreateAlertModal());

    // Alert modal
    document.getElementById('closeModal').addEventListener('click', () => closeModal('alertModal'));
    document.getElementById('cancelAlert').addEventListener('click', () => closeModal('alertModal'));
    document.querySelector('#alertModal .modal-backdrop').addEventListener('click', () => closeModal('alertModal'));

    // Condition buttons
    document.querySelectorAll('.condition-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.condition-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('alertCondition').value = btn.dataset.condition;
        });
    });

    // Symbol select change
    document.getElementById('alertSymbol').addEventListener('change', (e) => {
        updateSelectedPrice(e.target.value);
    });

    // Alert form submit
    document.getElementById('alertForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const symbol = document.getElementById('alertSymbol').value;
        const condition = document.getElementById('alertCondition').value;
        const targetPrice = parseFloat(document.getElementById('alertPrice').value);
        const notifyEmail = document.getElementById('notifyEmail').checked;
        const notifySMS = document.getElementById('notifySMS').checked;

        const notificationTypes = [];
        if (notifyEmail) notificationTypes.push('email');
        if (notifySMS) notificationTypes.push('sms');

        try {
            await createAlert({
                symbol,
                condition,
                target_price: targetPrice,
                notification_types: notificationTypes.join(','),
            });

            closeModal('alertModal');
            showToast('Alert created successfully!', 'success');

            // Reset form
            e.target.reset();
            document.querySelectorAll('.condition-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('.condition-btn[data-condition="above"]').classList.add('active');
            document.getElementById('alertCondition').value = 'above';
        } catch (error) {
            showToast(error.message || 'Failed to create alert', 'error');
        }
    });

    // Auth modal
    document.getElementById('closeAuthModal').addEventListener('click', () => closeModal('authModal'));
    document.querySelector('#authModal .modal-backdrop').addEventListener('click', () => closeModal('authModal'));

    let isLoginMode = true;

    document.getElementById('authSwitchBtn').addEventListener('click', () => {
        isLoginMode = !isLoginMode;

        document.getElementById('authTitle').textContent = isLoginMode ? 'Sign In' : 'Create Account';
        document.getElementById('authSubmit').textContent = isLoginMode ? 'Sign In' : 'Sign Up';
        document.getElementById('authSwitchText').textContent = isLoginMode ? "Don't have an account?" : 'Already have an account?';
        document.getElementById('authSwitchBtn').textContent = isLoginMode ? 'Sign Up' : 'Sign In';

        document.querySelectorAll('.register-only').forEach(el => {
            el.style.display = isLoginMode ? 'none' : 'block';
        });
    });

    document.getElementById('authForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('authEmail').value;
        const password = document.getElementById('authPassword').value;
        const phone = document.getElementById('authPhone').value;

        try {
            if (isLoginMode) {
                await login(email, password);
                showToast('Welcome back!', 'success');
            } else {
                await register(email, password, phone);
                await login(email, password);
                showToast('Account created successfully!', 'success');
            }

            closeModal('authModal');
            e.target.reset();
        } catch (error) {
            showToast(error.message || 'Authentication failed', 'error');
        }
    });

    // Initial login button
    document.getElementById('loginBtn')?.addEventListener('click', () => openModal('authModal'));
}

// ============================================
// INITIALIZATION
// ============================================
async function init() {
    console.log('🚀 PriceAlert Pro initializing...');

    // Check for saved token
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
        state.token = savedToken;
        await fetchUserProfile();
        await fetchAlerts();
    }

    // Initialize UI
    updateUserUI();
    initEventListeners();

    // Start clock
    updateClock();
    setInterval(updateClock, 1000);

    // Connect WebSocket
    connectWebSocket();

    // Fetch initial prices via REST (fallback)
    try {
        const response = await fetch(`${CONFIG.API_URL}/prices`);
        if (response.ok) {
            const data = await response.json();
            Object.entries(data.prices || {}).forEach(([symbol, priceData]) => {
                state.prices[symbol] = priceData;
            });
            renderPriceGrid();
        }
    } catch (error) {
        console.log('Waiting for backend to start...');
    }

    console.log('✅ PriceAlert Pro ready!');
}

// Start the app
document.addEventListener('DOMContentLoaded', init);
