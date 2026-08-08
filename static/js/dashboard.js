/* ============================================================
   MediChain - Dashboard JavaScript
   dashboard.js - Charts, analytics, real-time stats
   ============================================================ */

'use strict';

/* ---------- Chart Color Palette ---------- */
const MC_COLORS = {
  primary:   '#1a73e8',
  secondary: '#00bcd4',
  success:   '#00c853',
  warning:   '#ffab00',
  danger:    '#f44336',
  info:      '#29b6f6',
  purple:    '#7c4dff',
  pink:      '#e91e63',
  teal:      '#009688',
  orange:    '#ff6d00',
};

/* ---------- Global Chart Defaults ---------- */
function initChartDefaults() {
  if (typeof Chart === 'undefined') return;

  Chart.defaults.font.family = "'Poppins', sans-serif";
  Chart.defaults.font.size   = 12;
  Chart.defaults.color       = '#8898aa';
  Chart.defaults.responsive  = true;
  Chart.defaults.maintainAspectRatio = false;

  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.pointStyle    = 'circle';
  Chart.defaults.plugins.legend.labels.padding       = 16;
  Chart.defaults.plugins.legend.labels.font          = { family: "'Poppins', sans-serif", size: 11, weight: '500' };

  Chart.defaults.plugins.tooltip.backgroundColor    = 'rgba(26,31,54,0.9)';
  Chart.defaults.plugins.tooltip.padding            = 10;
  Chart.defaults.plugins.tooltip.cornerRadius       = 8;
  Chart.defaults.plugins.tooltip.titleFont          = { family: "'Poppins', sans-serif", size: 11, weight: '600' };
  Chart.defaults.plugins.tooltip.bodyFont           = { family: "'Poppins', sans-serif", size: 11 };
  Chart.defaults.plugins.tooltip.displayColors      = true;
  Chart.defaults.plugins.tooltip.boxPadding         = 4;
}

/* ---------- Patient Growth Line Chart ---------- */
function initPatientGrowthChart(canvasId = 'patientGrowthChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  /* <!-- Flask Dynamic Route: /api/analytics/patient-growth --> */
  const data = {
    registered: [120, 145, 162, 180, 210, 235, 258, 290, 315, 342, 378, 410],
    active:     [98,  120, 138, 155, 188, 210, 230, 265, 288, 315, 348, 380],
  };

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Registered Patients',
          data: data.registered,
          borderColor: MC_COLORS.primary,
          backgroundColor: createGradient(ctx, MC_COLORS.primary),
          borderWidth: 2.5,
          pointBackgroundColor: MC_COLORS.primary,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6,
          tension: 0.4,
          fill: true,
        },
        {
          label: 'Active Patients',
          data: data.active,
          borderColor: MC_COLORS.success,
          backgroundColor: createGradient(ctx, MC_COLORS.success, 0.08),
          borderWidth: 2.5,
          pointBackgroundColor: MC_COLORS.success,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6,
          tension: 0.4,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: { font: { size: 11 } },
        },
        y: {
          grid: { color: 'rgba(0,0,0,0.04)', drawBorder: false },
          border: { display: false, dash: [4, 4] },
          ticks: { font: { size: 11 }, padding: 8 },
          beginAtZero: true,
        },
      },
      plugins: { legend: { position: 'top', align: 'end' } },
    },
  });
}

/* ---------- Records by Type Bar Chart ---------- */
function initRecordsByTypeChart(canvasId = 'recordsByTypeChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  /* <!-- Flask Dynamic Route: /api/analytics/records-by-type --> */
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Consultation', 'Lab Result', 'Radiology', 'Prescription', 'Surgery', 'Vaccination'],
      datasets: [{
        label: 'Records',
        data: [248, 185, 132, 310, 64, 98],
        backgroundColor: [
          MC_COLORS.primary + 'CC',
          MC_COLORS.success + 'CC',
          MC_COLORS.info    + 'CC',
          MC_COLORS.warning + 'CC',
          MC_COLORS.danger  + 'CC',
          MC_COLORS.purple  + 'CC',
        ],
        borderColor: [
          MC_COLORS.primary,
          MC_COLORS.success,
          MC_COLORS.info,
          MC_COLORS.warning,
          MC_COLORS.danger,
          MC_COLORS.purple,
        ],
        borderWidth: 2,
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: { font: { size: 10 } },
        },
        y: {
          grid: { color: 'rgba(0,0,0,0.04)' },
          border: { display: false },
          ticks: { font: { size: 11 }, padding: 8 },
          beginAtZero: true,
        },
      },
      plugins: { legend: { display: false } },
    },
  });
}

