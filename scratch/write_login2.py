from pathlib import Path

path = Path(r'd:\Grayphite\Django_learning\accounts\templates\accounts\login.html')

content = """{% load socialaccount %}

{% extends 'accounts/auth_base.html' %}

{% block title %}Login | E-Learning{% endblock %}

{% block header_title %}Welcome back{% endblock %}
{% block header_subtitle %}Sign in to your account to continue{% endblock %}

{% block form_action %}{% url 'login' %}{% endblock %}

{% block fields %}
{% if form.non_field_errors %}
<div class="field-group"><div class="field-error">{{ form.non_field_errors|join:', ' }}</div></div>
{% endif %}

<div class="field-group">
  <label for="{{ form.username.id_for_label }}">Username</label>
  {{ form.username }}
  {% if form.username.errors %}
  <div class="field-error">{{ form.username.errors|join:', ' }}</div>
  {% endif %}
</div>

<div class="field-group">
  <label for="{{ form.password.id_for_label }}">Password</label>
  <input
    type="password"
    id="{{ form.password.id_for_label }}"
    name="{{ form.password.name }}"
    autocomplete="current-password"
  >
  <button type="button" class="toggle-password" aria-label="Toggle password visibility">👁️</button>
  {% if form.password.errors %}
  <div class="field-error">{{ form.password.errors|join:', ' }}</div>
  {% endif %}
</div>
{% endblock %}

{% block content %}
{% if google_configured %}
<div class="google-auth">
  <a class="btn btn-google" href="{% provider_login_url 'google' %}">
    <span class="google-icon">G</span>
    Continue with Google
  </a>
</div>
{% endif %}

<form class="auth-form login-form" method="post" action="{% url 'login' %}" novalidate>
  {% csrf_token %}
  <input type="hidden" name="next" value="{{ request.GET.next }}">

  {% if messages %}
  <div class="messages">
    {% for message in messages %}
    <div class="alert alert-{{ message.tags }}" role="alert">
      {{ message }}
      <button type="button" class="alert-close" aria-label="Close" data-message-close>&times;</button>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <div class="field-group">
    <label for="{{ form.username.id_for_label }}">Username</label>
    {{ form.username }}
    {% if form.username.errors %}
    <div class="field-error">{{ form.username.errors|join:', ' }}</div>
    {% endif %}
  </div>

  <div class="field-group">
    <label for="{{ form.password.id_for_label }}">Password</label>
    <input
      type="password"
      id="{{ form.password.id_for_label }}"
      name="{{ form.password.name }}"
      autocomplete="current-password"
    >
    <button type="button" class="toggle-password" aria-label="Toggle password visibility">👁️</button>
    {% if form.password.errors %}
    <div class="field-error">{{ form.password.errors|join:', ' }}</div>
    {% endif %}
  </div>

  <div class="role-toggle-hint">
    <strong>Student account</strong>
    <span>Use this for taking courses.</span>
  </div>

  <div class="role-toggle" role="radiogroup" aria-label="Account type">
    <button
      type="button"
      class="role-btn"
      data-role="student"
      aria-checked="true"
      aria-selected="true"
      tabindex="0"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
      <span class="role-label">Student</span>
      <span class="role-badge">Default</span>
    </button>
    <button
      type="button"
      class="role-btn"
      data-role="instructor"
      aria-checked="false"
      aria-selected="false"
      tabindex="-1"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
        <path d="M6 12v5c3 1.5 5.5 3 8 3s5-1.5 8-3v-5"/>
      </svg>
      <span class="role-label">Instructor</span>
      <span class="role-badge">Apply now</span>
    </button>
  </div>

  <button class="btn btn-submit" type="submit">
    <span class="btn-text">Login</span>
    <span class="btn-spinner"></span>
  </button>
</form>

<footer class="form-footer">
  <p>
    Don't have an account? <a href="{% url 'register' %}">Register here</a>
  </p>
</footer>
{% endblock %}

{% block extra_js %}
<script>
  // Toggle password visibility.
  document.querySelector('.toggle-password').addEventListener('click', function () {
    var input = document.getElementById("{{ form.password.id_for_label }}");
    var type = input.getAttribute('type') === 'password' ? 'text' : 'password';
    input.setAttribute('type', type);
    this.setAttribute('aria-label', type === 'password' ? 'Hide password' : 'Show password');
  });
</script>
{% endblock %}
"""
path.write_text(content, encoding='utf-8')
print('login.html written, len=', len(content))
