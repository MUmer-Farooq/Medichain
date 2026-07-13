function handleDragOver(e) { e.preventDefault(); document.getElementById('dropZone').classList.add('drag-over'); }
    function handleDragLeave() { document.getElementById('dropZone').classList.remove('drag-over'); }
    function handleDrop(e) { e.preventDefault(); handleDragLeave(); handleFiles(e.dataTransfer.files); }

    function handleFiles(files) {
      const queue = document.getElementById('fileQueue');
      Array.from(files).forEach(file => {
        const item = document.createElement('div');
        item.className = 'upload-item';
        item.innerHTML = `<div class="ui-icon"><i class="fas fa-file"></i></div><div class="flex-1"><div class="fw-500 fs-13">${file.name}</div><div class="fs-11 text-muted">${(file.size / 1024 / 1024).toFixed(2)} MB</div><div class="upload-progress mt-1"><div class="upload-progress-bar" style="width:0%" id="pb-${Date.now()}"></div></div></div><button type="button" class="btn btn-sm btn-outline-danger btn-icon" onclick="this.closest('.upload-item').remove()"><i class="fas fa-times fs-11"></i></button>`;
        queue.appendChild(item);
        const pb = item.querySelector('.upload-progress-bar');
        let w = 0;
        const t = setInterval(() => { w += Math.random() * 15; if (w >= 100) { w = 100; clearInterval(t); } pb.style.width = w + '%'; }, 200);
      });
    }

    function handleUpload(e) {
      e.preventDefault();
      if (!document.getElementById('confirmUpload').checked) { MediChain.showToast('Please confirm authorization', 'warning'); return; }
      MediChain.showLoading('Encrypting and uploading…');
      /* Flask Dynamic Route: POST /doctor/upload-report */
      setTimeout(() => {
        MediChain.hideLoading();
        MediChain.showToast('Files uploaded and attached to blockchain record!', 'success');
      }, 2000);
    }