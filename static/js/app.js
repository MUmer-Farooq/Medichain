/* ============================================================
   MediChain - Main Application JavaScript
   app.js - Core functionality, sidebar, navbar, utilities
   ============================================================ */

'use strict';

/* ---------- DOM Ready ---------- */
document.addEventListener('DOMContentLoaded', function () {
  initSidebar();
  initTooltips();
  initDropdowns();
  initActiveNav();
  initSearchHighlight();
  initAOS();
  loadComponents();
});

/* ---------- Load Components (Navbar + Sidebar) ----------
   For Flask integration: replace with {% include 'components/navbar.html' %}
   and {% include 'components/sidebar.html' %}
   -------------------------------------------------------- */
function loadComponents() {
  const sidebarPlaceholder = document.getElementById('sidebar-placeholder');
  const navbarPlaceholder  = document.getElementById('navbar-placeholder');

  if (sidebarPlaceholder && sidebarPlaceholder.dataset.src) {
    fetch(sidebarPlaceholder.dataset.src)
      .then(r => r.ok ? r.text() : '')
      .then(html => {
        if (html) {
          sidebarPlaceholder.innerHTML = html;
          initActiveNav();
        }
      }).catch(() => {});
  }

  if (navbarPlaceholder && navbarPlaceholder.dataset.src) {
    fetch(navbarPlaceholder.dataset.src)
      .then(r => r.ok ? r.text() : '')
      .then(html => {
        if (html) {
          navbarPlaceholder.innerHTML = html;
          initTooltips();
        }
      }).catch(() => {});
  }
}

/* ---------- Sidebar Toggle ---------- */
function initSidebar() {
  const toggleBtn  = document.getElementById('sidebar-toggle');
  const sidebar    = document.getElementById('mc-sidebar');
  const overlay    = document.getElementById('sidebar-overlay');
  const body       = document.body;
  const isMobile   = () => window.innerWidth < 992;

  if (!sidebar) return;

  // Restore collapse state on desktop
  if (!isMobile() && localStorage.getItem('sidebarCollapsed') === 'true') {
    body.classList.add('sidebar-collapsed');
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', function () {
      if (isMobile()) {
        sidebar.classList.toggle('show');
        if (overlay) overlay.classList.toggle('show');
      } else {
        body.classList.toggle('sidebar-collapsed');
        localStorage.setItem('sidebarCollapsed', body.classList.contains('sidebar-collapsed'));
      }
    });
  }

  // Close on overlay click
  if (overlay) {
    overlay.addEventListener('click', closeSidebar);
  }

  // Close on ESC key
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isMobile()) closeSidebar();
  });

  function closeSidebar() {
    sidebar.classList.remove('show');
    if (overlay) overlay.classList.remove('show');
  }

  // Handle resize
  window.addEventListener('resize', debounce(function () {
    if (!isMobile()) {
      sidebar.classList.remove('show');
      if (overlay) overlay.classList.remove('show');
    }
  }, 250));
}

/* ---------- Active Navigation ---------- */
function initActiveNav() {
  const currentPath = window.location.pathname.split('/').pop() || 'index.html';
  const navLinks = document.querySelectorAll('.nav-item-link');

  navLinks.forEach(link => {
    const href = link.getAttribute('href') || '';
    const linkPage = href.split('/').pop() || '';
    if (linkPage && linkPage === currentPath) {
      link.classList.add('active');
    }
  });
}

/* ---------- Bootstrap Tooltips ---------- */
function initTooltips() {
  const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(el => {
    new bootstrap.Tooltip(el, { trigger: 'hover', placement: el.dataset.bsPlacement || 'top' });
  });
}

/* ---------- Bootstrap Dropdowns ---------- */
function initDropdowns() {
  // Bootstrap handles dropdowns natively, but we enhance them
  const dropdowns = document.querySelectorAll('.dropdown-toggle');
  dropdowns.forEach(el => {
    el.addEventListener('show.bs.dropdown', function () {
      const menu = this.nextElementSibling;
      if (menu) menu.style.animation = 'dropIn 0.2s ease';
    });
  });
}

/* ---------- AOS Animation Init ---------- */
function initAOS() {
  if (typeof AOS !== 'undefined') {
    AOS.init({
      duration: 600,
      easing: 'ease-out-cubic',
      once: true,
      offset: 40,
    });
  }
}

/* ---------- Search Highlight ---------- */
function initSearchHighlight() {
  const searchInput = document.getElementById('table-search');
  if (!searchInput) return;

  searchInput.addEventListener('input', debounce(function () {
    const query = this.value.trim().toLowerCase();
    const rows  = document.querySelectorAll('.mc-table tbody tr');

    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = query === '' || text.includes(query) ? '' : 'none';
    });

    // Show/hide empty state
    const visibleRows = document.querySelectorAll('.mc-table tbody tr:not([style*="none"])');
    const emptyState  = document.getElementById('table-empty-state');
    if (emptyState) {
      emptyState.style.display = visibleRows.length === 0 ? 'block' : 'none';
    }
  }, 300));
}

