import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'E_learning.settings')
import django
django.setup()
from django.test import Client
from django.urls import reverse
c = Client()
r = c.get(reverse('register'))
html = r.content.decode()
print('auth-card:', 'auth-card' in html)
print('id_role:', 'id="id_role"' in html)
print('name=role count:', html.count('name="role"'))
print('Account type:', 'Account type' in html)
print('role-toggle:', 'role-toggle' in html)
print('len:', len(html))
open('scratch/reg_rendered.html','w',encoding='utf-8').write(html)
print('saved')
