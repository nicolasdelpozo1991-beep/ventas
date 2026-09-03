"""
Paso 1 del pipeline: toma el export .xls/.xlsx crudo del sistema de
facturación y produce df_full_clean.pkl, el DataFrame limpio que usa
build_data.py.

Uso:
    pip install pandas xlrd openpyxl --break-system-packages
    python3 clean_source.py facturacion_full.xlsx df_full_clean.pkl

Distintos exports del sistema traen los mismos datos con nombres de columna
distintos (ej. 'vendedor' vs 'nombre_1', 'ID_cliente' vs 'id_cliente'). Este
script tolera las variantes conocidas vía ALIASES; si aparece un export con
nombres nuevos, sumar la variante ahí en vez de tocar el resto del script.

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

ALIASES = {
    'vendedor': ['vendedor', 'nombre_1'],
    'ID_tipo_de_comprobante': ['ID_tipo_de_comprobante', 'id_tipo_de_comprobante'],
    'ID_cliente': ['ID_cliente', 'id_cliente'],
    'ID_file': ['ID_file', 'id_file'],
    'renta_terrester_mb': ['renta_terrester_mb', 'renta_terrestre_mb'],
}


def slug(nombre: str) -> str:
    n = unicodedata.normalize('NFKD', nombre).encode('ascii', 'ignore').decode('ascii')
    return n.strip().lower().replace(' ', '_')


def resolve_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for target, candidates in ALIASES.items():
        found = next((c for c in candidates if c in df.columns), None)
        if found is None:
            raise KeyError(f'Ninguna de estas columnas está en el export: {candidates}')
        if found != target:
            rename[found] = target
    return df.rename(columns=rename)


def parse_fecha(raw: pd.Series) -> pd.Series:
    fecha = pd.to_datetime(raw, dayfirst=True, format='mixed', errors='coerce')

    # Algún export trae alguna fecha corrupta (ej. milisegundos pegados con
    # ':' en vez de '.', tipo "12/8/2026 11:54:43:133") que el parser normal
    # no puede leer. Para esas filas, nos quedamos con el primer token
    # "DD/MM/YYYY" y lo parseamos aparte en vez de descartar la fila.
    bad = fecha.isna() & raw.notna()
    if bad.any():
        primer_token = raw[bad].astype(str).str.split(' ').str[0]
        fecha[bad] = pd.to_datetime(primer_token, dayfirst=True, errors='coerce')

    return fecha.dt.normalize()


# Combinación de columnas que identifica una fila de forma (casi) única en
# los exports de este sistema. ID_factura_cabeza NO sirve como key: se
# reusa entre filas no relacionadas. La usa merge_weekly.py para no duplicar
# filas al mergear un export incremental contra el histórico.
DEDUPE_KEY = ['ID_file', 'fecha', 'importe_total_mb', 'ID_cliente', 'ID_tipo_de_comprobante']


def clean(src_xls: str) -> pd.DataFrame:
    engine = 'openpyxl' if src_xls.lower().endswith('.xlsx') else 'xlrd'
    df = pd.read_excel(src_xls, engine=engine)
    df = resolve_columns(df)

    # Filas sin vendedor asignado (raras, pero existen) -> bucket explícito
    df['vendedor'] = df['vendedor'].fillna('SIN ASIGNAR')

    df['facturacion'] = df['importe_total_mb']
    df['rentabilidad'] = df['renta_aerea_mb'] + df['renta_terrester_mb']
    df['fecha'] = parse_fecha(df['fecha_emision'])

    sin_fecha = df['fecha'].isna()
    if sin_fecha.any():
        print(f'AVISO: {sin_fecha.sum()} fila(s) con fecha_emision ilegible, se descartan:')
        print(df.loc[sin_fecha, ['ID_file', 'ID_tipo_de_comprobante', 'nombre_cliente', 'fecha_emision']])
        df = df[~sin_fecha].copy()

    df['es_nc'] = df['ID_tipo_de_comprobante'].isin(['NCI', 'NEC', 'NED'])
    df['semana'] = df['fecha'] - pd.to_timedelta(df['fecha'].dt.weekday, unit='D')
    df['mes'] = df['fecha'].values.astype('datetime64[M]')
    df['vid'] = df['vendedor'].map(slug)

    return df


def main(src_xls: str, out_pkl: str):
    df = clean(src_xls)
    df.to_pickle(out_pkl)
    print(f'{len(df)} filas -> {out_pkl}')
    print(f'  rango de fechas: {df.fecha.min().date()} a {df.fecha.max().date()}')
    print(f'  vendedores únicos: {df.vid.nunique()}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
