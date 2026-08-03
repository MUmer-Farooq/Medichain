/* System Admin Module JavaScript */

document.addEventListener('DOMContentLoaded', () => {
    // Blockchain Monitor Logic
    const terminal = document.getElementById('bc-terminal');
    if (terminal) {
        let blockNum = 18432, txNum = 94218;
        const types = ['CREATE_RECORD', 'UPDATE_RECORD', 'READ_RECORD', 'GRANT_ACCESS', 'REVOKE_ACCESS'];

        setInterval(() => {
            const tx = Math.floor(Math.random() * 3) + 1;
            txNum += tx;
            if (Math.random() > .6) blockNum++;

            const liveBlockCount = document.getElementById('live-block-count');
            const liveTxCount = document.getElementById('live-tx-count');

            if (liveBlockCount) liveBlockCount.textContent = blockNum.toLocaleString();
            if (liveTxCount) liveTxCount.textContent = txNum.toLocaleString();

            const type = types[Math.floor(Math.random() * types.length)];
            terminal.innerHTML = `<div><span style="color:#69f0ae">✓</span> Block #${blockNum.toLocaleString()} — COMMITTED</div><div style="color:#80cbc4">type: <span style="color:#f48fb1">${type}</span></div><div style="color:#546e7a">--- ${new Date().toLocaleTimeString()} ---</div>` + terminal.innerHTML;

            if (terminal.children.length > 40) terminal.lastChild.remove();
        }, 4000);
    }

    // Hospitals page logic
    const tableSearch = document.getElementById('table-search');
    const hasPagination = document.getElementById('pagination');
    if ((tableSearch || hasPagination) && typeof MediChain !== 'undefined') {
        if (typeof MediChain.initTableSort === 'function') {
            MediChain.initTableSort();
        }
        if (typeof MediChain.initPagination === 'function') {
            MediChain.initPagination({ pageSize: 10 });
        }
    }
});

