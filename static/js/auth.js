/**
 * Auth page UX: role toggle (radios), password show/hide, submit loading state,
 * and dynamic heading/copy swap for the register page.
 */
(function () {
  'use strict';

  // ---------- Password show/hide ----------
  var EYE_OPEN = '<svg class="eye-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>';
  var EYE_CLOSED = '<svg class="eye-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>';

  document.querySelectorAll('.toggle-password').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var wrap = btn.closest('.password-wrap') || btn.parentElement;
      var input = wrap ? wrap.querySelector('input') : null;
      if (!input) {
        var prev = btn.previousElementSibling;
        while (prev && prev.tagName !== 'INPUT') prev = prev.previousElementSibling;
        input = prev;
      }
      if (!input) return;
      var isPassword = input.getAttribute('type') === 'password';
      input.setAttribute('type', isPassword ? 'text' : 'password');
      btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
      btn.innerHTML = isPassword ? EYE_CLOSED : EYE_OPEN;
    });
  });

  // ---------- Submit loading state ----------
  document.querySelectorAll('.auth-form').forEach(function (form) {
    form.addEventListener('submit', function () {
      var btn = form.querySelector('.btn-submit');
      if (btn) btn.classList.add('loading');
    });
  });

  // ---------- Role toggle (register page) ----------
  var toggle = document.querySelector('[data-role-toggle]');
  if (!toggle) return;

  var radios = Array.prototype.slice.call(toggle.querySelectorAll('input[type="radio"]'));
  var titleEl = document.querySelector('.auth-title');
  var subtitleEl = document.querySelector('.auth-subtitle');
  var hintTitle = document.getElementById('role-hint-title');
  var hintDetail = document.getElementById('role-hint-detail');
  var card = document.querySelector('.auth-card');

  var copy = {
    student: { title: 'Create a Student Account', subtitle: 'browse courses and enroll.', hint: 'Student account', detail: 'Browse courses and enroll.', card: 'auth-card--student' },
    instructor: { title: 'Create an Instructor Account', subtitle: 'create and manage your courses.', hint: 'Instructor account', detail: 'Create and manage your courses.', card: 'auth-card--instructor' }
  };

  function applyRole(role) {
    if (!copy[role]) role = 'student';
    var c = copy[role];

    if (titleEl) titleEl.textContent = c.title;
    if (subtitleEl) subtitleEl.textContent = c.subtitle;
    if (hintTitle) hintTitle.textContent = c.hint;
    if (hintDetail) hintDetail.textContent = c.detail;
    if (card) {
      card.classList.remove('auth-card--student', 'auth-card--instructor');
      card.classList.add(c.card);
    }
    document.title = (role === 'instructor' ? 'Register as Instructor' : 'Register as Student') + ' — E-Learning';

    // sync checked state (radios already handle value submission)
    radios.forEach(function (r) {
      r.checked = (r.value === role);
    });
  }

  radios.forEach(function (r) {
    r.addEventListener('change', function () {
      if (r.checked) applyRole(r.value);
    });
  });

  // initial
  var checked = toggle.querySelector('input[type="radio"]:checked');
  applyRole(checked ? checked.value : 'student');
})();
