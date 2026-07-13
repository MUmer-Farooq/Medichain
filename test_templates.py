import app
from pathlib import Path
import traceback

client = app.app.test_client()

templates = list(Path('templates').rglob('*.html'))
errors = []

for t in templates:
    rel = t.relative_to('templates').as_posix()
    if rel in ['index.html', 'login.html', 'hospital_registration.html']:
        if rel == 'index.html': route = '/'
        if rel == 'login.html': route = '/login'
        if rel == 'hospital_registration.html': route = '/hospital_registration'
    else:
        route = '/' + rel.replace('.html', '')
    
    try:
        resp = client.get(route)
        if resp.status_code != 200:
            print(f'Error rendering {rel}: {resp.status_code}')
            errors.append(rel)
    except Exception as e:
        print(f'Exception rendering {rel}: {e}')
        traceback.print_exc()
        errors.append(rel)

print(f'Tested {len(templates)} templates, {len(errors)} errors.')
