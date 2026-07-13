 let prescRowCount = 1;

    /* Flask Dynamic Route: /api/patients/{id} for auto-fill */
    const patientData = {
      'MC-2024-008342': { age: '45 / Male', blood: 'O+', allergy: 'Penicillin', lastVisit: 'Jun 28, 2026' },
      'MC-2024-007891': { age: '34 / Female', blood: 'A+', allergy: 'None', lastVisit: 'Jun 25, 2026' },
      'MC-2024-006543': { age: '48 / Male', blood: 'B+', allergy: 'Sulfa drugs', lastVisit: 'Jun 20, 2026' },
      'MC-2024-005120': { age: '37 / Female', blood: 'AB+', allergy: 'None', lastVisit: 'Jun 15, 2026' },
    };

    function loadPatientInfo(id) {
      const summary = document.getElementById('patientSummary');
      const idField = document.getElementById('patientId');
      if (!id) { summary.style.display = 'none'; idField.value = ''; return; }
      const d = patientData[id];
      if (d) {
        document.getElementById('pAge').textContent = d.age;
        document.getElementById('pBlood').textContent = d.blood;
        document.getElementById('pAllergy').textContent = d.allergy;
        document.getElementById('pLastVisit').textContent = d.lastVisit;
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

    function submitRecord(e) {
      e.preventDefault();
      if (!document.getElementById('confirmAccuracy').checked) {
        MediChain.showToast('Please confirm record accuracy', 'warning'); return;
      }
      MediChain.showLoading('Committing to blockchain…');
      /* Flask Dynamic Route: POST /doctor/records/create */
      setTimeout(() => {
        MediChain.hideLoading();
        Swal.fire({ icon: 'success', title: 'Record Committed!', html: 'Medical record has been saved and committed to the Hyperledger Fabric blockchain.<br/><small class="text-muted">Block #18,433 • Tx-94219</small>', confirmButtonText: 'View Record', confirmButtonColor: 'var(--primary)' }).then(() => window.location.href = 'medical_history.html');
      }, 2200);
    }