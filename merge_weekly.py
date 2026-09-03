"""
Actualización incremental: toma un export chico (solo la semana nueva),
lo limpia igual que clean_source.py, lo mergea contra df_full_clean.pkl
sin duplicar filas, y sobreescribe el pkl.

Uso:
    python3 merge_weekly.py export_semana.xlsx
    python3 merge_weekly.py export_semana.xlsx --pkl df_full_clean.pkl

Después de correr esto, seguí con el resto del pipeline:
    python3 build_data.py
    (o directamente ./weekly.sh export_semana.xlsx, que hace los 3 pasos)

Deduplica por clean_source.DEDUPE_KEY (ID_file, fecha, importe_total_mb,
ID_cliente, ID_tipo_de_comprobante) — ID_factura_cabeza no sirve como key
porque el sistema la reusa entre filas no relacionadas.
"""
import argparse
import os
import sys

import pandas as pd

from clean_source import DEDUPE_KEY, clean


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('export_nuevo', help='export .xls/.xlsx con las filas nuevas (ej. de la semana)')
    ap.add_argument('--pkl', default='df_full_clean.pkl', help='pkl histórico a actualizar (default: df_full_clean.pkl)')
    args = ap.parse_args()

    if not os.path.exists(args.pkl):
        print(f'No existe {args.pkl} todavía. Para el primer build corré clean_source.py directo:')
        print(f'  python3 clean_source.py {args.export_nuevo} {args.pkl}')
        sys.exit(1)

    old_df = pd.read_pickle(args.pkl)
    new_df = clean(args.export_nuevo)

    key_old = old_df.set_index(DEDUPE_KEY).index
    is_dup = new_df.set_index(DEDUPE_KEY).index.isin(key_old)
    added_df = new_df[~is_dup]

    merged = pd.concat([old_df, added_df], ignore_index=True)
    merged.to_pickle(args.pkl)

    print(f'{args.export_nuevo}: {len(new_df)} filas leídas, {is_dup.sum()} ya estaban (se descartan), {len(added_df)} nuevas')
    print(f'{args.pkl}: {len(old_df)} -> {len(merged)} filas')
    print(f'  rango de fechas: {merged.fecha.min().date()} a {merged.fecha.max().date()}')


if __name__ == '__main__':
    main()