/* ---------- Hospital Status Doughnut Chart ---------- */
function initHospitalStatusChart(canvasId = 'hospitalStatusChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  // Read real data from data attributes set by Flask template
  const active = parseInt(ctx.dataset.active) || 0;
  const pending = parseInt(ctx.dataset.pending) || 0;
  const suspended = parseInt(ctx.dataset.suspended) || 0;
  const rejected = parseInt(ctx.dataset.rejected) || 0;

  const labels = [];
  const data = [];
  const colors = [];

  if (active > 0) { labels.push('Active'); data.push(active); colors.push(MC_COLORS.success); }
  if (pending > 0) { labels.push('Pending'); data.push(pending); colors.push(MC_COLORS.warning); }
  if (suspended > 0) { labels.push('Suspended'); data.push(suspended); colors.push(MC_COLORS.danger); }
  if (rejected > 0) { labels.push('Rejected'); data.push(rejected); colors.push('#b0bec5'); }

  // Fallback if no data
  if (data.length === 0) {
    labels.push('No Data');
    data.push(1);
    colors.push('#e0e0e0');
  }

  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderColor: '#fff',
        borderWidth: 3,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: { position: 'right', labels: { padding: 12 } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed} hospitals`,
          },
        },
      },
    },
  });
}

/* ---------- Weekly Activity Bar Chart ---------- */
function initWeeklyActivityChart(canvasId = 'weeklyActivityChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  // Read real patient/doctor activity data injected by the Flask template
  const dataEl = document.getElementById('weekly-activity-data');
  let activityData = null;
  if (dataEl) {
    try {
      activityData = JSON.parse(dataEl.textContent);
    } catch (e) {
      activityData = null;
    }
  }

  const labels   = (activityData && activityData.labels)   || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const patients = (activityData && activityData.patients) || [];
  const doctors  = (activityData && activityData.doctors)  || [];

  // Normalize to 7 values; missing/empty -> 0
  const weekDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const norm = (arr) => weekDays.map((d, i) => {
    const v = parseInt(arr[i], 10);
    return isNaN(v) ? 0 : v;
  });

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Patients Registered',
          data: norm(patients),
          backgroundColor: MC_COLORS.danger + 'CC',
          borderColor:     MC_COLORS.danger,
          borderWidth: 2,
          borderRadius: 6,
          borderSkipped: false,
        },
        {
          label: 'Doctors Registered',
          data: norm(doctors),
          backgroundColor: MC_COLORS.info + 'CC',
          borderColor:     MC_COLORS.info,
          borderWidth: 2,
          borderRadius: 6,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false }, border: { display: false } },
        y: { grid: { color: 'rgba(0,0,0,0.04)' }, border: { display: false }, beginAtZero: true },
      },
      plugins: { legend: { position: 'top', align: 'end' } },
    },
  });
}

/* ---------- Blockchain Transactions Line Chart ---------- */
function initBlockchainChart(canvasId = 'blockchainChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  /* <!-- Flask Dynamic Route: /api/blockchain/transactions-chart --> */
  const labels = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2,'0')}:00`);
  const data   = [12,8,5,3,4,9,22,45,68,82,75,88,95,78,92,105,88,72,65,58,42,35,28,18];

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Transactions/hr',
        data,
        borderColor: MC_COLORS.success,
        backgroundColor: createGradient(ctx, MC_COLORS.success, 0.15),
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 5,
        tension: 0.4,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { maxRotation: 0, font: { size: 10 } } },
        y: { grid: { color: 'rgba(0,0,0,0.04)' }, border: { display: false }, beginAtZero: true },
      },
      plugins: { legend: { display: false } },
    },
  });
}

