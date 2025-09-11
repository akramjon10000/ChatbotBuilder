/**
 * AI Chatbot Platform - Main JavaScript
 */

// Global variables
let currentLanguage = 'uz';
let isTyping = false;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Set current language
    currentLanguage = document.documentElement.lang || 'uz';
    
    // Initialize components
    initializeTooltips();
    initializeModals();
    initializeCharts();
    initializeChatInterface();
    initializeFormValidation();
    initializeNotifications();
    
    // Auto-refresh trial status
    startTrialStatusMonitoring();
    
    console.log('AI Chatbot Platform initialized');
    
    // Remove Replit development tools if they exist
    removeReplotDevTools();
}

/**
 * Remove Replit development tools from DOM
 */
function removeReplotDevTools() {
    function cleanDevTools() {
        // Remove Eruda and other dev tool elements
        const devSelectors = [
            '#eruda', '#eruda-container', 
            '[id*="eruda"]', '[class*="eruda"]',
            '[id*="__replco"]', '[class*="__replco"]',
            'script[src*="eruda"]', 'script[src*="devtools"]'
        ];
        
        devSelectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                if (el && el.parentNode) {
                    el.parentNode.removeChild(el);
                }
            });
        });
        
        // Remove any style elements that might be injected
        const styles = document.querySelectorAll('style');
        styles.forEach(style => {
            if (style.textContent && style.textContent.includes('eruda')) {
                style.remove();
            }
        });
    }
    
    // Clean immediately
    cleanDevTools();
    
    // Monitor for dynamic injection
    const observer = new MutationObserver(() => {
        cleanDevTools();
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Also clean periodically as backup
    setInterval(cleanDevTools, 2000);
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize modals
 */
function initializeModals() {
    // Auto-focus on modal inputs
    document.addEventListener('shown.bs.modal', function (event) {
        const modal = event.target;
        const firstInput = modal.querySelector('input, textarea, select');
        if (firstInput) {
            firstInput.focus();
        }
    });
}

/**
 * Initialize charts if Chart.js is available
 */
function initializeCharts() {
    if (typeof Chart !== 'undefined') {
        // Set default chart options
        Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;
    }
}

/**
 * Initialize chat interface
 */
function initializeChatInterface() {
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    
    if (chatForm && messageInput) {
        // Auto-resize textarea
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
        
        // Handle Enter key
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
        
        // Quick message buttons
        document.querySelectorAll('.quick-message').forEach(button => {
            button.addEventListener('click', function() {
                messageInput.value = this.dataset.message;
                messageInput.focus();
                messageInput.dispatchEvent(new Event('input'));
            });
        });
    }
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    // Custom validation messages
    const validationMessages = {
        uz: {
            required: 'Bu maydon to\'ldirilishi shart',
            email: 'To\'g\'ri email manzil kiriting',
            minlength: 'Juda qisqa',
            maxlength: 'Juda uzun'
        },
        ru: {
            required: 'Это поле обязательно для заполнения',
            email: 'Введите правильный email адрес',
            minlength: 'Слишком короткий',
            maxlength: 'Слишком длинный'
        },
        en: {
            required: 'This field is required',
            email: 'Please enter a valid email address',
            minlength: 'Too short',
            maxlength: 'Too long'
        }
    };
    
    // Add validation to forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
                showValidationErrors(form);
            }
            form.classList.add('was-validated');
        });
    });
    
    function showValidationErrors(form) {
        const invalidFields = form.querySelectorAll(':invalid');
        if (invalidFields.length > 0) {
            invalidFields[0].focus();
            showNotification(
                validationMessages[currentLanguage]?.required || 'Please fill in all required fields',
                'error'
            );
        }
    }
}

/**
 * Initialize notifications system
 */
