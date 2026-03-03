/**
 * Admin Panel JavaScript
 * Uses event delegation for CSP-compliant handlers
 */

(function() {
    'use strict';

    // ============================================================
    // Toggle Note Form (document validation)
    // ============================================================
    document.addEventListener('click', function(e) {
        const toggleBtn = e.target.closest('[data-action="toggle-note-form"]');
        if (!toggleBtn) return;

        const docId = toggleBtn.getAttribute('data-doc-id');
        const buttonsDiv = document.getElementById(`note-buttons-${docId}`);
        const formContainer = document.getElementById(`note-form-${docId}`);
        const textarea = document.getElementById(`note-textarea-${docId}`);

        if (buttonsDiv) {
            // Check if hidden (either via CSS class or inline style)
            const isHidden = buttonsDiv.classList.contains('hidden') || buttonsDiv.style.display === 'none';

            // Toggle: show if hidden, hide if visible
            if (isHidden) {
                buttonsDiv.classList.remove('hidden');
                buttonsDiv.style.display = 'flex';
                if (textarea) {
                    textarea.readOnly = false;
                    textarea.focus();
                }
            } else {
                buttonsDiv.classList.add('hidden');
                buttonsDiv.style.display = 'none';
                if (textarea) {
                    textarea.readOnly = true;
                }
            }
        } else if (formContainer) {
            // Case: No notes - toggle entire form visibility
            formContainer.classList.toggle('hidden');

            if (!formContainer.classList.contains('hidden')) {
                const textarea = formContainer.querySelector('textarea');
                if (textarea) textarea.focus();
            }
        }
    });

    // ============================================================
    // Row Click Navigation
    // ============================================================
    document.addEventListener('click', function(e) {
        const clickableRow = e.target.closest('[data-action="navigate"]');
        if (!clickableRow) return;

        // Don't navigate if clicking on a button, link, or input
        if (e.target.closest('button, a, input, select, textarea')) return;

        const url = clickableRow.getAttribute('data-url');
        if (url) {
            window.location.href = url;
        }
    });

    // ============================================================
    // Activity Log Details Toggle
    // ============================================================
    document.addEventListener('click', function(e) {
        const toggleBtn = e.target.closest('[data-action="toggle-details"]');
        if (!toggleBtn) return;

        const targetId = toggleBtn.getAttribute('data-target');
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
            targetEl.classList.toggle('hidden');
        }
    });

    // ============================================================
    // Stop Propagation for Nested Clickable Elements
    // ============================================================
    document.addEventListener('click', function(e) {
        const stopProp = e.target.closest('[data-action="stop-propagation"]');
        if (stopProp) {
            e.stopPropagation();
        }
    });

    // ============================================================
    // Auto-Submit Forms on Select Change
    // ============================================================
    document.addEventListener('change', function(e) {
        const autoSubmit = e.target.closest('[data-auto-submit]');
        if (!autoSubmit) return;

        const form = autoSubmit.closest('form');
        if (form) {
            form.submit();
        }
    });

    // ============================================================
    // Auto-Save Description Field
    // ============================================================
    function autoSaveDescription(form) {
        const input = form.querySelector('input[name="details"]');
        if (!input || input.value === input.dataset.lastSavedValue) return;

        const formData = new FormData(form);
        const csrfToken = formData.get('csrf_token');

        fetch(form.action, {
            method: 'POST',
            headers: {
                'X-CSRF-Token': csrfToken
            },
            body: formData
        }).then(response => {
            if (response.ok) {
                input.dataset.lastSavedValue = input.value;
                input.classList.add('border-green-500');
                setTimeout(() => input.classList.remove('border-green-500'), 1000);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function() {
        const autoSaveForms = document.querySelectorAll('form[data-auto-save]');
        autoSaveForms.forEach(form => {
            const input = form.querySelector('input[name="details"]');
            if (!input) return;

            input.dataset.lastSavedValue = input.value;

            input.addEventListener('blur', () => {
                autoSaveDescription(form);
            });

            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    input.blur();
                }
            });
        });
    });

})();
