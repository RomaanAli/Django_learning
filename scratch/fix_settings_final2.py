# -*- coding: utf-8 -*-
path = r'd:\Grayphite\Django_learning\E_learning\settings.py'

with open(path, 'rb') as f:
    content = f.read()

# Extract the exact broken block from the file
idx = content.find(b'ALLOWED_HOSTS')
idx2 = content.find(b'for host in os.environ.get', idx)
end = content.find(b']', idx2)
broken = content[idx:end + 1]
print('Broken block:', repr(broken))
print('Length:', len(broken))

CRLF = b'\r\n'

# Build the correct block
fixed = b'ALLOWED_HOSTS = [' + CRLF + b'    ' + b"'testserver'," + CRLF
fixed += CRLF + b'    for host in os.environ.get(' + b"'DJANGO_ALLOWED_HOSTS'" + b', ' + b"'localhost,127.0.0.1,.onrender.com'" + b').split(' + b"'" + b',' + b"'" + b')' + CRLF
fixed += CRLF + b'    if host.strip()' + CRLF + b']' + CRLF

print('Broken found:', broken in content)
if broken in content:
    content = content.replace(broken, fixed)
    with open(path, 'wb') as f:
        f.write(content)
    print('FIXED!')
else:
    print('Broken block NOT found in content')
