#!/usr/bin/env bash
# Actualización incremental: mergea un export chico (solo la semana nueva)
# contra df_full_clean.pkl sin duplicar filas, y reconstruye dashboard.html.
# Uso: ./weekly.sh export_semana.xlsx
set -euo pipefail
SRC_XLS="${1:?Uso: ./weekly.sh <export_semana.xls|.xlsx>}"

pip install pandas xlrd openpyxl --break-system-packages -q

python3 merge_weekly.py "$SRC_XLS"
python3 build_data.py
# build_data.py reescribe dashboard_data.json entero, así que el bloque de
# altas (aparte, ver build_altas.py) hay que volver a aplicarlo después.
if [ -f altas_diarias.xlsx ]; then
  python3 build_altas.py altas_diarias.xlsx
fi
python3 render_dashboard.py
