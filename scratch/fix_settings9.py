path = r'd:\Grayphite\Django_learning\E_learning\settings.py'
with open(path, 'rb') as f:
    content = f.read()

CRLF = b'\r\n'
SSP = b"'testserver',"          # the bad line
host_strip = b'host.strip()'   # the good first item
for_host = b"for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')"
if_host = b'if host.strip()'
close_bracket = b']'



old = b'ALLOWED_HOSTS = [' + CRLF + b'    ' + SSP + CRLF + b'    ' + host_strip + CRLF + b'    ' + for_host + CRLF + b'    ' + if_host + CRLF + CRLF + close_bracket + CRLF

print('Old block found:', old in content)

if old in content:
    correct_testserver_line = b"ALLOWED_HOSTS = [" + CRLF + b"    '" + b"testserver" + b"'," + CRLF
    correct_for = b"    " + for_host + CRLF + b"    " + if_host + CRLF + CRLF + close_bracket + CRLF

    content = content.replace(old, correct_testserver_line + correct_for)
    with open(path, 'wb') as f:
        f.write(content)
    print('Fixed: removed duplicate host.strip() line')
else:
    print('Old block not found - dumping content')
    idx = content.find(b'ALLOWED_HOSTS')
    print(repr(content[idx:idx+200]))
