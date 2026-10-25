# -*- coding: utf-8 -*-
path = r'd:\Grayphite\Django_learning\E_learning\settings.py'
with open(path, 'rb') as f:
    content = f.read()

CRLF = b'\r\n'
SSP = b"'testserver',"          # the bad line
host_strip = b'host.strip()'   # the good first item
for_host = b"for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')"
if_host = b'if host.strip()'
close_bracket = b']'

# Old block: list starting with testserver (should be replaced by this line)
# We want to replace the block with:
# ALLOWED_HOSTS = [
#     'testserver',
#     host.strip()
#     for host in ...
#     if host.strip()
# ]
# So `testserver` stays, and we remove the duplicated host.strip() line.

# The broken pattern: after ALLOWED_HOSTS = [, we have testserver, then host.strip()
# We want: testserver, then host.strip() (comprehension)

# Pattern to replace: the list starting with testserver that has a SEPARATE host.strip() line
# Old: ALLOWED_HOSTS = [\r\n    'testserver',\r\n    host.strip()\r\n    for host in os.environ.get(...)\r\n    if host.strip()\r\n]\r\n
old = b'ALLOWED_HOSTS = [' + CRLF + b'    ' + SSP + CRLF + b'    ' + host_strip + CRLF + b'    ' + for_host + CRLF + b'    ' + if_host + CRLF + CRLF + close_bracket + CRLF

print('Old block found:', old in content)

if old in content:
    # The correct block keeps testserver, removes the separate host.strip() line
    # New: ALLOWED_HOSTS = [\r\n    'testserver',\r\n    for host in os.environ.get(...)\r\n    if host.strip()\r\n]\r\n
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
