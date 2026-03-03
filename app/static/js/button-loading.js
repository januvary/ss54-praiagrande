/**
 * Button Loading State Utility
 * Handles loading states for form submit buttons
 */

(function() {
    'use strict';

    /**
     * Set button loading state
     * @param {HTMLButtonElement} button - The button element
     * @param {boolean} loading - Whether to show loading state
     */
    function setButtonLoading(button, loading) {
        const textEl = button.querySelector('[data-button-text]');
        const spinnerEl = button.querySelector('[data-button-spinner]');
        
        if (loading) {
            button.disabled = true;
            button.dataset.originalDisabled = 'true';
            if (textEl) textEl.classList.add('hidden');
            if (spinnerEl) spinnerEl.classList.remove('hidden');
        } else {
            button.disabled = false;
            delete button.dataset.originalDisabled;
            if (textEl) textEl.classList.remove('hidden');
            if (spinnerEl) spinnerEl.classList.add('hidden');
        }
    }

    /**
     * Set icon button loading state (replaces icon with spinner)
     * @param {HTMLElement} button - The button element  
     * @param {boolean} loading - Whether to show loading state
     */
    function setIconButtonLoading(button, loading) {
        const iconEl = button.querySelector('svg');
        
        if (loading) {
            button.disabled = true;
            button.dataset.isLoading = 'true';
            if (iconEl) {
                iconEl.dataset.originalDisplay = iconEl.style.display || '';
                iconEl.style.display = 'none';
            }
            const spinner = document.createElement('div');
            spinner.className = 'animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full';
            spinner.dataset.spinner = 'true';
            button.insertBefore(spinner, iconEl);
        } else {
            button.disabled = false;
            delete button.dataset.isLoading;
            const spinner = button.querySelector('[data-spinner="true"]');
            if (spinner) spinner.remove();
            if (iconEl) {
                iconEl.style.display = iconEl.dataset.originalDisplay || '';
                delete iconEl.dataset.originalDisplay;
            }
        }
    }

    /**
     * Set link loading state (for anchor tags that trigger actions)
     * @param {HTMLAnchorElement} link - The link element
     * @param {boolean} loading - Whether to show loading state
     */
    function setLinkLoading(link, loading) {
        const textEl = link.querySelector('[data-link-text]');
        const spinnerEl = link.querySelector('[data-link-spinner]');
        
        if (loading) {
            link.style.pointerEvents = 'none';
            link.dataset.isLoading = 'true';
            if (textEl) textEl.classList.add('hidden');
            if (spinnerEl) spinnerEl.classList.remove('hidden');
        } else {
            link.style.pointerEvents = '';
            delete link.dataset.isLoading;
            if (textEl) textEl.classList.remove('hidden');
            if (spinnerEl) spinnerEl.classList.add('hidden');
        }
    }

    // Initialize form submit handlers
    function initFormLoading() {
        document.querySelectorAll('form[data-loading]').forEach(form => {
            form.addEventListener('submit', function() {
                const btn = this.querySelector('button[type="submit"]');
                if (btn) setButtonLoading(btn, true);
            });
        });
    }

    // Initialize action link handlers
    function initActionLinks() {
        document.querySelectorAll('a[data-action-link]').forEach(link => {
            link.addEventListener('click', function(e) {
                // Only handle if not already loading
                if (this.dataset.isLoading) return;
                
                setLinkLoading(this, true);
                
                // For download links, the page will navigate and reload
                // so we don't need to unset loading manually
            });
        });
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initFormLoading();
            initActionLinks();
        });
    } else {
        initFormLoading();
        initActionLinks();
    }

    // Export to global scope
    window.ButtonLoading = {
        setButtonLoading,
        setIconButtonLoading,
        setLinkLoading
    };

})();
