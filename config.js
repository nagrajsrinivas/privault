// PriVaultHub Global Configuration
window.PRIVAUULT_CONFIG = {
    // Mode Scenarios:
    // 'scenario1': Only Mobile (Offline Mode)
    // 'scenario2': Mobile + Laptop Backup (Local Wi-Fi)
    // 'scenario3': Full Feature (Central Server OCR + Local Storage)
    PROCESSING_MODE: localStorage.getItem('privault_mode') || 'scenario3',
    
    // Central Server Endpoint URL
    API_BASE_URL: localStorage.getItem('privault_url') || 'http://127.0.0.1:8000'
};