"""
Paso 1 del pipeline: toma el export .xls crudo del sistema de facturación
y produce df_full_clean.pkl, el DataFrame limpio que usa build_data.py.

Uso:
    pip install pandas xlrd --break-system-packages
    python3 clean_source.py facturacion_full.xls df_full_clean.pkl

Columnas derivadas que agrega (además de las ~52 originales del export):
  - facturacion   = importe_total_mb (monto neto en USD / "moneda base",
                    ya viene con signo negativo en las notas de crédito)
  - rentabilidad  = renta_aerea_mb + renta_terrester_mb
  - fecha         = fecha_emision parseada a datetime (solo la parte de fecha)
  - es_nc         = True si ID_tipo_de_comprobante está en {NCI, NEC, NED}
                    (nota de crédito interna/externa). FEC/FCI/FCM/FET son
                    facturas; AJH/AJU son ajustes de rentabilidad sin
                    facturación asociada (quedan con es_nc=False).
  - semana        = lunes de la semana ISO de `fecha`
  - mes           = primer día del mes de `fecha`
  - vid           = slug del nombre del vendedor (minúsculas, sin acentos,
                    espacios -> guión bajo) — id estable para vincular con
                    TEAM7 en meta_lists.json / build_data.py
"""
import sys
import unicodedata
import pandas as pd


def slug(nombre: str) -> str:
    n = unicodedata.normalize('NFKD', nombre).encode('ascii', 'ignore').decode('ascii')
    return n.strip().lower().replace(' ', '_')


def main(src_xls: str, out_pkl: str):
    df = pd.read_excel(src_xls, engine='xlrd')

    # Filas sin vendedor asignado (raras, pero existen) -> bucket explícito
    df['vendedor'] = df['vendedor'].fillna('SIN ASIGNAR')

    df['facturacion'] = df['importe_total_mb']
    df['rentabilidad'] = df['renta_aerea_mb'] + df['renta_terrester_mb']
    df['fecha'] = pd.to_datetime(df['fecha_emision'], dayfirst=True, format='mixed').dt.normalize()
    df['es_nc'] = df['ID_tipo_de_comprobante'].isin(['NCI', 'NEC', 'NED'])
    df['semana'] = df['fecha'] - pd.to_timedelta(df['fecha'].dt.weekday, unit='D')
    df['mes'] = df['fecha'].values.astype('datetime64[M]')
    df['vid'] = df['vendedor'].map(slug)

    df.to_pickle(out_pkl)
    print(f'{len(df)} filas -> {out_pkl}')
    print(f'  rango de fechas: {df.fecha.min().date()} a {df.fecha.max().date()}')
    print(f'  vendedores únicos: {df.vid.nunique()}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
