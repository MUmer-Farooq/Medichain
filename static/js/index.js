document.addEventListener('DOMContentLoaded', () => {

  // Initialize AOS
  AOS.init();

  // Navbar Scroll Effect
  const navbar = document.getElementById('lp-navbar');

  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.classList.toggle('scrolled', window.scrollY > 20);
    });
  }

});