path = r'd:\Grayphite\Django_learning\E_learning\settings.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """ALLOWED_HOSTS = [
    'testserver',
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')
    if host.strip()
]
"""

new = """ALLOWED_HOSTS = [
    'testserver',
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')
    if host.strip()
]
"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed')
else:
    print('Old block not found - checking content')
    idx = content.find('ALLOWED_HOSTS')
    print(repr(content[idx:idx+400]))
