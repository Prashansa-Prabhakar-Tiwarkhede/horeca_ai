// Smart HORECA AI — Main JavaScript

// Live clock
function updateClock() {
  const el = document.getElementById('clock');
  if (el) {
    const now = new Date();
    el.textContent = now.toLocaleString('en-IN', {
      weekday: 'short', day: '2-digit', month: 'short',
      hour: '2-digit', minute: '2-digit'
    });
  }
}
updateClock();
setInterval(updateClock, 1000);

// Sidebar toggle (mobile)
function toggleSidebar() {
  document.getElementById('sidebar')?.classList.toggle('open');
}

// Close sidebar on outside click (mobile)
document.addEventListener('click', (e) => {
  const sb = document.getElementById('sidebar');
  const toggle = document.querySelector('.menu-toggle');
  if (sb && sb.classList.contains('open')) {
    if (!sb.contains(e.target) && e.target !== toggle) {
      sb.classList.remove('open');
    }
  }
});

// Auto-dismiss alerts
document.querySelectorAll('.alert').forEach(el => {
  setTimeout(() => {
    el.style.transition = 'opacity 0.4s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 400);
  }, 4000);
});

// Number counter animation for KPI cards
function animateCounters() {
  document.querySelectorAll('.kpi-value').forEach(el => {
    const target = parseFloat(el.textContent);
    if (isNaN(target)) return;
    let start = 0;
    const duration = 800;
    const step = target / (duration / 16);
    const timer = setInterval(() => {
      start = Math.min(start + step, target);
      el.textContent = Number.isInteger(target)
        ? Math.round(start)
        : start.toFixed(1);
      if (start >= target) clearInterval(timer);
    }, 16);
  });
}
window.addEventListener('load', animateCounters);
