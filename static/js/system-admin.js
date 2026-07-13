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
function approveRequest(name) {
    if (typeof Swal !== 'undefined' && typeof MediChain !== 'undefined') {
        Swal.fire({
            icon: 'question',
            title: 'Approve Hospital?',
            html: `<strong>${name}</strong> will be added to MediChain network.`,
            showCancelButton: true,
            confirmButtonText: 'Yes, Approve',
            confirmButtonColor: 'var(--success)',
            cancelButtonColor: '#6c757d'
        }).then(r => {
            if (r.isConfirmed) MediChain.showToast(`${name} approved successfully!`, 'success');
        });
    }
}

function rejectRequest(name) {
    if (typeof Swal !== 'undefined' && typeof MediChain !== 'undefined') {
        Swal.fire({
            icon: 'warning',
            title: 'Reject Application?',
            html: `<strong>${name}</strong>'s application will be rejected.`,
            showCancelButton: true,
            confirmButtonText: 'Yes, Reject',
            confirmButtonColor: 'var(--danger)',
            cancelButtonColor: '#6c757d',
            input: 'textarea',
            inputPlaceholder: 'Rejection reason (required)…'
        }).then(r => {
            if (r.isConfirmed && r.value) MediChain.showToast(`${name} rejected.`, 'error');
        });
    }
}

function approveAll() {
    if (typeof MediChain !== 'undefined') {
        MediChain.showToast('Select hospitals using checkboxes first', 'warning');
    }
}

// Settings Tabs
function switchTab(id, el) {
    document.querySelectorAll('.settings-tab').forEach(t => t.classList.add('d-none'));
    const targetTab = document.getElementById('tab-' + id);
    if (targetTab) targetTab.classList.remove('d-none');

    document.querySelectorAll('.nav .nav-item-link').forEach(a => a.classList.remove('active'));
    el.classList.add('active');

    if (typeof event !== 'undefined') event.preventDefault();
}