/* ---------- Gender Distribution Pie Chart ---------- */
function initGenderChart(canvasId = 'genderChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  /* <!-- Flask Dynamic Route: /api/analytics/gender-distribution --> */
  return new Chart(ctx, {
    type: 'pie',
    data: {
      labels: ['Male', 'Female', 'Other'],
      datasets: [{
        data: [52, 44, 4],
        backgroundColor: [MC_COLORS.primary, MC_COLORS.pink, MC_COLORS.teal],
        borderColor: '#fff',
        borderWidth: 3,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { padding: 12 } },
        tooltip: {
          callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed}%` },
        },
      },
    },
  });
}

/* ---------- Age Distribution Bar Chart ---------- */
function initAgeDistributionChart(canvasId = 'ageDistributionChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  /* <!-- Flask Dynamic Route: /api/analytics/age-distribution --> */
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['0-10', '11-20', '21-30', '31-40', '41-50', '51-60', '61-70', '71+'],
      datasets: [{
        label: 'Patients',
        data: [45, 82, 148, 210, 186, 145, 98, 56],
        backgroundColor: createBarGradients(8),
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { display: false }, border: { display: false } },
        y: { grid: { color: 'rgba(0,0,0,0.04)' }, border: { display: false }, beginAtZero: true },
      },
      plugins: { legend: { display: false } },
    },
  });
}

/* ---------- Doctor Appointments Chart ---------- */
function initAppointmentsChart(canvasId = 'appointmentsChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  /* <!-- Flask Dynamic Route: /api/doctor/appointments-chart --> */
  const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Scheduled',
          data: [8, 12, 10, 15, 9],
          backgroundColor: MC_COLORS.primary + 'CC',
          borderColor: MC_COLORS.primary,
          borderWidth: 2,
          borderRadius: 6,
          borderSkipped: false,
        },
        {
          label: 'Completed',
          data: [7, 11, 9, 14, 8],
          backgroundColor: MC_COLORS.success + 'CC',
          borderColor: MC_COLORS.success,
          borderWidth: 2,
          borderRadius: 6,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false }, border: { display: false } },
        y: { grid: { color: 'rgba(0,0,0,0.04)' }, border: { display: false }, beginAtZero: true },
      },
      plugins: { legend: { position: 'top', align: 'end' } },
    },
  });
}

/* ---------- Record Access Radar Chart ---------- */
function initAccessRadarChart(canvasId = 'accessRadarChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  /* <!-- Flask Dynamic Route: /api/analytics/access-patterns --> */
  return new Chart(ctx, {
    type: 'radar',
    data: {
      labels: ['Emergency', 'Consultation', 'Lab', 'Radiology', 'Pharmacy', 'Surgery'],
      datasets: [
        {
          label: 'This Month',
          data: [65, 85, 72, 58, 90, 45],
          borderColor: MC_COLORS.primary,
          backgroundColor: MC_COLORS.primary + '20',
          borderWidth: 2,
          pointBackgroundColor: MC_COLORS.primary,
        },
        {
          label: 'Last Month',
          data: [55, 72, 60, 48, 78, 38],
          borderColor: MC_COLORS.secondary,
          backgroundColor: MC_COLORS.secondary + '20',
          borderWidth: 2,
          pointBackgroundColor: MC_COLORS.secondary,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          beginAtZero: true,
          grid: { color: 'rgba(0,0,0,0.06)' },
          ticks: { font: { size: 10 }, stepSize: 20 },
          pointLabels: { font: { size: 11, family: "'Poppins', sans-serif" } },
        },
      },
      plugins: { legend: { position: 'top' } },
    },
  });
}

/* ---------- Mini Sparkline ---------- */
function initSparkline(canvasId, data, color = MC_COLORS.primary) {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map((_, i) => i),
      datasets: [{
        data,
        borderColor: color,
        backgroundColor: color + '20',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.4,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        x: { display: false },
        y: { display: false, beginAtZero: false },
      },
      events: [],
    },
  });
}

/* ---------- Gradient Helper ---------- */
function createGradient(ctx, color, alpha = 0.2) {
  const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0,   color + Math.round(alpha * 255).toString(16).padStart(2,'0'));
  gradient.addColorStop(1,   color + '00');
  return gradient;
}

function createBarGradients(count) {
  const palette = [
    MC_COLORS.primary, MC_COLORS.secondary, MC_COLORS.success,
    MC_COLORS.warning, MC_COLORS.danger,    MC_COLORS.purple,
    MC_COLORS.teal,    MC_COLORS.info,
  ];
  return Array.from({ length: count }, (_, i) => palette[i % palette.length] + 'CC');
}

/* ---------- Animate Counter ---------- */
function animateCounter(el, target, duration = 1200, prefix = '', suffix = '') {
  const start   = 0;
  const step    = target / (duration / 16);
  let   current = start;

  const timer = setInterval(() => {
    current += step;
    if (current >= target) {
      current = target;
      clearInterval(timer);
    }
    el.textContent = prefix + Math.floor(current).toLocaleString() + suffix;
  }, 16);
}

function initCounterAnimations() {
  const counters = document.querySelectorAll('[data-count]');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !entry.target.dataset.animated) {
        entry.target.dataset.animated = '1';
        animateCounter(
          entry.target,
          parseInt(entry.target.dataset.count),
          1000,
          entry.target.dataset.prefix || '',
          entry.target.dataset.suffix || '',
        );
      }
    });
  }, { threshold: 0.3 });

  counters.forEach(el => observer.observe(el));
}

/* ---------- Blockchain Live Updates ---------- */
function initBlockchainLiveUpdate() {
  const blockCount   = document.getElementById('live-block-count');
  const txCount      = document.getElementById('live-tx-count');
  const networkStatus= document.getElementById('live-network-status');

  if (!blockCount && !txCount) return;

  /* <!-- Blockchain Status: Replace with WebSocket or /api/blockchain/status --> */
  let blocks = 18432;
  let txs    = 94218;

  setInterval(() => {
    const newTx = Math.floor(Math.random() * 5) + 1;
    txs += newTx;

    if (Math.random() > 0.7) blocks++;

    if (blockCount) blockCount.textContent = blocks.toLocaleString();
    if (txCount)    txCount.textContent    = txs.toLocaleString();

    // Flash update
    [blockCount, txCount].forEach(el => {
      if (!el) return;
      el.style.color = 'var(--success)';
      setTimeout(() => { el.style.color = ''; }, 600);
    });
  }, 3000);
}

/* ---------- Analytics Data Reader ---------- */
function getAnalyticsData() {
  const el = document.getElementById('analytics-data');
  if (!el) return null;
  try {
    return JSON.parse(el.textContent);
  } catch (e) {
    return null;
  }
}

/* ---------- Hospital Registrations Over Time (Line) ---------- */
function initRegistrationChart(canvasId = 'registrationChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  const data = getAnalyticsData();
  const labels = (data && data.reg_months) || [];
  const values = (data && data.reg_counts) || [];

  if (labels.length === 0) {
    labels.push('No Data');
    values.push(0);
  }

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Hospitals Registered',
        data: values,
        borderColor: MC_COLORS.primary,
        backgroundColor: createGradient(ctx, MC_COLORS.primary),
        borderWidth: 2.5,
        pointBackgroundColor: MC_COLORS.primary,
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.4,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: { font: { size: 11 } },
        },
        y: {
          grid: { color: 'rgba(0,0,0,0.04)', drawBorder: false },
          border: { display: false, dash: [4, 4] },
          ticks: { font: { size: 11 }, padding: 8 },
          beginAtZero: true,
        },
      },
      plugins: { legend: { position: 'top', align: 'end' } },
    },
  });
}

/* ---------- Hospital Status Distribution (Doughnut) ---------- */
function initStatusChart(canvasId = 'statusChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  const data = getAnalyticsData();
  const dist = (data && data.status_distribution) || [];

  let labels = [];
  let values = [];
  let colors = [];

  dist.forEach(item => {
    if (item.value > 0) {
      labels.push(item.label);
      values.push(item.value);
      colors.push(item.color);
    }
  });

  if (values.length === 0) {
    labels.push('No Data');
    values.push(1);
    colors.push('#e0e0e0');
  }

  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderColor: '#fff',
        borderWidth: 3,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: { position: 'right', labels: { padding: 12 } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed} hospitals`,
          },
        },
      },
    },
  });
}

