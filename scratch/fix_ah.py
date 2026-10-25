import os
path = r'd:\Grayphite\Django_learning\E_learning\settings.py'
with open(path, 'rb') as f:
    c = f.read()

old = b"ALLOWED_HOSTS = [\r\n    'testserver',\r\n\r\n    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')\r\n\r\n    if host.strip()\r\n]\r\n\r\n    \r\n\r\n\r\nrender_hostname = "

new = b"ALLOWED_HOSTS = [\r\n    'testserver',\r\n    *[\r\n        host.strip()\r\n        for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')\r\n        if host.strip()\r\n    ],\r\n]\r\n\r\nrender_hostname = "

assert old in c, 'old not found'
c = c.replace(old, new)
with open(path, 'wb') as f:
    f.write(c)
print('done')
