# -*- coding: utf-8 -*-
path = r'd:\Grayphite\Django_learning\E_learning\settings.py'
with open(path, 'rb') as f:
    content = f.read()

CRLF = b'\r\n'
indent = b'    '
SSP = b"'testserver'," + CRLF
host_strip = indent + b'host.strip()' + CRLF
for_host = indent + b"for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')" + CRLF
if_host = indent + b'if host.strip()' + CRLF
close_bracket = CRLF + b']' + CRLF

old = b'ALLOWED_HOSTS = [' + CRLF + indent + SSP + host_strip + for_host + if_host + CRLF + close_bracket

print('Old block found:', old in content)

if old in content:
    correct_testserver = indent + b"'testserver'," + CRLF
    new = b'ALLOWED_HOSTS = [' + CRLF + indent + correct_testserver + for_host + if_host + CRLF + close_bracket
    content = content.replace(old, new)
    with open(path, 'wb') as f:
        f.write(content)
    print('Fixed!')
else:
    print('Old block NOT found')
