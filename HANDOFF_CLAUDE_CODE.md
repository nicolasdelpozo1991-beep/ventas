# Pulso Comercial — handoff para Claude Code

Dashboard de facturación y rentabilidad por vendedor (operador turístico mayorista), armado como una única página HTML autocontenida (sin build step, sin backend). Este documento es para pegarle a Claude Code y que siga iterando sobre el proyecto.

## Qué es esto

Un archivo `dashboard.html` de ~550 KB: CSS + JS vanilla + los datos embebidos como un `const DATA = {...}` en un `<script>`. No usa librerías de gráficos (los charts son SVG a mano) ni frameworks. Corre abriendo el archivo en cualquier navegador, sin servidor.

Hoy vive publicado como Artifact público (con link compartible) en `https://claude.ai/code/artifact/0baa6037-37fa-40f3-b635-69d7cf476338`. Si vas a seguir editando `dashboard_template.html` acá, esa URL sigue siendo la versión "oficial" que ve Nicolás — coordinen quién la actualiza para no pisarse.

## Archivos que te paso

| Archivo | Qué hace |
|---|---|
| `clean_source.py` | Paso 1: toma el `.xls` crudo del sistema de facturación y arma `df_full_clean.pkl` (agrega columnas derivadas: `facturacion`, `rentabilidad`, `fecha`, `es_nc`, `semana`, `mes`, `vid`) |
| `build_data.py` | Paso 2: de `df_full_clean.pkl` arma `dashboard_data.json` — los datos a nivel de comprobante individual (fila por fila, no agregados) que consume el dashboard |
| `dashboard_template.html` | El template maestro: todo el HTML/CSS/JS, con un placeholder `/*__DATA__*/` donde se inyecta el JSON |
| `build.sh` | Corre los 3 pasos de punta a punta: `./build.sh export.xls` → genera `dashboard.html` |

**El archivo que se edita siempre es `dashboard_template.html`**, nunca `dashboard.html` directamente (ese se regenera).

## Cómo regenerar

```bash
pip install pandas xlrd --break-system-packages
./build.sh facturacion_full.xls
```

Esto reconstruye `df_full_clean.pkl` → `dashboard_data.json` → `dashboard.html`. Cualquier cambio en `dashboard_template.html` o en un export `.xls` nuevo pasa por acá.

**Ojo**: `build.sh` asume que le pasás un export `.xls` con TODO el histórico (no incremental). En la práctica, las actualizaciones semanales llegan como exports chicos (solo la semana nueva). Para esos casos no se usa `build.sh` tal cual — se limpia el export nuevo con `clean_source.py` a un pkl aparte, se valida que no haya filas duplicadas contra el pkl viejo (el campo `ID_factura_cabeza` del sistema **no sirve como key** — se reusa entre filas no relacionadas; usar en cambio la combinación `['ID_file','fecha','importe_total_mb','ID_cliente','ID_tipo_de_comprobante']`), y recién ahí se hace `pd.concat([old_df, new_df])` y se guarda como el `df_full_clean.pkl` nuevo antes de correr `build_data.py`. Si querés, este flujo incremental se puede envolver en un script aparte (`merge_weekly.py` o similar) — no está armado todavía, es manual.

## Arquitectura de datos (importante antes de tocar nada)

El dashboard **no** trabaja con agregados precalculados por vendedor — trabaja con datos a nivel de fila (una fila = un comprobante). `dashboard_data.json` tiene esta forma:

```
DATA.rows = {
  vb: [...],   // índice de "bucket" de vendedor (0-6 = los 7 del equipo, 7 = Otros)
  d:  [...],   // índice de fecha (en DATA.fechas)
  w:  [...],   // índice de semana (en DATA.semanas)
  mo: [...],   // índice de mes (en DATA.meses)
  f:  [...],   // ID_file (para contar files únicos)
  c:  [...],   // índice de cliente (en DATA.clientes)
  a:  [...],   // facturación de esa fila (con signo — negativo en notas de crédito)
  r:  [...],   // rentabilidad de esa fila
  nc: [...],   // 1 si es nota de crédito, 0 si no
}
```

Todo lo demás (KPIs, ranking, margen, evolución, scatter, tabla, top clientes) se calcula en el navegador con funciones JS que recorren `DATA.rows` y agregan al vuelo (`computeBucketStats`, `periodSeriesForBuckets`, `computeTopClientes`, etc., todas en el `<script>` de `dashboard_template.html`). Esto es lo que permite que el filtro de período funcione de forma consistente en todos los gráficos a la vez.

