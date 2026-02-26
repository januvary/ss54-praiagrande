/**
 * File Upload Web Component
 * Usage: <file-upload-input name="doc_1" accept=".pdf,.jpg,.jpeg,.png" multiple preview></file-upload-input>
 */
class FileUploadInput extends HTMLElement {
  constructor() {
    super();
    this.files = [];
    this.fileInput = null;
    this.objectUrls = new Map(); // Store object URLs by index
  }

  connectedCallback() {
    const name = this.getAttribute('name') || 'files';
    const accept = this.getAttribute('accept') || '';
    const multiple = this.hasAttribute('multiple');
    const showPreview = this.hasAttribute('preview');

    this.innerHTML = `
      <div class="file-upload-component">
        <input type="file" name="${name}" id="${name}" accept="${accept}" ${multiple ? 'multiple' : ''} class="hidden">
        <label for="${name}"
          class="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 cursor-pointer transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path>
          </svg>
          <span class="file-label">Escolher arquivos</span>
        </label>
        <div class="file-list mt-3 space-y-2"></div>
      </div>
    `;

    this.fileInput = this.querySelector('input[type="file"]');
    this.fileLabel = this.querySelector('.file-label');
    this.fileList = this.querySelector('.file-list');
    this.showPreview = showPreview;

    // Handle file selection
    this.fileInput.addEventListener('change', (e) => {
      this.addFiles(Array.from(e.target.files));
      // Clear the input so change event fires again if same files selected
      e.target.value = '';
    });

    // Sync files to input before form submit
    const form = this.closest('form');
    if (form) {
      form.addEventListener('submit', () => this.syncFilesToInput());
    }
  }

  addFiles(newFiles) {
    // Add new files to our array (avoid duplicates by name+size)
    for (const file of newFiles) {
      const exists = this.files.some(f => f.name === file.name && f.size === file.size);
      if (!exists) {
        this.files.push(file);
      }
    }
    this.render();
  }

  removeFile(index) {
    // Revoke object URL to free memory
    if (this.objectUrls.has(index)) {
      URL.revokeObjectURL(this.objectUrls.get(index));
      this.objectUrls.delete(index);
    }
    this.files.splice(index, 1);
    this.render();
  }

  syncFilesToInput() {
    // Create a new FileList-like object with DataTransfer
    const dataTransfer = new DataTransfer();
    for (const file of this.files) {
      dataTransfer.items.add(file);
    }
    this.fileInput.files = dataTransfer.files;
  }

  formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  getFileIcon(mimeType) {
    if (mimeType === 'application/pdf') {
      return `<svg class="w-8 h-8 text-red-500" fill="currentColor" viewBox="0 0 24 24">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 2l5 5h-5V4zM8.5 13c.28 0 .5.22.5.5v3c0 .28-.22.5-.5.5s-.5-.22-.5-.5v-3c0-.28.22-.5.5-.5zm3 0c.28 0 .5.22.5.5v2h.5c.28 0 .5.22.5.5s-.22.5-.5.5h-1c-.28 0-.5-.22-.5-.5v-2.5c0-.28.22-.5.5-.5zm3 0h1c.28 0 .5.22.5.5s-.22.5-.5.5H15v.5h.5c.28 0 .5.22.5.5s-.22.5-.5.5H15v.5c0 .28-.22.5-.5.5s-.5-.22-.5-.5v-3c0-.28.22-.5.5-.5z"/>
      </svg>`;
    }
    return `<svg class="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
    </svg>`;
  }

  render() {
    if (this.files.length === 0) {
      this.fileLabel.textContent = 'Escolher arquivos';
      this.fileList.innerHTML = '';
      return;
    }

    this.fileLabel.textContent = `${this.files.length} arquivo(s) selecionado(s)`;

    this.fileList.innerHTML = this.files.map((file, index) => {
      const isImage = file.type.startsWith('image/');
      let preview;

      // Create and store object URL
      const objectUrl = URL.createObjectURL(file);
      this.objectUrls.set(index, objectUrl);

      if (this.showPreview) {
        if (isImage) {
          preview = `<img src="${objectUrl}" alt="${file.name}" class="w-12 h-12 object-cover rounded border border-slate-200">`;
        } else {
          preview = this.getFileIcon(file.type);
        }

        // Wrap in clickable div with data attributes
        preview = `
          <div class="cursor-pointer hover:ring-2 hover:ring-accent transition-all"
               data-upload-component="${this.getAttribute('name')}"
               data-file-index="${index}">
            ${preview}
          </div>
        `;
      } else {
        preview = this.getFileIcon(file.type);
      }

      return `
        <div class="flex items-center gap-3 p-2 bg-slate-50 rounded-lg border border-slate-200">
          <div class="flex-shrink-0">${preview}</div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-slate-700 truncate">${file.name}</p>
            <p class="text-xs text-slate-500">${this.formatFileSize(file.size)}</p>
          </div>
          <button type="button"
            class="flex-shrink-0 p-1 text-slate-400 hover:text-red-500 transition-colors remove-file-btn"
            data-upload-component="${this.getAttribute('name')}"
            data-file-index="${index}"
            title="Remover arquivo">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
      `;
    }).join('');
  }
}

customElements.define('file-upload-input', FileUploadInput);
