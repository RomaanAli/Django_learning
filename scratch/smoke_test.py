# -*- coding: utf-8 -*-
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'E_learning.settings')
import django
django.setup()

from django.test import Client
from django.urls import reverse

client = Client()

# Test login page renders
resp = client.get(reverse('login'))
print('Login page status:', resp.status_code)
content = resp.content.decode()
print('Has auth-card:', 'auth-card' in content)
print('Has role-toggle:', 'role-toggle' in content)
print('Has role-toggle-hint:', 'role-toggle-hint' in content)
print('Has role input count:', content.count('name="role"'))

# Test register page renders
resp = client.get(reverse('register'))
print('Register page status:', resp.status_code)
content = resp.content.decode()
print('Has role field:', 'id="id_role"' in content)
print('Has role-toggle:', 'role-toggle' in content)
print('Has Account type label:', 'Account type' in content)
print('Has hidden role field:', content.count('name="role"') >= 2)
