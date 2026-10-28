path = r'd:\Grayphite\Django_learning\accounts\templates\accounts\register.html'
content = """{% extends 'accounts/auth_base.html' %}

{% load socialaccount %}

{% block title %}Register — E-learning{% endblock %}

{% block header_title %}Create your account{% endblock %}
{% block header_subtitle %}Join the platform as a Student or Instructor{% endblock %}

{% block form_action %}{% url 'register' %}{% endblock %}

{% block submit_text %}Register{% endblock %}

{% block footer %}
<p>Already have an account? <a href="{% url 'login' %}">Sign in</a></p>
{% endblock %}

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
  <label for="{{ form.first_name.id_for_label }}">First name</label>
  {{ form.first_name }}
  {% if form.first_name.errors %}
  <div class="field-error">{{ form.first_name.errors|join:', ' }}</div>
  {% endif %}
</div>

<div class="field-group">
  <label for="{{ form.last_name.id_for_label }}">Last name</label>
  {{ form.last_name }}
  {% if form.last_name.errors %}
  <div class="field-error">{{ form.last_name.errors|join:', ' }}</div>
  {% endif %}
</div>

<div class="field-group">
  <label for="{{ form.email.id_for_label }}">Email</label>
  {{ form.email }}
  {% if form.email.errors %}
  <div class="field-error">{{ form.email.errors|join:', ' }}</div>
  {% endif %}
</div>

<div class="field-group">
  <label for="{{ form.password1.id_for_label }}">Password</label>
  <input
    type="password"
    id="{{ form.password1.id_for_label }}"
    name="{{ form.password1.name }}"
    autocomplete="new-password"
  >
  <button type="button" class="toggle-password" aria-label="Toggle password visibility">👁️</button>
  {% if form.password1.errors %}
  <div class="field-error">{{ form.password1.errors|join:', ' }}</div>
  {% endif %}
</div>

<div class="field-group">
  <label for="{{ form.password2.id_for_label }}">Confirm password</label>
  <input
    type="password"
    id="{{ form.password2.id_for_label }}"
    name="{{ form.password2.name }}"
    autocomplete="new-password"
  >
  <button type="button" class="toggle-password" aria-label="Toggle password visibility">👁️</button>
  {% if form.password2.errors %}
  <div class="field-error">{{ form.password2.errors|join:', ' }}</div>
  {% endif %}
</div>

<div class="field-group">
  <label for="{{ form.role.id_for_label }}">Account type</label>
  {{ form.role }}
  {% if form.role.errors %}
  <div class="field-error">{{ form.role.errors|join:', ' }}</div>
  {% endif %}
</div>
{% endblock %}

{% block extra_js %}
<script>
  document.querySelectorAll('.toggle-password').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var target = btn.previousElementSibling;
      while (target && target.tagName !== 'INPUT') { target = target.previousElementSibling; }
      if (!target) return;
      var type = target.getAttribute('type') === 'password' ? 'text' : 'password';
      target.setAttribute('type', type);
      btn.setAttribute('aria-label', type === 'password' ? 'Hide password' : 'Show password');
    });
  });
</script>
{% endblock %}
"""
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('written', len(content))
