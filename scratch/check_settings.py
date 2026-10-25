# -*- coding: utf-8 -*-
import os

path = r'd:\Grayphite\Django_learning\E_learning\settings.py'
with open(path, 'rb') as f:
    content = f.read()

# Build old block using bytes concat
CRLF = b'\r\n'
SSP = b"'testserver',"
host_strip = b'host.strip()'
for_host = b"for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')"
if_host = b'if host.strip()'
close_bracket = b']'

old = b'ALLOWED_HOSTS = [' + CRLF + b'    ' + SSP + CRLF + b'    ' + host_strip + CRLF + b'    ' + for_host + CRLF + b'    ' + if_host + CRLF + CRLF + close_bracket + CRLF

print('Old block found:', old in content)

if old in content:
    content = content.replace(old, old)
    with open(path, 'wb') as f:
        f.write(content)
    print('Fixed - block unchanged (already correct)')
else:
    print('Old block not found')
    print('--- content around ALLOWED_HOSTS ---')
    idx = content.find(b'ALLOWED_HOSTS')
    print(content[idx:idx+200])
