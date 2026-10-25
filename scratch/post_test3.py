import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'E_learning.settings')
import django
django.setup()
from django.test import Client
from django.urls import reverse

c = Client()
# Instructor registration
resp = c.post(reverse('register'), {
    'username': 'inst123',
    'first_name': 'Inst',
    'last_name': 'Ructor',
    'email': 'inst123@example.com',
    'password1': 'StrongPass123!',
    'password2': 'StrongPass123!',
    'role': 'instructor',
})
print('Instructor reg status:', resp.status_code, getattr(resp, 'url', ''))
from django.contrib.auth import get_user_model
U = get_user_model()
u = U.objects.filter(username='inst123').first()
print('Instructor user:', u is not None, getattr(u, 'role', None))

# Tampered role admin should be invalid
c2 = Client()
resp3 = c2.post(reverse('register'), {
    'username': 'bad123',
    'first_name': 'Bad',
    'last_name': 'User',
    'email': 'bad123@example.com',
    'password1': 'StrongPass123!',
    'password2': 'StrongPass123!',
    'role': 'admin',
})
print('Admin role reg status:', resp3.status_code, getattr(resp3, 'url', ''))
print('Bad user created:', U.objects.filter(username='bad123').exists())