/* ---------- Table Sorting ---------- */
function initTableSort() {
  const headers = document.querySelectorAll('.mc-table th[data-sort]');
  let currentSort = { col: null, asc: true };

  headers.forEach(th => {
    th.style.cursor = 'pointer';
    th.innerHTML += ' <i class="fas fa-sort ms-1 opacity-25 fs-11"></i>';

    th.addEventListener('click', function () {
      const col   = this.dataset.sort;
      const tbody = this.closest('table').querySelector('tbody');
      const rows  = Array.from(tbody.querySelectorAll('tr'));
      const idx   = Array.from(this.parentElement.children).indexOf(this);

      currentSort.asc = currentSort.col === col ? !currentSort.asc : true;
      currentSort.col = col;

      rows.sort((a, b) => {
        const aVal = a.cells[idx]?.textContent.trim() || '';
        const bVal = b.cells[idx]?.textContent.trim() || '';
        const num  = !isNaN(parseFloat(aVal)) && !isNaN(parseFloat(bVal));
        if (num) return currentSort.asc
          ? parseFloat(aVal) - parseFloat(bVal)
          : parseFloat(bVal) - parseFloat(aVal);
        return currentSort.asc
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      });

      rows.forEach(r => tbody.appendChild(r));

      // Update icons
      headers.forEach(h => {
        const icon = h.querySelector('.fa-sort, .fa-sort-up, .fa-sort-down');
        if (icon) {
          icon.className = h === this
            ? `fas ${currentSort.asc ? 'fa-sort-up' : 'fa-sort-down'} ms-1 fs-11 text-primary`
            : 'fas fa-sort ms-1 opacity-25 fs-11';
        }
      });
    });
  });
}

/* ---------- Pagination ---------- */
function initPagination(options = {}) {
  const {
    tableId     = 'mc-table',
    pageSize    = 10,
    paginationId= 'pagination',
  } = options;

  const table  = document.getElementById(tableId);
  const pgEl   = document.getElementById(paginationId);
  if (!table || !pgEl) return;

  const rows   = Array.from(table.querySelectorAll('tbody tr'));
  let current  = 1;
  const total  = () => Math.ceil(rows.filter(r => r.style.display !== 'none').length / pageSize);

  function render() {
    const visRows = rows.filter(r => r.style.display !== 'none');
    const start   = (current - 1) * pageSize;
    const end     = start + pageSize;

    visRows.forEach((r, i) => { r.style.display = (i >= start && i < end) ? '' : 'none'; });

    pgEl.innerHTML = '';
    const pages = total();

    if (pages <= 1) return;

    // Prev
    pgEl.innerHTML += `<li class="page-item ${current===1?'disabled':''}">
      <a class="page-link" href="#" data-page="${current-1}"><i class="fas fa-chevron-left fs-11"></i></a></li>`;

    for (let p = 1; p <= pages; p++) {
      if (p === 1 || p === pages || (p >= current - 1 && p <= current + 1)) {
        pgEl.innerHTML += `<li class="page-item ${p===current?'active':''}">
          <a class="page-link" href="#" data-page="${p}">${p}</a></li>`;
      } else if (p === current - 2 || p === current + 2) {
        pgEl.innerHTML += `<li class="page-item disabled"><span class="page-link">…</span></li>`;
      }
    }

    // Next
    pgEl.innerHTML += `<li class="page-item ${current===pages?'disabled':''}">
      <a class="page-link" href="#" data-page="${current+1}"><i class="fas fa-chevron-right fs-11"></i></a></li>`;

    pgEl.querySelectorAll('a.page-link').forEach(a => {
      a.addEventListener('click', e => {
        e.preventDefault();
        const p = parseInt(a.dataset.page);
        if (p >= 1 && p <= total()) { current = p; render(); }
      });
    });
  }

  render();
}

/* ---------- Filter Dropdown ---------- */
function filterTable(selectEl) {
  const val   = selectEl.value.toLowerCase();
  const col   = parseInt(selectEl.dataset.col || '0');
  const rows  = document.querySelectorAll('.mc-table tbody tr');

  rows.forEach(row => {
    const cell = row.cells[col];
    if (!cell) return;
    const text = cell.textContent.toLowerCase();
    row.style.display = (val === '' || text.includes(val)) ? '' : 'none';
  });
}

/* ---------- Confirm Delete (SweetAlert2) ---------- */
function confirmDelete(options = {}) {
  const {
    title  = 'Are you sure?',
    text   = 'This action cannot be undone.',
    url    = '#',
    method = 'POST',
  } = options;

  if (typeof Swal === 'undefined') {
    if (confirm(title + '\n' + text)) window.location.href = url;
    return;
  }

  Swal.fire({
    title,
    text,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#f44336',
    cancelButtonColor:  '#6c757d',
    confirmButtonText: 'Yes, delete it!',
    cancelButtonText:  'Cancel',
    borderRadius: '12px',
    customClass: { popup: 'mc-swal' },
  }).then(result => {
    if (result.isConfirmed) {
      if (method === 'GET') {
        window.location.href = url;
      } else {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = url;
        document.body.appendChild(form);
        form.submit();
      }
    }
  });
}

