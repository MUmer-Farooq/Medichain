import glob
import os

for f in glob.glob('templates/system-admin/*.html'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Update login links
    content = content.replace('../login.html', '/logout')
    
    # Update static links
    content = content.replace('../static/', "{{ url_for('static', filename='') }}")
    content = content.replace("filename='')css/", "filename='css/")
    content = content.replace("filename='')js/", "filename='js/")
    content = content.replace("filename='')img/", "filename='img/")
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print('Done!')
