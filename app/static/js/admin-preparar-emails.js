/**
 * Admin Preparar Emails Page JavaScript
 * Handles PDF viewing and form submission for DRS emails
 */

(function() {
    'use strict';

    function viewPdf(button) {
        const pdfId = button.getAttribute('data-pdf-id');
        const protocol = button.getAttribute('data-protocol');

        if (pdfId) {
            window.openDocViewer(pdfId, 'application/pdf', `PDF - ${protocol}`, '/admin/documents');
        }
    }

    function handleFormSubmit(form) {
        const button = form.querySelector('button[type="submit"]');
        if (!button) return true;

        const loadingText = button.getAttribute('data-loading-text') || 'Enviando...';
        const originalText = button.innerHTML;

        button.disabled = true;
        button.innerHTML = `
            <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
            ${loadingText}
        `;

        return true;
    }

    document.addEventListener('click', function(e) {
        const viewPdfBtn = e.target.closest('[data-action="view-pdf"]');
        if (viewPdfBtn) {
            e.preventDefault();
            viewPdf(viewPdfBtn);
            return;
        }
    });

    function autoSaveDescription(input) {
        const processId = input.getAttribute('data-process-id');
        const csrfToken = document.querySelector('input[name="csrf_token"]').value;
        const description = input.value;

        if (description === input.dataset.lastSavedValue) return;

        fetch(`/admin/processes/${processId}/details`, {
            method: 'POST',
            headers: {
                'X-CSRF-Token': csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `csrf_token=${encodeURIComponent(csrfToken)}&details=${encodeURIComponent(description)}`
        }).then(response => {
            if (response.ok) {
                input.dataset.lastSavedValue = description;
                input.classList.add('border-green-500');
                setTimeout(() => input.classList.remove('border-green-500'), 1000);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function() {
        const autoSaveInputs = document.querySelectorAll('input[data-auto-save]');
        autoSaveInputs.forEach(input => {
            input.dataset.lastSavedValue = input.value;

            input.addEventListener('blur', () => {
                autoSaveDescription(input);
            });

            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    e.stopPropagation();
                    autoSaveDescription(input);
                    input.blur();
                }
            });
        });

        const forms = document.querySelectorAll('form[id^="form-"]');
        forms.forEach(form => {
            form.addEventListener('submit', function() {
                handleFormSubmit(this);
            });
        });
    });

})();
