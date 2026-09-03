#!/usr/bin/env bash
# Pipeline completo: xls/xlsx crudo -> pkl limpio -> JSON de datos -> dashboard.html
# Uso: ./build.sh facturacion_full.xlsx
set -euo pipefail
SRC_XLS="${1:?Uso: ./build.sh <export.xls|export.xlsx>}"

pip install pandas xlrd openpyxl --break-system-packages -q

python3 clean_source.py "$SRC_XLS" df_full_clean.pkl
python3 build_data.py
python3 render_dashboard.py
