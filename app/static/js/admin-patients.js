(function () {
    'use strict';

    let selectedPatientId = null;

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

    document.addEventListener('contextmenu', function (e) {
        const row = e.target.closest('.patient-row');

        if (row) {
            e.preventDefault();
            e.stopPropagation();

            selectedPatientId = row.dataset.patientId;
            showContextMenu(e.clientX, e.clientY);
        }
    });

    document.addEventListener('click', function (e) {
        hideContextMenu();

        const changeEmailBtn = e.target.closest('[data-context-action="change-email"]');
        if (changeEmailBtn) {
            e.preventDefault();
            e.stopPropagation();
            if (selectedPatientId) {
                window.location.href = `/admin/patients/${selectedPatientId}/change-email`;
            }
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