/* ---------- Toast Notification ---------- */
function showToast(message, type = 'success') {
  if (typeof Swal !== 'undefined') {
    Swal.mixin({
      toast: true,
      position: 'top-end',
      showConfirmButton: false,
      timer: 3500,
      timerProgressBar: true,
    }).fire({ icon: type, title: message });
    return;
  }

  // Fallback
  const toastEl = document.createElement('div');
  toastEl.className = `mc-alert mc-alert-${type} position-fixed top-0 end-0 m-3`;
  toastEl.style.cssText = 'z-index:9999;min-width:280px;animation:dropIn .2s ease;';
  toastEl.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} alert-icon"></i><span>${message}</span>`;
  document.body.appendChild(toastEl);
  setTimeout(() => toastEl.remove(), 3500);
}

/* ---------- Form Validation ---------- */
function initFormValidation(formId) {
  const form = document.getElementById(formId);
  if (!form) return;

  form.addEventListener('submit', function (e) {
    if (!form.checkValidity()) {
      e.preventDefault();
      e.stopPropagation();
      form.classList.add('was-validated');

      // Scroll to first error
      const firstInvalid = form.querySelector(':invalid');
      if (firstInvalid) {
        firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
        firstInvalid.focus();
      }
    } else {
      // Show loading state
      const submitBtn = form.querySelector('[type="submit"]');
      if (submitBtn) {
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing…';
        submitBtn.disabled = true;
      }
    }
  });

  // Real-time validation feedback
  form.querySelectorAll('input, select, textarea').forEach(field => {
    field.addEventListener('blur', function () {
      if (form.classList.contains('was-validated')) {
        this.classList.toggle('is-invalid', !this.checkValidity());
        this.classList.toggle('is-valid',   this.checkValidity());
      }
    });
  });
}

/* ---------- Password Toggle ---------- */
function togglePassword(inputId, iconEl) {
  const input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    if (iconEl) { iconEl.classList.remove('fa-eye'); iconEl.classList.add('fa-eye-slash'); }
  } else {
    input.type = 'password';
    if (iconEl) { iconEl.classList.remove('fa-eye-slash'); iconEl.classList.add('fa-eye'); }
  }
}

/* ---------- Copy to Clipboard ---------- */
function copyToClipboard(text, btnEl) {
  navigator.clipboard.writeText(text).then(() => {
    if (btnEl) {
      const orig = btnEl.innerHTML;
      btnEl.innerHTML = '<i class="fas fa-check text-success"></i>';
      setTimeout(() => { btnEl.innerHTML = orig; }, 1500);
    }
    showToast('Copied to clipboard!', 'success');
  }).catch(() => showToast('Failed to copy', 'error'));
}

/* ---------- Debounce Utility ---------- */
function debounce(fn, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

/* ---------- Format Date ---------- */
function formatDate(dateStr, format = 'short') {
  const date = new Date(dateStr);
  if (isNaN(date)) return dateStr;
  const opts = format === 'short'
    ? { year: 'numeric', month: 'short', day: 'numeric' }
    : { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
  return date.toLocaleDateString('en-US', opts);
}

/* ---------- Relative Time ---------- */
function timeAgo(dateStr) {
  const date  = new Date(dateStr);
  const now   = new Date();
  const diff  = Math.floor((now - date) / 1000);

  if (diff < 60)   return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400)return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/* ---------- Loading Overlay ---------- */
function showLoading(message = 'Loading…') {
  let overlay = document.getElementById('mc-loading');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'mc-loading';
    overlay.innerHTML = `
      <div style="background:rgba(255,255,255,0.95);border-radius:12px;padding:2rem 3rem;text-align:center;box-shadow:0 8px 32px rgba(26,115,232,0.15);">
        <div class="spinner-border text-primary mb-3" style="width:2.5rem;height:2.5rem;"></div>
        <p class="mb-0 fw-500 text-medium" id="mc-loading-msg">${message}</p>
      </div>`;
    overlay.style.cssText = 'position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:9999;background:rgba(0,0,0,0.15);backdrop-filter:blur(4px);';
    document.body.appendChild(overlay);
  } else {
    document.getElementById('mc-loading-msg').textContent = message;
  }
}

function hideLoading() {
  const overlay = document.getElementById('mc-loading');
  if (overlay) overlay.remove();
}

/* ---------- Expose Globals ---------- */
window.MediChain = {
  confirmDelete,
  showToast,
  initFormValidation,
  initTableSort,
  initPagination,
  filterTable,
  togglePassword,
  copyToClipboard,
  formatDate,
  timeAgo,
  showLoading,
  hideLoading,
  debounce,
};
