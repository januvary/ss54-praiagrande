(function () {
    'use strict';

    let selectedProcessIds = new Set();
    let lastClickedRow = null;
    let lastClickedRowWasSelected = false;

    function getCsrfToken() {
        return window.csrfToken || null;
    }

    function setRowSelection(row, isSelected) {
        const checkbox = row.querySelector('[data-process-checkbox]');
        const processId = row.dataset.processId;

        if (isSelected) {
            row.classList.add('bg-blue-50');
            row.classList.remove('hover:bg-slate-50');
            if (checkbox) checkbox.checked = true;
            selectedProcessIds.add(processId);
        } else {
            row.classList.remove('bg-blue-50');
            row.classList.add('hover:bg-slate-50');
            if (checkbox) checkbox.checked = false;
            selectedProcessIds.delete(processId);
        }
    }

    function updateSelectionBar() {
        const bar = document.getElementById('selection-bar');
        const count = document.getElementById('selection-count');
        const selectAll = document.getElementById('select-all');

        if (selectedProcessIds.size > 0) {
            bar.classList.remove('hidden');
            count.textContent = selectedProcessIds.size;
        } else {
            bar.classList.add('hidden');
        }

        const allCheckboxes = document.querySelectorAll('[data-process-checkbox]');
        const allChecked = allCheckboxes.length > 0 &&
            allCheckboxes.length === selectedProcessIds.size;

        if (selectAll) {
            selectAll.checked = allChecked;
            selectAll.indeterminate = selectedProcessIds.size > 0 && !allChecked;
        }
    }

    function clearAllSelection() {
        selectedProcessIds.clear();
        document.querySelectorAll('.process-row').forEach(row => {
            const checkbox = row.querySelector('[data-process-checkbox]');
            if (checkbox) checkbox.checked = false;
            row.classList.remove('bg-blue-50');
            row.classList.add('hover:bg-slate-50');
        });
        lastClickedRow = null;
        lastClickedRowWasSelected = false;
        updateSelectionBar();
    }

    function selectRange(startRow, endRow, select) {
        const rows = Array.from(document.querySelectorAll('.process-row'));
        const startIndex = rows.indexOf(startRow);
        const endIndex = rows.indexOf(endRow);

        if (startIndex === -1 || endIndex === -1) return;

        const [min, max] = [Math.min(startIndex, endIndex), Math.max(startIndex, endIndex)];

        for (let i = min; i <= max; i++) {
            const processId = rows[i].dataset.processId;
            const isSelected = selectedProcessIds.has(processId);
            if (isSelected !== select) {
                setRowSelection(rows[i], select);
            }
        }
        updateSelectionBar();
    }

    function showContextMenu(x, y) {
        const menu = document.getElementById('context-menu');
        if (!menu) return;

        menu.classList.remove('hidden');

        const menuRect = menu.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        let posX = x;
        let posY = y;

        if (x + menuRect.width > viewportWidth - 10) {
            posX = viewportWidth - menuRect.width - 10;
        }
        if (y + menuRect.height > viewportHeight - 10) {
            posY = viewportHeight - menuRect.height - 10;
        }

        menu.style.left = posX + 'px';
        menu.style.top = posY + 'px';
    }

    function hideContextMenu() {
        const menu = document.getElementById('context-menu');
        if (menu) {
            menu.classList.add('hidden');
        }
    }

    function showLoading() {
        selectedProcessIds.forEach(processId => {
            const row = document.querySelector(`.process-row[data-process-id="${processId}"]`);
            if (!row) return;

            const cell = row.querySelector('td:first-child');
            if (!cell) return;

            const checkbox = cell.querySelector('input[data-process-checkbox]');
            if (!checkbox) return;

            cell.dataset.originalCheckbox = cell.innerHTML;

            const spinner = document.createElement('div');
            spinner.className = 'flex items-center justify-center w-full h-full';
            spinner.innerHTML = '<div class="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>';
            cell.innerHTML = '';
            cell.appendChild(spinner);
        });
    }

    function hideLoading() {
        selectedProcessIds.forEach(processId => {
            const row = document.querySelector(`.process-row[data-process-id="${processId}"]`);
            if (!row) return;

            const cell = row.querySelector('td:first-child');
            if (!cell) return;

            if (cell.dataset.originalCheckbox) {
                cell.innerHTML = cell.dataset.originalCheckbox;
                delete cell.dataset.originalCheckbox;
            }
        });
    }

    async function changeStatus(newStatus) {
        const processIds = Array.from(selectedProcessIds);
        const count = processIds.length;

        if (count === 0) return;

        const statusBtn = document.querySelector(`[data-context-action="change-status"][data-status="${newStatus}"]`);
        const statusLabel = statusBtn ? statusBtn.querySelector('span:last-child').textContent.trim() : newStatus;

        const emailStatuses = ['incompleto', 'correcao_solicitada', 'autorizado', 'negado', 'completo', 'em_revisao', 'expirado'];
        const sendsEmail = emailStatuses.includes(newStatus);

        let message;
        if (count === 1) {
            message = sendsEmail
                ? `Alterar status para "${statusLabel}" e notificar o paciente por email?`
                : `Alterar status para "${statusLabel}"?`;
        } else {
            message = sendsEmail
                ? `Alterar status de ${count} processos para "${statusLabel}" e notificar pacientes por email?`
                : `Alterar status de ${count} processos para "${statusLabel}"?`;
        }

        if (!confirm(message)) return;

        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            alert('Erro: token CSRF não encontrado. Recarregue a página.');
            return;
        }

        const formData = new FormData();
        processIds.forEach(id => formData.append('process_ids', id));
        formData.append('status', newStatus);
        formData.append('csrf_token', csrfToken);

        hideContextMenu();
        showLoading();
        clearAllSelection();

        try {
            const response = await fetch('/admin/processes/bulk-status', {
                method: 'POST',
                body: formData
            });

            if (response.ok || response.redirected) {
                window.location.reload();
            } else {
                const text = await response.text();
                console.error('Status change failed:', text);
                alert('Erro ao atualizar status. Tente novamente.');
                hideLoading();
            }
        } catch (error) {
            console.error('Error changing status:', error);
            alert('Erro ao atualizar status. Tente novamente.');
            hideLoading();
        }
    }

    document.addEventListener('click', function (e) {
        hideContextMenu();

        const statusBtn = e.target.closest('[data-context-action="change-status"]');
        if (statusBtn) {
            e.preventDefault();
            e.stopPropagation();
            const newStatus = statusBtn.dataset.status;
            changeStatus(newStatus);
            return;
        }

        const row = e.target.closest('.process-row');
        if (row && !e.target.closest('a') && !e.target.closest('input[type="checkbox"]')) {
            e.preventDefault();
            const processId = row.dataset.processId;
            const isSelected = selectedProcessIds.has(processId);

            if (e.shiftKey && lastClickedRow) {
                selectRange(lastClickedRow, row, lastClickedRowWasSelected);
            } else {
                setRowSelection(row, !isSelected);
                updateSelectionBar();
                lastClickedRow = row;
                lastClickedRowWasSelected = !isSelected;
            }
            return;
        }

        const checkbox = e.target.closest('[data-process-checkbox]');
        if (checkbox) {
            const row = checkbox.closest('.process-row');
            const processId = row.dataset.processId;
            const wasSelected = selectedProcessIds.has(processId);
            setRowSelection(row, checkbox.checked);
            updateSelectionBar();
            lastClickedRow = row;
            lastClickedRowWasSelected = checkbox.checked;
            return;
        }

        const selectAll = e.target.closest('#select-all');
        if (selectAll) {
            const allRows = document.querySelectorAll('.process-row');
            const shouldSelect = selectedProcessIds.size < allRows.length;
            allRows.forEach(row => {
                setRowSelection(row, shouldSelect);
            });
            updateSelectionBar();
            lastClickedRow = null;
            lastClickedRowWasSelected = false;
            return;
        }

        const clearBtn = e.target.closest('#clear-selection');
        if (clearBtn) {
            clearAllSelection();
            return;
        }
    });

    document.addEventListener('contextmenu', function (e) {
        const row = e.target.closest('.process-row');

        if (row) {
            e.preventDefault();

            const processId = row.dataset.processId;
            if (!selectedProcessIds.has(processId)) {
                clearAllSelection();
                setRowSelection(row, true);
                updateSelectionBar();
                lastClickedRow = row;
                lastClickedRowWasSelected = true;
            }

            showContextMenu(e.clientX, e.clientY);
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            hideContextMenu();
        }
    });

    document.addEventListener('scroll', function () {
        hideContextMenu();
    });

})();
