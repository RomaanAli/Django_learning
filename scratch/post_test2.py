import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'E_learning.settings')
import django
django.setup()
from django.test import Client
from django.urls import reverse

c = Client()
resp = c.post(reverse('register'), {
    'username': 'testuser123',
    'first_name': 'Test',
    'last_name': 'User',
    'email': 'testuser123@example.com',
    'password1': 'StrongPass123!',
    'password2': 'StrongPass123!',
    'role': 'student',
})
print('Register POST status:', resp.status_code, getattr(resp, 'url', ''))
from django.contrib.auth import get_user_model
U = get_user_model()
u = U.objects.filter(username='testuser123').first()
print('User created:', u is not None, getattr(u, 'role', None), getattr(u, 'is_active', None))

resp2 = c.post(reverse('login'), {
    'username': 'testuser123',
    'password': 'StrongPass123!',
})
print('Login POST status:', resp2.status_code, getattr(resp2, 'url', ''))
