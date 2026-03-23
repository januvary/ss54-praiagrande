/**
 * Document Viewer - Shared modal for viewing documents
 * 
 * Usage: 
 * - Include this script and the modal HTML
 * - Add data-action="open-doc-viewer" to trigger elements
 * - Data attributes: data-doc-id, data-mime-type, data-filename, data-base-path
 */

(function() {
    'use strict';

    // ============================================================
    // Helper Functions
    // ============================================================

    function clearElement(element) {
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
    }

    // ============================================================
    // Core Functions
    // ============================================================

    function openDocViewer(docId, mimeType, filename, basePath) {
        basePath = basePath || '/documentos';
        const modal = document.getElementById('docViewerModal');
        const title = document.getElementById('docViewerTitle');
        const content = document.getElementById('docViewerContent');

        if (!modal || !title || !content) return;

        clearElement(content);
        title.textContent = filename;

        if (mimeType && mimeType.startsWith('image/')) {
            const img = document.createElement('img');
            img.src = `${basePath}/${docId}/download`;
            img.alt = filename;
            img.style.cssText = 'max-width: 100%; max-height: 100%; object-fit: contain; display: block; margin: auto;';
            content.appendChild(img);
        } else if (mimeType === 'application/pdf') {
            const embed = document.createElement('embed');
            embed.src = `${basePath}/${docId}/download`;
            embed.type = 'application/pdf';
            embed.style.cssText = 'width: 100%; height: 100%;';
            content.appendChild(embed);
        } else {
            const p = document.createElement('p');
            p.className = 'p-8 text-center text-slate-500';
            p.textContent = 'Visualização não disponível para este tipo de arquivo.';
            content.appendChild(p);
        }

        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }

    function closeDocViewer(event) {
        const modal = document.getElementById('docViewerModal');
        if (!modal) return;

        // If event provided and target is not the modal itself, don't close
        if (event && event.target !== modal) return;

        modal.classList.add('hidden');
        modal.classList.remove('flex');

        const content = document.getElementById('docViewerContent');
        if (content) clearElement(content);
    }

    // ============================================================
    // Event Delegation
    // ============================================================

    document.addEventListener('click', function(e) {
        // Open doc viewer
        const openBtn = e.target.closest('[data-action="open-doc-viewer"]');
        if (openBtn) {
            const docId = openBtn.getAttribute('data-doc-id');
            const mimeType = openBtn.getAttribute('data-mime-type');
            const filename = openBtn.getAttribute('data-filename');
            const basePath = openBtn.getAttribute('data-base-path') || '/documentos';
            openDocViewer(docId, mimeType, filename, basePath);
            return;
        }

        // Close doc viewer
        const closeBtn = e.target.closest('[data-action="close-doc-viewer"]');
        if (closeBtn) {
            closeDocViewer();
            return;
        }

        // Close on modal background click
        const modal = document.getElementById('docViewerModal');
        if (modal && e.target === modal) {
            closeDocViewer();
        }
    });

    // Close on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modal = document.getElementById('docViewerModal');
            if (modal && !modal.classList.contains('hidden')) {
                closeDocViewer();
            }
        }
    });

    // ============================================================
    // Expose to global scope for backward compatibility
    // ============================================================
    window.openDocViewer = openDocViewer;
    window.closeDocViewer = closeDocViewer;

})();
