path = r'd:\Grayphite\Django_learning\E_learning\settings.py'

with open(path, 'rb') as f:
    content = f.read()

CRLF = b'\r\n'

broken = b'ALLOWED_HOSTS = [\r\n    ' + b"'testserver'," + CRLF + CRLF
broken += CRLF + b'    for host in os.environ.get(' + b"'DJANGO_ALLOWED_HOSTS'" + b', ' + b"'localhost,127.0.0.1,.onrender.com'" + b').split(' + b"'" + b',' + b"'" + b')' + CRLF + CRLF
broken += CRLF + b'    if host.strip()' + CRLF + b']' + CRLF

fixed = b'ALLOWED_HOSTS = [\r\n    ' + b"'testserver'," + CRLF
fixed += CRLF + b'    for host in os.environ.get(' + b"'DJANGO_ALLOWED_HOSTS'" + b', ' + b"'localhost,127.0.0.1,.onrender.com'" + b').split(' + b"'" + b',' + b"'" + b')' + CRLF + CRLF
fixed += CRLF + b'    if host.strip()' + CRLF + b']' + CRLF

print('Broken found:', broken in content)
if broken in content:
    content = content.replace(broken, fixed)
    with open(path, 'wb') as f:
        f.write(content)
    print('FIXED!')
else:
    print('Broken block NOT found')
