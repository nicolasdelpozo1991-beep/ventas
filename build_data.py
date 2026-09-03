import pandas as pd
import json
import numpy as np
import datetime

df = pd.read_pickle('df_full_clean.pkl')

# Los 7 vendedores que se muestran individualmente en el dashboard (fijo,
# corresponde a la estructura de equipo real). Todo vendedor cuyo vid no
# esté en esta lista cae en el bucket "Otros" en cada gráfico y en la tabla.
TEAM7 = [
    'debora_esquivel', 'david_laredo', 'gisela_martinez', 'sol_lomiento',
    'matias_araoz', 'daniela_alonso', 'julieta_cocchi',
]

# ---- dimension lookups (sorted, matching previous build) ----
fechas = sorted(df['fecha'].dt.strftime('%Y-%m-%d').unique().tolist())
semanas = sorted(df['semana'].dt.strftime('%Y-%m-%d').unique().tolist())
meses = sorted(df['mes'].dt.strftime('%Y-%m-%d').unique().tolist())
date_idx = {d: i for i, d in enumerate(fechas)}
week_idx = {w: i for i, w in enumerate(semanas)}
month_idx = {m: i for i, m in enumerate(meses)}

df['_d'] = df['fecha'].dt.strftime('%Y-%m-%d').map(date_idx)
df['_w'] = df['semana'].dt.strftime('%Y-%m-%d').map(week_idx)
df['_mo'] = df['mes'].dt.strftime('%Y-%m-%d').map(month_idx)

# day -> week/month index lookup (for slicing period ranges from a day range)
day_week = [None] * len(fechas)
day_month = [None] * len(fechas)
tmp = df[['_d', '_w', '_mo']].drop_duplicates('_d').set_index('_d')
for i in range(len(fechas)):
    day_week[i] = int(tmp.loc[i, '_w'])
    day_month[i] = int(tmp.loc[i, '_mo'])

# ---- vendor bucket (7 team members individually, everyone else -> "otros") ----
team_pos = {v: i for i, v in enumerate(TEAM7)}
df['_vb'] = df['vid'].map(team_pos)
df['_vb'] = df['_vb'].where(df['_vb'].notna(), 7).astype(int)

# El export trae nombres en MAYÚSCULAS (vendedor y cliente); se muestran en
# Title Case en el dashboard, pero el matching (vid, ID_cliente) sigue
# usando los valores originales del export, no este formateo.
def display_name(s: str) -> str:
    return s.title()

bucket_meta = [{'id': v, 'nombre': display_name(df.loc[df.vid == v, 'vendedor'].iloc[0])} for v in TEAM7]
bucket_meta.append({'id': 'otros', 'nombre': 'Otros'})

# ---- client dense index + display name lookup ----
cli_names = (df.groupby('ID_cliente')['nombre_cliente']
             .agg(lambda s: s.mode().iat[0] if not s.mode().empty else s.iloc[0]))
cli_ids_sorted = sorted(cli_names.index.tolist())
cli_pos = {cid: i for i, cid in enumerate(cli_ids_sorted)}
clientes_lookup = [display_name(cli_names[cid]) for cid in cli_ids_sorted]
df['_c'] = df['ID_cliente'].map(cli_pos)

# ---- row-level columnar data ----
rows = {
    'vb': df['_vb'].astype(int).tolist(),
    'd': df['_d'].astype(int).tolist(),
    'w': df['_w'].astype(int).tolist(),
    'mo': df['_mo'].astype(int).tolist(),
    'f': df['ID_file'].astype(int).tolist(),
    'c': df['_c'].astype(int).tolist(),
    'a': [round(float(x), 2) for x in df['facturacion']],
    'r': [round(float(x), 2) for x in df['rentabilidad']],
    'nc': df['es_nc'].astype(int).tolist(),
}

meta_out = {
    'fecha_min': fechas[0],
    'fecha_max': fechas[-1],
    'moneda': 'USD',
    'n_vendedores': int(df['vid'].nunique()),
    'operaciones_totales': int(len(df)),
    'n_files_totales': int(df['ID_file'].nunique()),
    'generated_at': datetime.date.today().isoformat(),  # fecha en que se corrió este build (= "última actualización de datos")
}

data = {
    'meta': meta_out,
    'bucket_meta': bucket_meta,
    'fechas': fechas,
    'semanas': semanas,
    'meses': meses,
    'day_week': day_week,
    'day_month': day_month,
    'clientes': clientes_lookup,
    'rows': rows,
}

with open('dashboard_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

print('rows:', len(rows['vb']))
print('clientes:', len(clientes_lookup))
print('fechas/semanas/meses:', len(fechas), len(semanas), len(meses))
import os
print('json size KB:', os.path.getsize('dashboard_data.json')/1024)