/* ---------- Hospitals by City (Bar) ---------- */
function initCityChart(canvasId = 'cityChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  const data = getAnalyticsData();
  const labels = (data && data.cities) || [];
  const values = (data && data.city_counts) || [];

  if (labels.length === 0) {
    labels.push('No Data');
    values.push(0);
  }

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Hospitals',
        data: values,
        backgroundColor: MC_COLORS.info + 'CC',
        borderColor: MC_COLORS.info,
        borderWidth: 2,
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { display: false }, border: { display: false } },
        y: { grid: { color: 'rgba(0,0,0,0.04)' }, border: { display: false }, beginAtZero: true },
      },
      plugins: { legend: { display: false } },
    },
  });
}

/* ---------- Registered Users by Role (Doughnut) ---------- */
function initRoleChart(canvasId = 'roleChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  const data = getAnalyticsData();
  const roles = (data && data.roles) || [];
  const labels = roles.map(r => r[0]);
  const values = roles.map(r => r[1]);
  const roleColors = [MC_COLORS.primary, MC_COLORS.warning, MC_COLORS.pink, MC_COLORS.success];

  if (values.length === 0 || values.every(v => v === 0)) {
    labels.push('No Data');
    values.push(1);
  }

  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: roleColors.slice(0, labels.length),
        borderColor: '#fff',
        borderWidth: 3,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: { position: 'bottom', labels: { padding: 12 } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed} users`,
          },
        },
      },
    },
  });
}

/* ---------- Analytics Period Filter ---------- */
function onAnalyticsPeriodChange(select) {
  const value = select ? select.value : 'all';
  const url = new URL(window.location.href);
  if (value === 'all') {
    url.searchParams.delete('period');
  } else {
    url.searchParams.set('period', value);
  }
  window.location.href = url.toString();
}

/* ---------- Export Analytics Report (CSV) ---------- */
function exportAnalyticsReport() {
  const data = getAnalyticsData() || {};
  const rows = [];

  // Header
  rows.push(['MediChain System Analytics Report']);
  rows.push(['Generated', new Date().toLocaleString()]);
  rows.push([]);

  // KPI summary
  rows.push(['Metric', 'Value']);
  rows.push(['Total Hospitals', document.querySelector('.stat-card.primary .stat-value')?.textContent || '0']);
  rows.push(['Approved Hospitals', document.querySelector('.stat-card.success .stat-value')?.textContent || '0']);
  rows.push(['Pending Hospitals', document.querySelector('.stat-card.warning .stat-value')?.textContent || '0']);
  rows.push(['Rejected Hospitals', document.querySelector('.stat-card.danger .stat-value')?.textContent || '0']);
  rows.push(['Doctors', data.roles ? (data.roles.find(r => r[0] === 'Doctors') || [0, 0])[1] : 0]);
  rows.push(['Hospital Admins', data.roles ? (data.roles.find(r => r[0] === 'Hospital Admins') || [0, 0])[1] : 0]);
  rows.push(['Patients', data.roles ? (data.roles.find(r => r[0] === 'Patients') || [0, 0])[1] : 0]);
  rows.push([]);

  // Registrations over time
  rows.push(['Registrations Over Time']);
  rows.push(['Month', 'Hospitals']);
  const months = data.reg_months || [];
  const counts = data.reg_counts || [];
  months.forEach((m, i) => rows.push([m, counts[i] ?? 0]));
  rows.push([]);

  // Status distribution
  rows.push(['Hospital Status Distribution']);
  rows.push(['Status', 'Count']);
  (data.status_distribution || []).forEach(s => rows.push([s.label, s.value]));
  rows.push([]);

  // City distribution
  rows.push(['Hospitals by City']);
  rows.push(['City', 'Count']);
  const cities = data.cities || [];
  const cityCounts = data.city_counts || [];
  cities.forEach((c, i) => rows.push([c, cityCounts[i] ?? 0]));
  rows.push([]);

  // Recent hospitals table
  const table = document.getElementById('mc-table');
  if (table) {
    rows.push(['Recently Registered Hospitals']);
    const headerCells = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
    rows.push(headerCells);
    table.querySelectorAll('tbody tr').forEach(tr => {
      const cells = Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim().replace(/\s+/g, ' '));
      rows.push(cells);
    });
  }

  // Build CSV string
  const csv = rows
    .map(row => row.map(cell => {
      const s = String(cell ?? '');
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    }).join(','))
    .join('\r\n');

  // Trigger download
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `medichain-analytics-report-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
}

