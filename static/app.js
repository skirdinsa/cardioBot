/**
 * CardioBot Mini App JavaScript
 */

// Telegram WebApp instance
const tg = window.Telegram.WebApp;

// DOM elements
const elements = {
    loading: document.getElementById('loading'),
    content: document.getElementById('content'),
    error: document.getElementById('error'),
    errorMessage: document.getElementById('error-message'),
    retryBtn: document.getElementById('retry-btn'),
    resetBtn: document.getElementById('reset-btn'),

    // Notifications
    morningEnabled: document.getElementById('morning-enabled'),
    morningTime: document.getElementById('morning-time'),
    morningTimeRow: document.getElementById('morning-time-row'),
    eveningEnabled: document.getElementById('evening-enabled'),
    eveningTime: document.getElementById('evening-time'),
    eveningTimeRow: document.getElementById('evening-time-row'),

    // Thresholds
    goodUpper: document.getElementById('good-upper'),
    goodLower: document.getElementById('good-lower'),
    warningUpper: document.getElementById('warning-upper'),
    warningLower: document.getElementById('warning-lower'),

    // Timezone
    timezone: document.getElementById('timezone'),
};

// Current settings state
let currentSettings = null;
let hasChanges = false;

/**
 * Initialize the Mini App
 */
function init() {
    // Tell Telegram we're ready
    tg.ready();

    // Expand to full height
    tg.expand();

    // Set up MainButton
    tg.MainButton.setText('Save');
    tg.MainButton.onClick(saveSettings);

    // Set up back button
    tg.BackButton.show();
    tg.BackButton.onClick(() => tg.close());

    // Apply theme
    applyTheme();

    // Set up event listeners
    setupEventListeners();

    // Load settings
    loadSettings();
}

/**
 * Apply Telegram theme colors
 */
function applyTheme() {
    const root = document.documentElement;

    root.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#ffffff');
    root.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#000000');
    root.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#999999');
    root.style.setProperty('--tg-theme-link-color', tg.themeParams.link_color || '#2481cc');
    root.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#2481cc');
    root.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');
    root.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color || '#f0f0f0');
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Toggle visibility of time inputs based on enabled state
    elements.morningEnabled.addEventListener('change', () => {
        updateTimeRowVisibility();
        markChanged();
    });

    elements.eveningEnabled.addEventListener('change', () => {
        updateTimeRowVisibility();
        markChanged();
    });

    // Mark as changed on any input change
    const inputs = [
        elements.morningTime,
        elements.eveningTime,
        elements.goodUpper,
        elements.goodLower,
        elements.warningUpper,
        elements.warningLower,
        elements.timezone,
    ];

    inputs.forEach(input => {
        input.addEventListener('change', markChanged);
        input.addEventListener('input', markChanged);
    });

    // Retry button
    elements.retryBtn.addEventListener('click', loadSettings);

    // Reset button
    elements.resetBtn.addEventListener('click', resetToDefaults);
}

/**
 * Update time row visibility based on enabled state
 */
function updateTimeRowVisibility() {
    elements.morningTimeRow.classList.toggle('disabled', !elements.morningEnabled.checked);
    elements.eveningTimeRow.classList.toggle('disabled', !elements.eveningEnabled.checked);
}

/**
 * Mark that settings have been changed
 */
function markChanged() {
    if (!hasChanges) {
        hasChanges = true;
        tg.MainButton.show();
    }
}

/**
 * Load settings from server
 */
