path = r'd:\Grayphite\Django_learning\E_learning\settings.py'
content = open(path, encoding='utf-8').read()
if "'testserver'" not in content:
    content = content.replace(
        'ALLOWED_HOSTS = [',
        "ALLOWED_HOSTS = [\n    'testserver',"
    )
    open(path, 'w', encoding='utf-8').write(content)
    print('Added testserver')
else:
    print('testserver already present')
