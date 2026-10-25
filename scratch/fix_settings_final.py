# -*- coding: utf-8 -*-
path = r'd:\Grayphite\Django_learning\E_learning\settings.py'

# Read the file
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the ALLOWED_HOSTS = [ block and rewrite it
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if 'ALLOWED_HOSTS = [' in line:
        # Write the new block
        new_lines.append("ALLOWED_HOSTS = [\n")
        new_lines.append("    'testserver',\n")
        new_lines.append("    host.strip()\n")
        new_lines.append("    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')\n")
        new_lines.append("    if host.strip()\n")
        new_lines.append("]\n")
        # Skip the old block lines (consume until matching closing bracket)
        depth = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith('for host') or stripped.startswith('if host.strip()') or stripped.startswith('host.strip()'):
                pass
            if ']' in stripped and depth == 0:
                # Check if this is the closing bracket of ALLOWED_HOSTS
                # The new block already has the closing bracket
                break
            i += 1
        # Don't consume the closing bracket line - we'll add it in new_lines
        i += 1
    else:
        new_lines.append(line)
        i += 1

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Fixed ALLOWED_HOSTS in settings.py')
