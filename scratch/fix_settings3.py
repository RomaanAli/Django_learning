# -*- coding: utf-8 -*-
path = r'd:\Grayphite\Django_learning\E_learning\settings.py'
content = open(path, encoding='utf-8').read()

# Find the ALLOWED_HOSTS block and rewrite it cleanly
old_start = content.find('ALLOWED_HOSTS = [')
if old_start == -1:
    print('ALLOWED_HOSTS not found')
else:
    # Find the matching closing bracket
    depth = 0
    old_end = None
    i = old_start
    while i < len(content):
        if content[i] == '[':
            depth += 1
        elif content[i] == ']':
            depth -= 1
            if depth == 0:
                old_end = i + 1
                break
        i += 1
    if old_end is None:
        print('No closing bracket found')
    else:
        new_block = """ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')
    if host.strip()
]
"""
        content = content[:old_start] + new_block + content[old_end:]
        open(path, 'w', encoding='utf-8').write(content)
        print('Rewrote ALLOWED_HOSTS block')
