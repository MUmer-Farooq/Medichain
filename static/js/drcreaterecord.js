 let prescRowCount = 1;

    function loadPatientInfo(id) {
      const summary = document.getElementById('patientSummary');
      const idField = document.getElementById('patientId');
      if (!id) { summary.style.display = 'none'; idField.value = ''; return; }
      const option = document.querySelector(`[name="patient_id"] option[value="${CSS.escape(id)}"]`);
      const d = option?.dataset.patient ? JSON.parse(option.dataset.patient) : null;
      if (d) {
        document.getElementById('pAge').textContent = d.date_of_birth || 'N/A';
        document.getElementById('pBlood').textContent = d.blood_group || 'N/A';
        document.getElementById('pAllergy').textContent = 'N/A';
        document.getElementById('pLastVisit').textContent = d.status || 'N/A';
        idField.value = id;
        summary.style.display = 'block';
      }
    }

    function addPrescRow() {
      const container = document.getElementById('prescriptionContainer');
      const row = document.createElement('div');
      row.className = 'prescription-row row g-2 mb-2 align-items-end';
      row.id = 'presc-' + prescRowCount;
      row.innerHTML = `<div class="col-md-4"><input type="text" class="form-control" name="med_name[]" placeholder="Drug name"/></div><div class="col-md-2"><input type="text" class="form-control" name="med_dose[]" placeholder="500mg"/></div><div class="col-md-2"><input type="text" class="form-control" name="med_freq[]" placeholder="TDS"/></div><div class="col-md-2"><input type="text" class="form-control" name="med_dur[]" placeholder="30 days"/></div><div class="col-md-2"><button type="button" class="btn btn-outline-danger btn-sm w-100" onclick="removePrescRow(${prescRowCount})"><i class="fas fa-trash"></i></button></div>`;
      container.appendChild(row);
      prescRowCount++;
    }

    function removePrescRow(id) {
      const row = document.getElementById('presc-' + id);
      if (row) row.remove();
    }

    /* BMI Calculator */
    document.querySelectorAll('[name="height"],[name="weight"]').forEach(el => {
      el.addEventListener('input', () => {
        const h = parseFloat(document.querySelector('[name="height"]').value) / 100;
        const w = parseFloat(document.querySelector('[name="weight"]').value);
        const bmiEl = document.querySelector('[name="bmi"]');
        if (h > 0 && w > 0) bmiEl.value = (w / (h * h)).toFixed(1);
      });
    });

    /* File List Display */
    document.getElementById('attachFiles').addEventListener('change', function () {
      const list = document.getElementById('fileList');
      list.innerHTML = '';
      Array.from(this.files).forEach(f => {
        list.innerHTML += `<div class="d-flex align-items-center gap-2 py-1 border-bottom fs-12"><i class="fas fa-file text-primary"></i><span class="flex-1">${f.name}</span><span class="text-muted">${(f.size / 1024 / 1024).toFixed(1)}MB</span></div>`;
      });
    });

    document.getElementById('recordForm').addEventListener('submit', function (event) {
      if (!this.checkValidity() || !document.getElementById('confirmAccuracy').checked) {
        event.preventDefault();
        this.classList.add('was-validated');
        if (!document.getElementById('confirmAccuracy').checked) MediChain.showToast('Please confirm record accuracy', 'warning');
        return;
      }
      const submitButton = this.querySelector('button[type="submit"]');
      if (submitButton.disabled) { event.preventDefault(); return; }
      submitButton.disabled = true;
      submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving Record…';
    });