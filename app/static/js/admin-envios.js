/**
 * Admin Envios Page JavaScript
 * Handles PDF viewing, status changes, and bulk actions
 */

(function () {
    'use strict';

    // ============================================================
    // Utility Functions
    // ============================================================

    function isValidPdfId(pdfId) {
        return pdfId && pdfId !== 'None' && pdfId !== 'null' && pdfId !== '';
    }

    function clearPendingPdf() {
        sessionStorage.removeItem('pendingPdfProcess');
        sessionStorage.removeItem('pendingPdfProtocol');
    }

    function getCsrfToken() {
        return window.csrfToken || null;
    }

    // ============================================================
    // View or Generate PDF
    // ============================================================

    function viewOrGeneratePdf(button) {
        const processId = button.getAttribute('data-process-id');
        const protocolNumber = button.getAttribute('data-protocol');
        const combinedPdfId = button.getAttribute('data-pdf-id');

        // If PDF already exists, open it directly
        if (isValidPdfId(combinedPdfId)) {
            window.openDocViewer(combinedPdfId, 'application/pdf', `PDF Combinado - ${protocolNumber}`, '/admin/documents');
            return;
        }

        // PDF doesn't exist, need to generate it
        sessionStorage.setItem('pendingPdfProcess', processId);
        sessionStorage.setItem('pendingPdfProtocol', protocolNumber);

        fetch(`/admin/processes/${processId}/pdf`)
            .then(response => {
                if (response.ok || response.redirected) {
                    window.location.reload();
                } else {
                    clearPendingPdf();
                    alert('Erro ao gerar PDF. Tente novamente.');
                }
            })
            .catch(() => {
                clearPendingPdf();
                alert('Erro ao gerar PDF. Tente novamente.');
            });
    }

    // ============================================================
    // Quick Status Change
    // ============================================================

    async function quickStatus(button) {
        const processId = button.getAttribute('data-process-id');
        const status = button.getAttribute('data-status');
        const patientName = button.getAttribute('data-patient-name');

        const messages = {
            'enviado': `Marcar ${patientName} como enviado?`,
            'correcao_solicitada': `Solicitar correção para ${patientName} e notificar por email?`,
            'completo': `Marcar ${patientName} como completo e notificar por email?`,
            'autorizado': `Marcar ${patientName} como autorizado e notificar por email?`,
            'negado': `Marcar ${patientName} como negado e notificar por email?`
        };

        const message = messages[status] || `Confirmar mudança de status para ${patientName}?`;

        if (!confirm(message)) return;

        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            alert('Erro: token CSRF não encontrado. Recarregue a página.');
            return;
        }

        // Set loading state
        setIconButtonLoading(button, true);

        const formData = new FormData();
        formData.append('status', status);
        formData.append('csrf_token', csrfToken);

        try {
            const response = await fetch(`/admin/processes/${processId}/quick-status`, {
                method: 'POST',
                body: formData
            });

            if (response.ok || response.redirected) {
                window.location.reload();
            } else {
                setIconButtonLoading(button, false);
                alert('Erro ao atualizar status. Tente novamente.');
            }
        } catch (error) {
            console.error('Error updating status:', error);
            setIconButtonLoading(button, false);
            alert('Erro ao atualizar status. Tente novamente.');
        }
    }

    // ============================================================
    // Icon Button Loading State
    // ============================================================

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

    // ============================================================
    // Bulk Submit Validation
    // ============================================================

    function validateAndSubmitBulk(form) {
        const checkboxes = form.querySelectorAll('.process-checkbox:checked');
        if (checkboxes.length === 0) {
            alert('Selecione pelo menos um processo para marcar como enviado.');
            return false;
        }
        return confirm('Marcar todos os selecionados como enviados e notificar pacientes por email?');
    }

    // ============================================================
    // Event Delegation
    // ============================================================

    document.addEventListener('click', function (e) {
        // View PDF button
        const viewPdfBtn = e.target.closest('[data-action="view-pdf"]');
        if (viewPdfBtn) {
            e.preventDefault();
            viewOrGeneratePdf(viewPdfBtn);
            return;
        }

        // Quick status button
        const statusBtn = e.target.closest('[data-action="quick-status"]');
        if (statusBtn) {
            e.preventDefault();
            quickStatus(statusBtn);
            return;
        }
    });

    // Form submit handler for bulk action
    const bulkForm = document.getElementById('bulk-mark-sent-form');
    if (bulkForm) {
        bulkForm.addEventListener('submit', function (e) {
            if (!validateAndSubmitBulk(this)) {
                e.preventDefault();
            }
        });
    }

    // ============================================================
    // Select All Checkbox
    // ============================================================

    const selectAllCheckbox = document.getElementById('select-all-completo');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function () {
            const checkboxes = document.querySelectorAll('.process-checkbox');
            checkboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
        });
    }

    // ============================================================
    // Auto-open Modal After Page Reload (PDF generation)
    // ============================================================

    document.addEventListener('DOMContentLoaded', function () {
        const pendingProcessId = sessionStorage.getItem('pendingPdfProcess');
        const pendingProtocol = sessionStorage.getItem('pendingPdfProtocol');

        if (pendingProcessId) {
            const button = document.querySelector(`button[data-process-id="${pendingProcessId}"]`);
            if (button) {
                const combinedPdfId = button.getAttribute('data-pdf-id');
                if (isValidPdfId(combinedPdfId)) {
                    window.openDocViewer(combinedPdfId, 'application/pdf', `PDF Combinado - ${pendingProtocol}`, '/admin/documents');
                }
            }
            clearPendingPdf();
        }
    });

})();
