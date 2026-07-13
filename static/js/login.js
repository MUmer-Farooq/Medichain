// ===============================
// MediChain Global JavaScript
// ===============================

// Redirect map
const roleRedirects = {
  admin: 'system-admin/dashboard.html',
  hospital: 'hospital-admin/dashboard.html',
  doctor: 'doctor/dashboard.html',
  patient: 'patient/dashboard.html',
};

// Role Selection
function selectRole(el, role) {
  document.querySelectorAll('.role-tab').forEach(tab => {
    tab.classList.remove('active');
  });

  el.classList.add('active');
  document.getElementById('roleInput').value = role;
}


// Initialize form validation for login
document.addEventListener('DOMContentLoaded', function() {
  if (typeof window.MediChain !== 'undefined' && window.MediChain.initFormValidation) {
    window.MediChain.initFormValidation('loginForm');
  }
});