function handleDragOver(e) { e.preventDefault(); document.getElementById('dropZone').classList.add('drag-over'); }
    function handleDragLeave() { document.getElementById('dropZone').classList.remove('drag-over'); }
    function handleDrop(e) {
      e.preventDefault();
      handleDragLeave();
      const input = document.getElementById('fileInput');
      const transfer = new DataTransfer();
      Array.from(e.dataTransfer.files).forEach(file => transfer.items.add(file));
      input.files = transfer.files;
      handleFiles(input.files);
    }

    function handleFiles(files) {
      const queue = document.getElementById('fileQueue');
        const allowed = ['pdf', 'jpg', 'jpeg', 'png', 'dcm'];
        Array.from(files).forEach(file => {
          const extension = file.name.split('.').pop().toLowerCase();
          if (!allowed.includes(extension) || file.size > 20 * 1024 * 1024) {
            MediChain.showToast('Only PDF, JPG, PNG, or DICOM files up to 20MB are accepted.', 'warning');
            return;
          }
        const item = document.createElement('div');
        item.className = 'upload-item';
        item.innerHTML = `<div class="ui-icon"><i class="fas fa-file"></i></div><div class="flex-1"><div class="fw-500 fs-13">${file.name}</div><div class="fs-11 text-muted">${(file.size / 1024 / 1024).toFixed(2)} MB</div><div class="upload-progress mt-1"><div class="upload-progress-bar" style="width:0%" id="pb-${Date.now()}"></div></div></div><button type="button" class="btn btn-sm btn-outline-danger btn-icon" onclick="this.closest('.upload-item').remove()"><i class="fas fa-times fs-11"></i></button>`;
        queue.appendChild(item);
        const pb = item.querySelector('.upload-progress-bar');
        let w = 0;
        const t = setInterval(() => { w += Math.random() * 15; if (w >= 100) { w = 100; clearInterval(t); } pb.style.width = w + '%'; }, 200);
      });
    }

  document.getElementById('uploadForm').addEventListener('submit', function (event) {
    if (!this.checkValidity() || !document.getElementById('confirmUpload').checked || !document.getElementById('fileInput').files.length) {
      event.preventDefault();
      this.classList.add('was-validated');
      if (!document.getElementById('confirmUpload').checked) MediChain.showToast('Please confirm authorization.', 'warning');
      return;
    }
    const submit = this.querySelector('button[type="submit"]');
    if (submit.disabled) { event.preventDefault(); return; }
    submit.disabled = true;
    submit.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Uploading…';
  });

  document.querySelector('[name="patient_id"]')?.addEventListener('change', event => {
    const patientId = event.target.value;
    const recordSelect = document.querySelector('[name="record_id"]');
    recordSelect?.querySelectorAll('option[data-patient-id]').forEach(option => {
      option.hidden = Boolean(patientId && option.dataset.patientId !== patientId);
    });
    if (recordSelect && recordSelect.selectedOptions[0]?.hidden) recordSelect.value = '';
  });