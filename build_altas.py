"""
Arma el bloque 'altas' de dashboard_data.json a partir del export de altas
diarias (altas = files nuevos dados de alta, por día — pipeline comercial,
no facturación). Fuente aparte de clean_source.py/build_data.py: una fila
por día, un solo departamento (MAY), se agrega directo al JSON ya armado.

Uso (después de build_data.py, antes de render_dashboard.py):
    python3 build_altas.py altas_diarias.xlsx
    python3 build_altas.py altas_diarias.xlsx --json otro_dashboard_data.json

El export trae cant_files, cant_pax, venta_ml, venta_me por día — hoy solo
se usa cant_files (cantidad de altas). Cada corrida reemplaza el bloque
'altas' completo con lo que traiga el export (no es incremental: si el
export es acumulado histórico, alcanza con volver a correr esto con el
export más reciente).
"""
import sys
import json
import argparse
import pandas as pd


def build_altas(src_xlsx: str) -> dict:
    engine = 'openpyxl' if src_xlsx.lower().endswith('.xlsx') else 'xlrd'
    df = pd.read_excel(src_xlsx, engine=engine)
    df['fecha'] = pd.to_datetime(dict(year=df['anio'], month=df['mes'], day=df['dia']))
    df['semana'] = df['fecha'] - pd.to_timedelta(df['fecha'].dt.weekday, unit='D')
    df['mes_'] = df['fecha'].values.astype('datetime64[M]')

    def series(group_col):
        g = df.groupby(group_col)['cant_files'].sum().sort_index()
        return [{'f': d.strftime('%Y-%m-%d'), 'v': int(v)} for d, v in g.items()]

    return {
        'daily': series('fecha'),
        'weekly': series('semana'),
        'monthly': series('mes_'),
    }


def main(src_xlsx: str, data_json: str):
    altas = build_altas(src_xlsx)

    with open(data_json, encoding='utf-8') as f:
        data = json.load(f)
    data['altas'] = altas
    with open(data_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"altas: {len(altas['daily'])} días, {len(altas['weekly'])} semanas, "
          f"{len(altas['monthly'])} meses -> {data_json}['altas']")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('export_altas', help='export .xls/.xlsx de altas diarias')
    ap.add_argument('--json', default='dashboard_data.json', help='dashboard_data.json a actualizar (default: dashboard_data.json)')
    args = ap.parse_args()
    main(args.export_altas, args.json)
