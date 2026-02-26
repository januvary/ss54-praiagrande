/**
 * Date Input Handler
 * Auto-formats and validates DD/MM/YYYY date inputs
 *
 * Usage:
 *   import { setupDateInput } from '/static/js/date-input.js';
 *   setupDateInput('date_of_birth');
 *   setupDateInput('birth_date', { maxDate: '2020-12-31' });
 */

/**
 * Setup auto-formatting and validation for a date input field
 * @param {string} inputId - The ID of the input element
 * @param {Object} options - Configuration options
 * @param {string} options.maxDate - Maximum allowed date ('today' or specific date)
 */
export function setupDateInput(inputId, options = {}) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const { maxDate = 'today' } = options;

    // Auto-format as user types
    input.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, ''); // Remove non-digits
        
        // Limit to 8 digits (DDMMYYYY)
        if (value.length > 8) value = value.slice(0, 8);
        
        // Auto-format with slashes
        if (value.length > 4) {
            e.target.value = `${value.slice(0,2)}/${value.slice(2,4)}/${value.slice(4)}`;
        } else if (value.length > 2) {
            e.target.value = `${value.slice(0,2)}/${value.slice(2)}`;
        } else {
            e.target.value = value;
        }
    });

    // Validate on blur (when leaving the field)
    input.addEventListener('blur', function(e) {
        const value = e.target.value.trim();
        const dateRegex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
        
        // Clear previous validation state
        input.classList.remove('border-red-500');
        
        if (!value) {
            // Empty field - clear validation
            input.setCustomValidity('');
            return;
        }
        
        if (!dateRegex.test(value)) {
            // Invalid format
            input.classList.add('border-red-500');
            input.setCustomValidity('Data deve estar no formato DD/MM/AAAA');
            return;
        }
        
        // Parse and validate date
        const [dayStr, monthStr, yearStr] = value.split('/');
        const day = parseInt(dayStr, 10);
        const month = parseInt(monthStr, 10);
        const year = parseInt(yearStr, 10);
        
        // Check if date is valid
        const date = new Date(year, month - 1, day);
        const isValidDate = (
            date.getDate() === day &&
            date.getMonth() === month - 1 &&
            date.getFullYear() === year
        );
        
        if (!isValidDate) {
            input.classList.add('border-red-500');
            input.setCustomValidity('Data inválida');
            return;
        }
        
        // Check if date is in the future
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        if (date > today) {
            input.classList.add('border-red-500');
            input.setCustomValidity('Data não pode estar no futuro');
            return;
        }
        
        // Check reasonable year range (1900-current year)
        if (year < 1900 || year > today.getFullYear()) {
            input.classList.add('border-red-500');
            input.setCustomValidity('Ano deve estar entre 1900 e ' + today.getFullYear());
            return;
        }
        
        // Valid date
        input.setCustomValidity('');
    });

    // Clear error when user starts typing again
    input.addEventListener('input', function(e) {
        if (input.classList.contains('border-red-500')) {
            input.classList.remove('border-red-500');
            input.setCustomValidity('');
        }
    });
}