async function loadSettings() {
    showLoading();

    try {
        const response = await fetch('/api/settings', {
            method: 'GET',
            headers: {
                'X-Telegram-Init-Data': tg.initData,
            },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Unknown error');
        }

        currentSettings = data.settings;
        applySettingsToForm(currentSettings);
        showContent();
        hasChanges = false;
        tg.MainButton.hide();

    } catch (error) {
        console.error('Error loading settings:', error);
        showError(`Failed to load settings: ${error.message}`);
    }
}

/**
 * Apply settings to form elements
 */
function applySettingsToForm(settings) {
    // Notifications
    elements.morningEnabled.checked = settings.notifications.morning_enabled;
    elements.eveningEnabled.checked = settings.notifications.evening_enabled;
    elements.morningTime.value = settings.notifications.morning_time;
    elements.eveningTime.value = settings.notifications.evening_time;

    // Thresholds
    elements.goodUpper.value = settings.thresholds.good_upper;
    elements.goodLower.value = settings.thresholds.good_lower;
    elements.warningUpper.value = settings.thresholds.warning_upper;
    elements.warningLower.value = settings.thresholds.warning_lower;

    // Timezone
    elements.timezone.value = settings.timezone;

    // Update visibility
    updateTimeRowVisibility();
}

/**
 * Get settings from form
 */
function getSettingsFromForm() {
    return {
        notifications: {
            morning_enabled: elements.morningEnabled.checked,
            evening_enabled: elements.eveningEnabled.checked,
            morning_time: elements.morningTime.value,
            evening_time: elements.eveningTime.value,
        },
        thresholds: {
            good_upper: parseInt(elements.goodUpper.value, 10),
            good_lower: parseInt(elements.goodLower.value, 10),
            warning_upper: parseInt(elements.warningUpper.value, 10),
            warning_lower: parseInt(elements.warningLower.value, 10),
        },
        timezone: elements.timezone.value,
    };
}

/**
 * Validate settings
 */
function validateSettings(settings) {
    const errors = [];

    // Validate time format
    const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;

    if (!timeRegex.test(settings.notifications.morning_time)) {
        errors.push('Invalid morning time format');
    }

    if (!timeRegex.test(settings.notifications.evening_time)) {
        errors.push('Invalid evening time format');
    }

    // Validate thresholds
    const { good_upper, good_lower, warning_upper, warning_lower } = settings.thresholds;

    if (good_upper < 80 || good_upper > 200) {
        errors.push('Normal systolic must be between 80-200');
    }

    if (good_lower < 40 || good_lower > 120) {
        errors.push('Normal diastolic must be between 40-120');
    }

    if (warning_upper < 80 || warning_upper > 220) {
        errors.push('Elevated systolic must be between 80-220');
    }

    if (warning_lower < 40 || warning_lower > 140) {
        errors.push('Elevated diastolic must be between 40-140');
    }

    if (warning_upper <= good_upper) {
        errors.push('Elevated systolic must be greater than normal');
    }

    if (warning_lower <= good_lower) {
        errors.push('Elevated diastolic must be greater than normal');
    }

    return errors;
}

/**
 * Save settings to server
 */
async function saveSettings() {
    const settings = getSettingsFromForm();

    // Validate
    const errors = validateSettings(settings);
    if (errors.length > 0) {
        tg.showAlert(errors.join('\n'));
        return;
    }

    // Show loading state on button
    tg.MainButton.showProgress();

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-Init-Data': tg.initData,
            },
            body: JSON.stringify(settings),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Unknown error');
        }

        // Success
        currentSettings = data.settings;
        hasChanges = false;
        tg.MainButton.hideProgress();
        tg.MainButton.hide();

        // Show success feedback
        tg.HapticFeedback.notificationOccurred('success');

        // Close the app after a short delay
        setTimeout(() => {
            tg.close();
        }, 500);

    } catch (error) {
        console.error('Error saving settings:', error);
        tg.MainButton.hideProgress();
        tg.showAlert(`Failed to save: ${error.message}`);
    }
}

/**
 * Reset to default settings
 */
async function resetToDefaults() {
    tg.showConfirm('Reset all settings to defaults?', async (confirmed) => {
        if (!confirmed) return;

        try {
            const response = await fetch('/api/defaults', {
                method: 'GET',
                headers: {
                    'X-Telegram-Init-Data': tg.initData,
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Unknown error');
            }

            applySettingsToForm(data.defaults);
            markChanged();

            tg.HapticFeedback.notificationOccurred('warning');

        } catch (error) {
            console.error('Error loading defaults:', error);
            tg.showAlert(`Failed to load defaults: ${error.message}`);
        }
    });
}

/**
 * Show loading state
 */
function showLoading() {
    elements.loading.classList.remove('hidden');
    elements.content.classList.add('hidden');
    elements.error.classList.add('hidden');
}

/**
 * Show content
 */
function showContent() {
    elements.loading.classList.add('hidden');
    elements.content.classList.remove('hidden');
    elements.error.classList.add('hidden');
}

/**
 * Show error state
 */
function showError(message) {
    elements.loading.classList.add('hidden');
    elements.content.classList.add('hidden');
    elements.error.classList.remove('hidden');
    elements.errorMessage.textContent = message;
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', init);
