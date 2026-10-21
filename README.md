*************************************************************************
# HyetiaScan 2.1.2

Análisis de lluvias

- Juan Manuel de Villeros Arias
- Mónica Liliana Gallego Jaramillo

Junio - Agosto 2024

Contacto: hyetiascan@teoktonos.com


*************************************************************************

### Cambios en versión 2.1.2 - Julio 2025

#### Nueva Opción para Controlar la Inclusión de Pausas Iguales a la Pausa Máxima

Se ha añadido una nueva funcionalidad en la interfaz de la pestaña "Eventos" que permite al usuario decidir si las pausas con una duración exactamente igual a la pausa máxima (definida en minutos) se consideran parte de una lluvia continua o como interrupciones que separan eventos de precipitación. 

El usuario puede elegir entre: 
- Incluir (tratar como lluvia): Las pausas de duración igual a la pausa máxima se consideran parte del mismo evento de lluvia (usa <= pausa_maxima).  
- Separar (tratar como interrupción): Las pausas de duración igual a la pausa máxima se tratan como interrupciones que dividen eventos (usa < pausa_maxima).

Este cambio mejora la flexibilidad del análisis de eventos de precipitación, especialmente para casos donde el criterio especificado de pausa máxima es igual al intervalo de medición, permitiendo un control más preciso sobre la definición de eventos continuos. 


*************************************************************************

### Uso sin interfaz (CLI y módulo)

La lógica de cálculo está en `hyetiascan_core.py`, un módulo sin dependencia de Streamlit. La aplicación (`HyetiaScan.py`) lo usa para todos sus cálculos, de modo que la interfaz, la línea de comandos y cualquier programa Python obtienen los mismos resultados.

#### Aplicación Streamlit (sin cambios)

```bash
pip install -r requirements.txt
streamlit run HyetiaScan.py        # http://localhost:8501/analysis
```

#### Línea de comandos

```bash
python hyetiascan_cli.py ejemplos/lluvia_ejemplo_5min.csv --salida resultados \
    --duplicadas primera --corruptas borrar --atipicas borrar --perdidas cero --json
```

Genera en `resultados/`: `lecturas_procesadas.csv`, `lecturas_agrupadas.csv`, `eventos.csv`, `acumulados.csv`, `curvas_huff.csv` y, con `--json`, `resumen.json`. Las columnas con listas (`lecturas`, `porcentajes`, `percentiles`) se guardan como JSON.

Opciones principales (ver `python hyetiascan_cli.py --help`):

- Carga: `--decimal {.,,}`, `--codificacion`, `--col-fechahora`, `--col-precipitacion`.
- Control de anormales: `--duplicadas {no-modificar,primera,ultima,sumar,promediar,borrar}`, `--corruptas borrar`, `--atipicas borrar`, `--umbral-atipicas` (20), `--perdidas cero`.
- Eventos: `--fecha-inicial`, `--fecha-final`, `--duracion-minima` (20), `--duracion-maxima` (9999), `--intensidad-minima` (3), `--pausa-maxima` (2 × intervalo), `--pausa-igual {incluir,separar}`, `--intervalo-percentiles` (10).

Igual que en la aplicación, si quedan lecturas anormales sin controlar no se calculan eventos; el programa guarda las lecturas y termina con código 2.

#### Como módulo de Python

```python
import hyetiascan_core as nucleo

df = nucleo.cargar_csv('ejemplos/lluvia_ejemplo_5min.csv')
lecturas = nucleo.extraer_lecturas(df, 'fechahora', 'precipitacion_mm')
intervalo = nucleo.estimar_intervalo_lecturas(lecturas)
lecturas = nucleo.normalizar_lecturas(lecturas, intervalo)
lecturas = nucleo.procesar_lecturas(
    lecturas, intervalo, control_duplicadas=nucleo.DUPLICADAS_PRIMERA,
    corruptas_borrar=True, atipicas_borrar=True, perdidas_asumir_cero=True,
)
fechas = lecturas['fechahora']
consolidadas = nucleo.consolidar_lecturas(
    lecturas, fechas.min().date(), fechas.max().date(), intervalo)
eventos = nucleo.calcular_eventos(
    consolidadas, duracion_minima=20, duracion_maxima=9999,
    pausa_maxima=2 * intervalo, intensidad_minima=3,
    intervalo=intervalo, incluir_pausa_igual=True,
)
curvas = nucleo.calcular_curvas_huff(eventos, intervalo=10)
acumulados = nucleo.obtener_acumulados(eventos)
```

`ejemplos/lluvia_ejemplo_5min.csv` es un archivo sintético (45 días, lecturas cada 5 minutos) con varios eventos, un vacío de 30 minutos, una lectura duplicada, una corrupta y una atípica, útil para probar los controles.
