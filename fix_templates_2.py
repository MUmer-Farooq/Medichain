import glob

for f in glob.glob('templates/system-admin/*.html'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Fix the url_for syntax error I just made
    content = content.replace("{{ url_for('static', filename='') }}css/", "{{ url_for('static', filename='css/")
    content = content.replace("{{ url_for('static', filename='') }}js/", "{{ url_for('static', filename='js/")
    content = content.replace("{{ url_for('static', filename='') }}img/", "{{ url_for('static', filename='img/")
    
    # We need to append the missing ' }}' at the end of the filename!
    # A better approach:
    # Actually wait, let's just do a simple regex using re module.
    pass

import re
for f in glob.glob('templates/system-admin/*.html'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # If the file has {{ url_for('static', filename='') }}css/style.css"
    # We want it to be {{ url_for('static', filename='css/style.css') }}"
    content = re.sub(r"\{\{ url_for\('static', filename=''\) \}\}(css|js|img)/(.*?)\"", r"{{ url_for('static', filename='\1/\2') }}\"", content)
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print('Done!')
