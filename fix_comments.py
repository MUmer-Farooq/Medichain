import glob
import re

for f in glob.glob('templates/**/*.html', recursive=True):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # We want to replace lines like "<!-- Flask: {% ... %} -->" or "<!-- Flask Dynamic: ... -->"
    # with "{# Flask: ... #}" or "{# Flask Dynamic: ... #}"
    
    # Find all lines containing "<!-- Flask"
    def replacer(match):
        return match.group(0).replace('<!--', '{#').replace('-->', '#}')
        
    content = re.sub(r'<!--\s*Flask.*?(?:-->)', replacer, content)
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)

print('Done fixing Flask comments!')