Si agregás un gráfico o métrica nueva: **no agregues un agregado precalculado en Python** — sumá una función JS que recorra `DATA.rows` con el mismo patrón (filtra por bucket + rango de fecha, acumula). Así se mantiene todo consistente con los filtros.

### Regla de negocio fija: "Equipo (7) + Otros"

Hay 7 vendedores fijos que se muestran individualmente (lista `TEAM7` en `build_data.py`); todos los demás vendedores se agrupan en un bucket "Otros" — en absolutamente todos los gráficos y en la tabla. Si el equipo cambia de composición, actualizá `TEAM7` en `build_data.py`.

### Formato numérico

Todo el dashboard usa formato es-AR: coma decimal, punto de miles (`fmtUSD`, `fmtPct`, `fmtInt` en el template). Mantené esa convención en cualquier agregado nuevo.

## Funcionalidades ya implementadas

- KPIs: facturación, rentabilidad, margen, facturación/rentabilidad por file — sin comparación contra período anterior (se probó una variación vs. 5 días hábiles previos y se sacó a pedido de Nicolás, confundía más de lo que aportaba). Si en algún momento piden retomar ese tipo de análisis, ojo con dejarlo claro en cuanto a moneda y período de comparación.
- Evolución temporal: barras por mes, línea por semana/día; multi-serie si seleccionás más de un vendedor
- Ranking de facturación, margen de rentabilidad (barra divergente), scatter volumen vs. rentabilidad
- Top clientes y concentración (% de facturación en top 5/10 clientes)
- Tabla de detalle ordenable
- Filtro de período (presets + rango personalizado) que re-calcula todo
- Botón "Limpiar selección"
- Exportar PDF vía `window.print()` con hoja de estilos dedicada (fuerza colores claros incluso en modo oscuro)
- Tema claro/oscuro automático (`prefers-color-scheme`)
- Badge "Datos actualizados" en el header (al lado del de "Período de la base"), + la fecha en el footer ("Generado ..."): ambos leen `DATA.meta.generated_at`, que `build_data.py` completa con la fecha en la que se corrió el build (no la fecha del dato más reciente — eso ya lo cubre `fecha_max`). Si armás un pipeline nuevo, acordate de seguir seteando ese campo.

## Actualización de datos: ya hay un recordatorio automático

Nicolás ya tiene un scheduled task (Friday, corre solo) que cada viernes le pide el `.xls` de la semana, corre el pipeline, mergea incremental y publica la nueva versión en el Artifact de arriba. Si vas a tocar el flujo de actualización de datos, avisale a Nicolás para que decida si lo deja como está, lo desactiva, o lo migra a lo que armes en Claude Code — mejor no terminar con dos procesos actualizando el mismo dashboard por separado.

## Qué NO está (por si lo pedís)

- **Export a planilla (CSV) desde el propio HTML**: se implementó usando la capability `downloads` del visor de Artifacts de Claude — algo específico de ese entorno, no de un HTML plano. Si Claude Code va a servir este archivo standalone (fuera de claude.ai), esa función no aplica: hay que resolver la descarga con un enfoque estándar de navegador (por ejemplo `<a download>` con un blob URL, que en un HTML servido normalmente sí funciona sin problema — el bloqueo era específico del sandbox del visor de Artifacts).
- Autenticación, multi-tenant, guardado de estado entre sesiones: no hay nada de esto, es un archivo estático.

## Estilo / principios de diseño a mantener

- Paleta y specs de marcas (grosor de barra ≤24px, gaps de 2px, gridlines hairline, etc.) siguen la guía de dataviz de Claude — si agregás gráficos, mantené la consistencia visual con los existentes en `dashboard_template.html` (mismos tokens CSS `--slot-1..7`, `--slot-otros`, `--accent`, etc.)
- Tooltips: un tooltip por posición del cursor listando todas las series, no uno por punto
- Sin librerías externas de charts — todo SVG a mano con helpers `svgEl`/`svgText` ya definidos

## Sugerencia de prompt inicial para Claude Code

> Este es el proyecto "Pulso Comercial", un dashboard HTML autocontenido (sin backend) para un operador turístico mayorista. Leé `HANDOFF_CLAUDE_CODE.md` primero. El archivo que se edita es `dashboard_template.html`; para ver los cambios corré `./build.sh <export.xls>` y abrí el `dashboard.html` resultante. [acá contás qué querés que haga]
