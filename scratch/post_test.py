import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'E_learning.settings')
import django
django.setup()
from django.test import Client
from django.urls import reverse

c = Client()
# Register
resp = c.post(reverse('register'), {
    'username': 'testuser123',
    'first_name': 'Test',
    'last_name': 'User',
    'email': 'testuser123@example.com',
    'password1': 'StrongPass123!',
    'password2': 'StrongPass123!',
    'role': 'student',
})
print('Register POST status:', resp.status_code, resp.url if hasattr(resp,'url') else '')
# Check user created
from django.contrib.auth import get_user_model
U = get_user_model()
u = U.objects.filter(username='testuser123').first()
print('User created:', u is not None, getattr(u,'role',None), getattr(u,'is_active',None))
PYEOF
print('done')
