path = r'd:\Grayphite\Django_learning\E_learning\settings.py'
content = open(path, encoding='utf-8').read()

start = content.find('ALLOWED_HOSTS = [')
if start == -1:
    print('Not found')
else:
    depth = 0
    end = None
    i = start
    while i < len(content):
        if content[i] == '[':
            depth += 1
        elif content[i] == ']':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
        i += 1

    new_block = """ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')
    if host.strip()
]
    """

    content = content[:start] + new_block + content[end:]

    if "'testserver'" not in content:
        content = content.replace(
            'ALLOWED_HOSTS = [',
            "ALLOWED_HOSTS = [\n    'testserver',"
        )

    open(path, 'w', encoding='utf-8').write(content)
    print('Settings fixed')
