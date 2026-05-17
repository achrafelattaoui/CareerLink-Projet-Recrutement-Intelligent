// Fichier de configuration pour l'IDE et les paramètres globaux

// Configuration du projet
const hostname = (typeof window !== 'undefined') ? window.location.hostname : 'localhost';
const PROJECT_CONFIG = {
    // Serveurs
    BACKEND_URL: `http://${hostname}:5001`,
    FRONTEND_URL: `http://${hostname}:8081`,

    // Timeouts
    API_TIMEOUT: 30000, // 30 secondes
    ALERT_DURATION: 4000, // 4 secondes

    // Pagination
    ITEMS_PER_PAGE: 10,
    MAX_RESULTS: 100,

    // Validation
    MIN_PASSWORD_LENGTH: 8,
    EMAIL_PATTERN: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    PHONE_PATTERN: /^[\d\s\-\+\(\)]{10,}$/,

    // Modes
    DEBUG: true,
    ENVIRONMENT: 'development', // 'development' ou 'production'
};

// Export pour Node.js si applicable
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PROJECT_CONFIG;
}
