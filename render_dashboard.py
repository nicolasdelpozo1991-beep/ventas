"""Paso 3 del pipeline: inyecta dashboard_data.json en dashboard_template.html -> dashboard.html."""
import json

data = json.load(open('dashboard_data.json'))
tmpl = open('dashboard_template.html').read()
out = tmpl.replace('/*__DATA__*/', json.dumps(data, ensure_ascii=False))
open('dashboard.html', 'w').write(out)
print(f'dashboard.html generado ({len(out) / 1024:.0f} KB)')
