(function () {
  function initHalfDaySection(section) {
    const toggle = section.querySelector('.half-day-toggle');
    const sessionWrap = section.querySelector('.half-day-session');
    const startInput = section.closest('form')?.querySelector('.half-day-start');
    const endInput = section.closest('form')?.querySelector('.half-day-end');
    if (!toggle || !sessionWrap) return;

    function sync() {
      const on = toggle.checked;
      sessionWrap.classList.toggle('hidden', !on);
      if (on && startInput && endInput && startInput.value) {
        endInput.value = startInput.value;
        endInput.readOnly = true;
      } else if (endInput) {
        endInput.readOnly = false;
      }
      if (!on) {
        sessionWrap.querySelectorAll('input[type="radio"]').forEach((r) => {
          r.checked = false;
        });
      }
    }

    toggle.addEventListener('change', sync);
    if (startInput) startInput.addEventListener('change', sync);
    sync();
  }

  document.querySelectorAll('.half-day-section').forEach(initHalfDaySection);

  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', (e) => {
      const toggle = form.querySelector('.half-day-toggle');
      if (!toggle || !toggle.checked) return;
      const selected = form.querySelector('input[name="half_day_session"]:checked');
      if (!selected) {
        e.preventDefault();
        alert('Please choose Morning or Afternoon for half-day leave.');
      }
    });
  });
})();