function initializeNotifications() {
    // Create notification container if it doesn't exist
    if (!document.getElementById('notification-container')) {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 350px;
        `;
        document.body.appendChild(container);
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('notification-container');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.style.cssText = 'margin-bottom: 10px;';
    
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-triangle',
        warning: 'fas fa-exclamation-circle',
        info: 'fas fa-info-circle'
    };
    
    notification.innerHTML = `
        <i class="${icons[type] || icons.info} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(notification);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }
}

/**
 * Start monitoring trial status
 */
function startTrialStatusMonitoring() {
    // Check every 5 minutes
    setInterval(checkTrialStatus, 300000);
}

/**
 * Check trial status
 */
function checkTrialStatus() {
    // This would make an AJAX call to check trial status
    // For now, we'll just check if the user is on trial
    const trialBadge = document.querySelector('.navbar .badge');
    if (trialBadge && trialBadge.textContent.includes('kun')) {
        const daysLeft = parseInt(trialBadge.textContent);
        if (daysLeft <= 1) {
            showNotification(
                getLocalizedMessage('trial_expiring_soon'),
                'warning',
                0
            );
        }
    }
}

/**
 * Get localized message
 */
function getLocalizedMessage(key) {
    const messages = {
        uz: {
            trial_expiring_soon: 'Sinov muddatingiz tugaydi! Admin ruxsatini so\'rang.',
            loading: 'Yuklanmoqda...',
            error: 'Xatolik yuz berdi',
            success: 'Muvaffaqiyatli'
        },
        ru: {
            trial_expiring_soon: 'Ваш пробный период заканчивается! Запросите разрешение администратора.',
            loading: 'Загрузка...',
            error: 'Произошла ошибка',
            success: 'Успешно'
        },
        en: {
            trial_expiring_soon: 'Your trial period is expiring! Request admin approval.',
            loading: 'Loading...',
            error: 'An error occurred',
            success: 'Success'
        }
    };
    
    return messages[currentLanguage]?.[key] || messages.en[key] || key;
}

/**
 * Show loading state
 */
function showLoading(element) {
    if (element) {
        element.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status"></span>
            ${getLocalizedMessage('loading')}
        `;
        element.disabled = true;
    }
}

/**
 * Hide loading state
 */
function hideLoading(element, originalText) {
    if (element) {
        element.innerHTML = originalText;
        element.disabled = false;
    }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification(getLocalizedMessage('copied'), 'success', 2000);
    }).catch(() => {
        showNotification(getLocalizedMessage('copy_failed'), 'error', 3000);
    });
}

/**
 * Format date for display
 */
function formatDate(dateString, locale = currentLanguage) {
    const date = new Date(dateString);
    const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    
    const localeMap = {
        uz: 'uz-UZ',
        ru: 'ru-RU',
        en: 'en-US'
    };
    
    return date.toLocaleDateString(localeMap[locale] || 'en-US', options);
}

/**
 * Validate email
 */
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Validate phone number
 */
function validatePhone(phone) {
    const re = /^[\+]?[1-9][\d]{6,14}$/;
    return re.test(phone.replace(/\D/g, ''));
}

/**
 * Auto-save form data
 */
function autoSaveForm(formId, interval = 30000) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    setInterval(() => {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        localStorage.setItem(`autosave_${formId}`, JSON.stringify(data));
    }, interval);
}

/**
 * Restore form data
 */
function restoreFormData(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const savedData = localStorage.getItem(`autosave_${formId}`);
    if (savedData) {
        const data = JSON.parse(savedData);
        Object.keys(data).forEach(key => {
            const field = form.querySelector(`[name="${key}"]`);
            if (field) {
                field.value = data[key];
            }
        });
    }
}

/**
 * Debounce function
 */
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

/**
 * Throttle function
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Check if element is in viewport
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Smooth scroll to element
 */
function scrollToElement(element, offset = 0) {
    const targetPosition = element.offsetTop - offset;
    window.scrollTo({
        top: targetPosition,
        behavior: 'smooth'
    });
}

/**
 * Add loading overlay
 */
function addLoadingOverlay(container) {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.style.cssText = `
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255, 255, 255, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;
    overlay.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status"></div>
            <div class="mt-2">${getLocalizedMessage('loading')}</div>
        </div>
    `;
    
    container.style.position = 'relative';
    container.appendChild(overlay);
    
    return overlay;
}

/**
 * Remove loading overlay
 */
function removeLoadingOverlay(container) {
    const overlay = container.querySelector('.loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

/**
 * Initialize dark mode toggle
 */
function initializeDarkMode() {
    const toggleButton = document.getElementById('darkModeToggle');
    if (!toggleButton) return;
    
    // Check saved preference
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    if (isDarkMode) {
        document.body.classList.add('dark-mode');
    }
    
    toggleButton.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
        const newDarkMode = document.body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', newDarkMode);
    });
}

/**
 * Handle keyboard shortcuts
 */
function handleKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Enter to submit forms
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const activeForm = document.activeElement.closest('form');
            if (activeForm) {
                activeForm.dispatchEvent(new Event('submit'));
            }
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                bootstrap.Modal.getInstance(openModal).hide();
            }
        }
    });
}

/**
 * Initialize search functionality
 */
function initializeSearch() {
    const searchInputs = document.querySelectorAll('[data-search]');
    searchInputs.forEach(input => {
        const targetSelector = input.dataset.search;
        const targets = document.querySelectorAll(targetSelector);
        
        const debouncedSearch = debounce((query) => {
            targets.forEach(target => {
                const text = target.textContent.toLowerCase();
                const matches = text.includes(query.toLowerCase());
                target.style.display = matches ? '' : 'none';
            });
        }, 300);
        
        input.addEventListener('input', (e) => {
            debouncedSearch(e.target.value);
        });
    });
}

// Initialize additional features
document.addEventListener('DOMContentLoaded', function() {
    initializeDarkMode();
    handleKeyboardShortcuts();
    initializeSearch();
});

// Export functions for global use
window.ChatbotPlatform = {
    showNotification,
    showLoading,
    hideLoading,
    copyToClipboard,
    validateEmail,
    validatePhone,
    formatDate,
    addLoadingOverlay,
    removeLoadingOverlay,
    getLocalizedMessage
};
