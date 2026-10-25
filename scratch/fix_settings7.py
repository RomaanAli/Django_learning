# -*- coding: utf-8 -*-
path = r'd:\Grayphite\Django_learning\E_learning\settings.py'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Look for the start of the ALLOWED_HOSTS block
    if 'ALLOWED_HOSTS = [' in line:
        # Check if the next line is '    testserver',
        if i + 1 < len(lines) and "'testserver'," in lines[i + 1]:
            # This is the broken block. Skip it and write the new block.
            new_lines.append("ALLOWED_HOSTS = [\n")
            new_lines.append("    'testserver',\n")
            new_lines.append("    host.strip()\n")
            new_lines.append("    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')\n")
            new_lines.append("    if host.strip()\n")
            new_lines.append("]\n")
            # Skip the old lines until we find the closing bracket
            i += 1
            while i < len(lines) and ']' not in lines[i]:
                i += 1
            # Skip the closing bracket line
            i += 1
            continue
    new_lines.append(line)
    i += 1

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Done')