// Dashboard mobile sidebar
function closeSidebarMobile() {
    const sidebar = document.getElementById('mc-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.remove('show');
    if (overlay) overlay.classList.remove('show');
}

// Hospital Requests actions
function approveRequest(hospitalId, hospitalName) {

    Swal.fire({
        icon: "question",
        title: "Approve Hospital?",
        text: `Approve ${hospitalName}?`,
        showCancelButton: true,
        confirmButtonText: "Approve",
        confirmButtonColor: "#198754"
    }).then((result) => {

        if (result.isConfirmed) {

            fetch(`/system-admin/approve_hospital/${hospitalId}`, {
                method: "POST"
            })
                .then(() => {
                    Swal.fire({
                        icon: "success",
                        title: "Approved",
                        text: "Hospital approved successfully."
                    }).then(() => {
                        location.reload();
                    });
                });

        }

    });

}
function rejectRequest(hospitalId, hospitalName) {

    Swal.fire({
        icon: "warning",
        title: "Reject Hospital?",
        text: `Reject ${hospitalName}?`,
        showCancelButton: true,
        confirmButtonText: "Reject",
        confirmButtonColor: "#dc3545"
    }).then((result) => {

        if (result.isConfirmed) {

            fetch(`/system-admin/reject_hospital/${hospitalId}`, {
                method: "POST"
            })
                .then(() => {
                    Swal.fire({
                        icon: "success",
                        title: "Rejected",
                        text: "Hospital rejected."
                    }).then(() => {
                        location.reload();
                    });
                });

        }

    });

}

function approveAll() {
    if (typeof MediChain !== 'undefined') {
        MediChain.showToast('Select hospitals using checkboxes first', 'warning');
    }
}

/* ============================================================
   Manage Hospitals — View / Edit / Status / Delete
   ============================================================ */
const MediChainHospitals = (() => {
    const STATUS_BADGES = {
        approved: 'success',
        pending: 'warning',
        rejected: 'danger',
        suspended: 'secondary',
    };

    function getStatusBadgeClass(status) {
        return STATUS_BADGES[status] || 'secondary';
    }

    function getStatusLabel(status) {
        const map = { approved: 'Approved', pending: 'Pending', rejected: 'Rejected', suspended: 'Suspended' };
        return map[status] || status || 'Unknown';
    }

    function hospitalCache() {
        return JSON.parse(document.getElementById('hospitals-data')?.textContent || '[]');
    }

    function findRow(id) {
        return document.querySelector(`#mc-table tbody tr[data-hospital-id="${id}"]`);
    }

    /* Refresh stats + header/footer counts from current table rows */
    function refreshCounts() {
        const rows = Array.from(document.querySelectorAll('#mc-table tbody tr[data-hospital-id]'));
        let active = 0, pending = 0, rejected = 0, suspended = 0;
        rows.forEach(r => {
            const s = r.dataset.status || '';
            if (s === 'approved') active++;
            else if (s === 'pending') pending++;
            else if (s === 'rejected') rejected++;
            else if (s === 'suspended') suspended++;
        });

        const set = (id, v) => {
            const el = document.getElementById(id);
            if (el) el.textContent = v;
        };
        set('stat-active', active);
        set('stat-pending', pending);
        set('stat-suspended', suspended);
        set('stat-rejected', rejected);
        set('stat-total', rows.length);

        // Card header badge + footer
        const headerBadge = document.querySelector('.card-header .badge-primary-soft');
        if (headerBadge) headerBadge.textContent = rows.length;
        const footer = document.querySelector('.card-footer small.text-muted');
        if (footer) footer.textContent = `Showing ${rows.length} hospitals`;

        // Sidebar pending badge
        const pendingBadge = document.querySelector('.sidebar-nav .nav-badge.danger');
        if (pendingBadge) pendingBadge.textContent = pending;

        // Page-header Pending Requests badge
        document.querySelectorAll('.page-header-right .badge').forEach(b => {
            if (b.classList.contains('bg-danger')) b.textContent = pending;
        });
    }

    function updateRow(row, hospital) {
        if (!row) return;
        row.dataset.status = hospital.status;
        row.dataset.hospitalId = hospital.hospital_id;

        // Name + reg
        const nameDiv = row.querySelector('td:nth-child(2) .fw-600');
        const regDiv = row.querySelector('td:nth-child(2) .text-muted');
        if (nameDiv) nameDiv.textContent = hospital.hospital_name;
        if (regDiv) regDiv.textContent = hospital.registration_number;

        // City
        const cityTd = row.querySelector('td:nth-child(3)');
        if (cityTd) cityTd.textContent = hospital.city;

        // Doctors
        const docsTd = row.querySelector('td:nth-child(5)');
        if (docsTd) docsTd.textContent = hospital.doctor_count || 0;

        // Status badge
        const badge = row.querySelector('.status-badge');
        if (badge) {
            badge.className = `badge badge-${getStatusBadgeClass(hospital.status)}-soft status-badge`;
            badge.textContent = getStatusLabel(hospital.status);
        }

        // Actions — re-render based on status
        const actionsCell = row.querySelector('td:last-child');
        if (actionsCell) {
            actionsCell.innerHTML = renderActions(hospital);
        }
        bindActions();
    }

    function renderActions(h) {
        const id = h.hospital_id;
        const base = [
            `<a href="#" class="btn-icon btn-view" data-hospital-id="${id}" title="View" data-bs-toggle="tooltip"><i class="fas fa-eye"></i></a>`,
            `<a href="#" class="btn-icon btn-edit" data-hospital-id="${id}" title="Edit" data-bs-toggle="tooltip"><i class="fas fa-pen"></i></a>`,
        ];
        if (h.status === 'pending') {
            base.push(`<a href="#" class="btn-icon btn-success btn-approve" data-hospital-id="${id}" title="Approve" data-bs-toggle="tooltip"><i class="fas fa-check"></i></a>`);
            base.push(`<a href="#" class="btn-icon btn-danger btn-reject" data-hospital-id="${id}" title="Reject" data-bs-toggle="tooltip"><i class="fas fa-times"></i></a>`);
        } else if (h.status === 'suspended') {
            base.push(`<a href="#" class="btn-icon btn-success btn-toggle-status" data-hospital-id="${id}" data-action="activate" title="Activate" data-bs-toggle="tooltip"><i class="fas fa-play"></i></a>`);
        } else {
            base.push(`<a href="#" class="btn-icon btn-warning btn-toggle-status" data-hospital-id="${id}" data-action="suspend" title="Suspend" data-bs-toggle="tooltip"><i class="fas fa-pause"></i></a>`);
        }
        base.push(`<a href="#" class="btn-icon btn-danger btn-delete" data-hospital-id="${id}" title="Delete" data-bs-toggle="tooltip"><i class="fas fa-trash"></i></a>`);
        return `<div class="table-actions">${base.join('')}</div>`;
    }

    function bindActions() {
        document.querySelectorAll('#mc-table .btn-view').forEach(a => {
            a.onclick = (e) => { e.preventDefault(); openModal(a.dataset.hospitalId, 'view'); };
        });
        document.querySelectorAll('#mc-table .btn-edit').forEach(a => {
            a.onclick = (e) => { e.preventDefault(); openModal(a.dataset.hospitalId, 'edit'); };
        });
        document.querySelectorAll('#mc-table .btn-approve').forEach(a => {
            a.onclick = (e) => { e.preventDefault(); changeStatus(a.dataset.hospitalId, 'approved'); };
        });
        document.querySelectorAll('#mc-table .btn-reject').forEach(a => {
            a.onclick = (e) => { e.preventDefault(); changeStatus(a.dataset.hospitalId, 'rejected'); };
        });
        document.querySelectorAll('#mc-table .btn-toggle-status').forEach(a => {
            a.onclick = (e) => {
                e.preventDefault();
                const action = a.dataset.action === 'activate' ? 'approved' : 'suspended';
                changeStatus(a.dataset.hospitalId, action);
            };
        });
        document.querySelectorAll('#mc-table .btn-delete').forEach(a => {
            a.onclick = (e) => { e.preventDefault(); deleteHospital(a.dataset.hospitalId); };
        });
    }

    function fetchHospitals() {
        return fetch('/system-admin/api/hospitals')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    data.hospitals.forEach(h => updateRow(findRow(h.hospital_id), h));
                    refreshCounts();
                }
            })
            .catch(() => {});
    }

    function openModal(id, mode) {
        const h = hospitalCache().find(x => String(x.hospital_id) === String(id));
        if (!h) return;

        const setVal = (elId, val) => {
            const el = document.getElementById(elId);
            if (el) el.value = val || '';
        };

        document.getElementById('modal-hospital-id').value = h.hospital_id;
        setVal('modal-hospital-name', h.hospital_name);
        setVal('modal-reg-number', h.registration_number);
        setVal('modal-city', h.city);
        setVal('modal-address', h.address);
        setVal('modal-phone', h.phone);
        setVal('modal-email', h.hospital_email);

        const statusSel = document.getElementById('modal-status');
        if (statusSel) statusSel.value = h.status;

        // In view mode, disable all fields; in edit mode enable them
        const inputs = document.querySelectorAll('#hospitalModal .form-control, #hospitalModal .form-select, #hospitalModal textarea');
        inputs.forEach(i => i.readOnly = mode === 'view');
        if (statusSel) statusSel.disabled = mode === 'view';

        const saveBtn = document.getElementById('modal-save-btn');
        if (saveBtn) saveBtn.style.display = mode === 'view' ? 'none' : '';

        new bootstrap.Modal(document.getElementById('hospitalModal')).show();
    }

    function saveHospitalChanges() {
        const id = document.getElementById('modal-hospital-id').value;
        const payload = {
            hospital_id: id,
            hospital_name: document.getElementById('modal-hospital-name').value,
            registration_number: document.getElementById('modal-reg-number').value,
            city: document.getElementById('modal-city').value,
            address: document.getElementById('modal-address').value,
            phone: document.getElementById('modal-phone').value,
            hospital_email: document.getElementById('modal-email').value,
            status: document.getElementById('modal-status').value,
        };

        if (!payload.hospital_name || !payload.registration_number || !payload.city || !payload.hospital_email) {
            MediChain.showToast('Please fill in required fields', 'warning');
            return;
        }

        fetch('/system-admin/hospitals/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    // Update local cache + row
                    const cache = hospitalCache();
                    const idx = cache.findIndex(x => String(x.hospital_id) === String(id));
                    if (idx > -1) {
                        Object.assign(cache[idx], payload);
                        document.getElementById('hospitals-data').textContent = JSON.stringify(cache);
                    }
                    updateRow(findRow(id), payload);
                    refreshCounts();

                    const modal = bootstrap.Modal.getInstance(document.getElementById('hospitalModal'));
                    if (modal) modal.hide();
                    MediChain.showToast(data.message || 'Hospital updated.', 'success');
                } else {
                    MediChain.showToast(data.error || 'Update failed', 'error');
                }
            })
            .catch(() => MediChain.showToast('Network error updating hospital', 'error'));
    }

    function changeStatus(id, status) {
        const h = hospitalCache().find(x => String(x.hospital_id) === String(id));
        const name = h ? h.hospital_name : 'this hospital';
        const label = getStatusLabel(status);
        const iconMap = { approved: 'success', rejected: 'warning', suspended: 'warning' };
        const confirmMap = {
            approved: { title: 'Approve Hospital?', text: `Approve ${name}?`, color: '#198754' },
            rejected: { title: 'Reject Hospital?', text: `Reject ${name}? This cannot be undone.`, color: '#dc3545' },
            suspended: { title: 'Suspend Hospital?', text: `Suspend ${name}? It will be temporarily deactivated.`, color: '#ff9800' },
        };
        const conf = confirmMap[status] || { title: 'Change Status?', text: `Change ${name} to ${label}?`, color: '#1a73e8' };

        Swal.fire({
            icon: iconMap[status] || 'question',
            title: conf.title,
            text: conf.text,
            showCancelButton: true,
            confirmButtonText: 'Yes',
            confirmButtonColor: conf.color,
            cancelButtonColor: '#6c757d',
        }).then(result => {
            if (!result.isConfirmed) return;
            fetch(`/system-admin/hospitals/${id}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status }),
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const cache = hospitalCache();
                        const idx = cache.findIndex(x => String(x.hospital_id) === String(id));
                        if (idx > -1) {
                            cache[idx].status = status;
                            document.getElementById('hospitals-data').textContent = JSON.stringify(cache);
                        }
                        const row = findRow(id);
                        const updated = { ...cache[idx], status };
                        updateRow(row, updated);
                        refreshCounts();
                        MediChain.showToast(data.message || `Hospital ${status}.`, 'success');
                    } else {
                        MediChain.showToast(data.error || 'Status change failed', 'error');
                    }
                })
                .catch(() => MediChain.showToast('Network error updating status', 'error'));
        });
    }

    function deleteHospital(id) {
        const h = hospitalCache().find(x => String(x.hospital_id) === String(id));
        const name = h ? h.hospital_name : 'this hospital';

        Swal.fire({
            icon: 'warning',
            title: 'Delete Hospital?',
            text: `Delete ${name}? This will permanently remove it and its users from the network.`,
            showCancelButton: true,
            confirmButtonText: 'Yes, delete it!',
            confirmButtonColor: '#f44336',
            cancelButtonColor: '#6c757d',
        }).then(result => {
            if (!result.isConfirmed) return;
            fetch(`/system-admin/hospitals/${id}/delete`, { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const row = findRow(id);
                        if (row) row.remove();
                        refreshCounts();
                        MediChain.showToast(data.message || 'Hospital deleted.', 'success');
                    } else {
                        MediChain.showToast(data.error || 'Delete failed', 'error');
                    }
                })
                .catch(() => MediChain.showToast('Network error deleting hospital', 'error'));
        });
    }

    function init() {
        bindActions();
    }

    return {
        init,
        bindActions,
        fetchHospitals,
        openModal,
        saveHospitalChanges,
        changeStatus,
        deleteHospital,
        refreshCounts,
        STATUS_BADGES,
    };
})();

// Expose saveHospitalChanges globally for the modal button
function saveHospitalChanges() {
    MediChainHospitals.saveHospitalChanges();
}

document.addEventListener('DOMContentLoaded', () => {
    if (typeof MediChainHospitals !== 'undefined') {
        MediChainHospitals.init();
    }
});

// Settings Tabs
function switchTab(id, el) {
    document.querySelectorAll('.settings-tab').forEach(t => t.classList.add('d-none'));
    const targetTab = document.getElementById('tab-' + id);
    if (targetTab) targetTab.classList.remove('d-none');

    document.querySelectorAll('.nav .nav-item-link').forEach(a => a.classList.remove('active'));
    el.classList.add('active');

    if (typeof event !== 'undefined') event.preventDefault();
}
