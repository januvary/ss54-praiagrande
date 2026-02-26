// Event delegation for file upload remove buttons
document.addEventListener('click', function(e) {
    const removeBtn = e.target.closest('.remove-file-btn');
    if (removeBtn) {
        e.preventDefault();
        const componentName = removeBtn.getAttribute('data-upload-component');
        const fileIndex = parseInt(removeBtn.getAttribute('data-file-index'));
        const component = document.querySelector(`file-upload-input[name="${componentName}"]`);
        if (component) {
            component.removeFile(fileIndex);
        }
    }
});