/* ---------- Dashboard Init ---------- */
document.addEventListener('DOMContentLoaded', function () {
  initChartDefaults();

  // Init all charts that exist on the current page
  initPatientGrowthChart();
  initRecordsByTypeChart();
  initHospitalStatusChart();
  initWeeklyActivityChart();
  initBlockchainChart();
  initGenderChart();
  initAgeDistributionChart();
  initAppointmentsChart();
  initAccessRadarChart();

  // Analytics charts (only on analytics page)
  initRegistrationChart();
  initStatusChart();
  initCityChart();
  initRoleChart();

  // Counter animations
  initCounterAnimations();

  // Blockchain live updates (only on blockchain monitor page)
  if (document.getElementById('live-block-count')) {
    initBlockchainLiveUpdate();
  }

  // Table features
  if (typeof MediChain !== 'undefined') {
    MediChain.initTableSort();
    MediChain.initPagination({ pageSize: 10 });
  }
});

/* ---------- Expose ---------- */
window.MCDashboard = {
  initPatientGrowthChart,
  initRecordsByTypeChart,
  initHospitalStatusChart,
  initWeeklyActivityChart,
  initBlockchainChart,
  initGenderChart,
  initAgeDistributionChart,
  initAppointmentsChart,
  initSparkline,
  animateCounter,
  MC_COLORS,
};
