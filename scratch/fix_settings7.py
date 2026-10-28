path = r'd:\Grayphite\Django_learning\E_learning\settings.py'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if 'ALLOWED_HOSTS = [' in line:
        if i + 1 < len(lines) and "'testserver'," in lines[i + 1]:
            new_lines.append("ALLOWED_HOSTS = [\n")
            new_lines.append("    'testserver',\n")
            new_lines.append("    host.strip()\n")
            new_lines.append("    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')\n")
            new_lines.append("    if host.strip()\n")
            new_lines.append("]\n")
            i += 1
            while i < len(lines) and ']' not in lines[i]:
                i += 1
            i += 1
            continue
    new_lines.append(line)
    i += 1

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Done')
