# -*- coding: utf-8 -*-
import os

path = r'd:\Grayphite\Django_learning\E_learning\settings.py'
with open(path, 'rb') as f:
    content = f.read()

old = b"""ALLOWED_HOSTS = [
    'testserver',
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')
    if host.strip()
]
"""

new = b"""ALLOWED_HOSTS = [
    'testserver',
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')
    if host.strip()
]
"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'wb') as f:
        f.write(content)
    print('Fixed (CRLF)')
else:
    print('Old block not found')
    # Try with \n
    old2 = old.replace(b'\r\n', b'\n')
    if old2 in content:
        content = content.replace(old2, new.replace(b'\r\n', b'\n'))
        with open(path, 'wb') as f:
            f.write(content)
        print('Fixed (LF)')
    else:
        print('Still not found - dumping content around ALLOWED_HOSTS')
        idx = content.find(b'ALLOWED_HOSTS')
        print(repr(content[idx:idx+300]))
