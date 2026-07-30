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

// Settings Tabs
function switchTab(id, el) {
    document.querySelectorAll('.settings-tab').forEach(t => t.classList.add('d-none'));
    const targetTab = document.getElementById('tab-' + id);
    if (targetTab) targetTab.classList.remove('d-none');

    document.querySelectorAll('.nav .nav-item-link').forEach(a => a.classList.remove('active'));
    el.classList.add('active');

    if (typeof event !== 'undefined') event.preventDefault();
}
