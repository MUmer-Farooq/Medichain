'use strict';

document.addEventListener('DOMContentLoaded', () => {
  const search = document.getElementById('patient-search');
  const status = document.getElementById('status-filter');
  const rows = Array.from(document.querySelectorAll('#mc-table tbody tr[data-status]'));
  const count = document.getElementById('patient-count');
  const totalText = count ? count.textContent.replace(/^.* of /, 'of ') : '';

  const applyFilters = () => {
    const query = (search?.value || '').trim().toLowerCase();
    const selectedStatus = (status?.value || '').toLowerCase();
    let visible = 0;
    rows.forEach(row => {
      const matchesSearch = !query || (row.dataset.search || '').includes(query);
      const matchesStatus = !selectedStatus || row.dataset.status === selectedStatus;
      row.style.display = matchesSearch && matchesStatus ? '' : 'none';
      if (matchesSearch && matchesStatus) visible += 1;
    });
    if (count) count.textContent = `Showing ${visible} ${totalText}`;
  };

  search?.addEventListener('input', applyFilters);
  status?.addEventListener('change', applyFilters);

  const patientModal = document.getElementById('patientModal');
  patientModal?.addEventListener('show.bs.modal', event => {
    const trigger = event.relatedTarget;
    const form = document.getElementById('patient-form');
    const title = document.getElementById('patient-modal-title');
    const password = document.querySelector('[name="password"]');
    const mode = trigger?.dataset.mode || 'add';
    const patient = trigger?.dataset.patient ? JSON.parse(trigger.dataset.patient) : {};
    form.action = mode === 'edit' ? `/doctor/patients/${patient.patient_id}/edit` : '/doctor/patients/add';
    title.textContent = mode === 'edit' ? 'Edit Patient' : 'Add Patient';
    password.required = mode !== 'edit';
    document.getElementById('patient-password-field').style.display = mode === 'edit' ? 'none' : '';
    form.querySelectorAll('[name]').forEach(input => {
      if (input.name !== 'password') input.value = patient[input.name] ?? (input.name === 'status' ? 'active' : '');
      else input.value = '';
    });
  });

  document.getElementById('patientViewModal')?.addEventListener('show.bs.modal', event => {
    const patient = JSON.parse(event.relatedTarget.dataset.patient || '{}');
    const labels = {
      patient_id: 'Patient ID', full_name: 'Full Name', email: 'Email', phone: 'Phone', date_of_birth: 'Date of Birth',
      gender: 'Gender', blood_group: 'Blood Group', address: 'Address', emergency_contact: 'Emergency Contact',
      emergency_phone: 'Emergency Phone', status: 'Status', created_at: 'Created'
    };
    document.getElementById('patient-details').innerHTML = Object.entries(labels).map(([key, label]) => `<dt class="col-sm-4">${label}</dt><dd class="col-sm-8">${escapeHtml(patient[key] || 'N/A')}</dd>`).join('');
  });

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
  }
});
