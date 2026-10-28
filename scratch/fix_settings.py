path = r'd:\Grayphite\Django_learning\E_learning\settings.py'
content = open(path, encoding='utf-8').read()
new_content = content.replace(
    "ALLOWED_HOSTS = [",
    "ALLOWED_HOSTS = [\n    'testserver',"
)
open(path, 'w', encoding='utf-8').write(new_content)
print('Updated settings')
