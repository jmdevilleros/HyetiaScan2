# *********************************************************************************************
# HyetiaScan
# Análisis de lluvias
# Juan Manuel de Villeros Arias
# Mónica Liliana Gallego Jaramillo
# Junio - Agosto 2024
#
# Archivo: hyetiascan_core.py - Lógica de cálculo, sin dependencia de Streamlit
#
# Funciones puras de carga, control de lecturas y cálculo de eventos. Las usan tanto la
# aplicación Streamlit (HyetiaScan.py) como la interfaz de línea de comandos
# (hyetiascan_cli.py), y pueden importarse desde cualquier programa Python.
# *********************************************************************************************

# =============================================================================================
# Bibliotecas
# =============================================================================================

import re
from math import floor, ceil, trunc

import numpy as np
import pandas as pd

from mensajes_es import TEXTOS

# =============================================================================================
# Globales
# =============================================================================================

# Opciones de control de lecturas duplicadas
DUPLICADAS_PRIMERA   = 'primera'
DUPLICADAS_ULTIMA    = 'ultima'
DUPLICADAS_SUMAR     = 'sumar'
DUPLICADAS_PROMEDIAR = 'promediar'
DUPLICADAS_BORRAR    = 'borrar'
OPCIONES_DUPLICADAS  = (
    DUPLICADAS_PRIMERA, DUPLICADAS_ULTIMA, DUPLICADAS_SUMAR,
    DUPLICADAS_PROMEDIAR, DUPLICADAS_BORRAR,
)

# Frecuencias de agrupación de lecturas (día, mes, año)
AGRUPACION_DIA = 'D'
AGRUPACION_MES = 'ME'
AGRUPACION_ANO = 'YE'

# Categorías de lecturas; todas menos la primera son anormales
LISTA_CATEGORIAS = [
    TEXTOS['colcorrectas'],
    TEXTOS['colperdidas'],
    TEXTOS['colduplicadas'],
    TEXTOS['colcorruptas'],
    TEXTOS['colatipicas'],
]
LISTA_ANORMALES = LISTA_CATEGORIAS[1:]

# Valores por defecto de la interfaz
UMBRAL_ATIPICAS          = 20
DURACION_MINIMA          = 20
DURACION_MAXIMA          = 9999
INTENSIDAD_MINIMA        = 3
LAPSOS_ACUMULADOS        = [10, 20, 30, 40, 50, 60, 90, 120]
INTERVALO_PERCENTILES    = 10

# =============================================================================================
# Carga de archivo
# =============================================================================================

# ---------------------------------------------------------------------------------------------
def cargar_csv(archivo, decimal: str = '.', codificacion: str = 'utf-8') -> pd.DataFrame:
    # archivo puede ser una ruta o un objeto tipo archivo. Las excepciones se propagan.
    return pd.read_csv(
        archivo, 
        decimal=decimal, 
        encoding=codificacion, 
        parse_dates=True, 
        engine='pyarrow',
    )

# ---------------------------------------------------------------------------------------------
def verificar_lecturas_cargadas(df: pd.DataFrame) -> bool:
    # Mínimo dos registros y dos columnas
    return (df is not None) and (df.shape[1] >= 2) and (df.shape[0] >= 2)

# ---------------------------------------------------------------------------------------------
def columnas_por_tipo(df: pd.DataFrame, tipos_validos: list[str]) -> list[str]:
    return list(df.select_dtypes(include=tipos_validos).columns)

# ---------------------------------------------------------------------------------------------
def buscar_errores_fechahora(df: pd.DataFrame):
    # Verificar explícitamente si hay columnas tipo object (strings) 
    # que no se pueden convertir a tipo fechahora por errores de formato.
    # Retorna (columna, indice, valor_fechahora) del primer error, o None.
    try:
        for col in df.select_dtypes(include='object'): 
            pd.to_datetime(df[col], format='%Y-%m-%d %H:%M:%S')
    except ValueError as ex:
        mensaje_error = str(ex)
        patron_fechahora = r'time data \"(.*?)\"'
        patron_posicion = r'at position (\d+)'

        coincidencia_fechahora = re.search(patron_fechahora, mensaje_error)
        coincidencia_posicion = re.search(patron_posicion, mensaje_error)

        valor_fechahora = coincidencia_fechahora.group(1) if coincidencia_fechahora else None
        indice = int(coincidencia_posicion.group(1)) if coincidencia_posicion else None
        return col, indice, valor_fechahora
    return None

# =============================================================================================
# Preparación y control de lecturas
# =============================================================================================

# ---------------------------------------------------------------------------------------------
def extraer_lecturas(df: pd.DataFrame, col1: str, col2: str) -> pd.DataFrame:
    return df[[col1, col2]].copy()

# ---------------------------------------------------------------------------------------------
def estimar_intervalo_lecturas(df: pd.DataFrame) -> int:
    # Calcular intervalo con la moda de los delta_t entre los primeros registros
    try:
        col_t = df.columns[0]
        s_delta_t = pd.to_timedelta(df[col_t].head(1000).diff().fillna(0))
        moda_dt = s_delta_t.mode()[0]
        intervalo = int(moda_dt.total_seconds() / 60)
    except:
        intervalo = 0
    return intervalo

# ---------------------------------------------------------------------------------------------
def normalizar_lecturas(df: pd.DataFrame, intervalo_minutos: int) -> pd.DataFrame:
    # Alinea fecha-hora al intervalo. Modifica df (como la versión original).
    col_fechahora = df.columns[0]
    df[col_fechahora] = df[col_fechahora].dt.floor(f'{intervalo_minutos}min')
    return df

# ---------------------------------------------------------------------------------------------
def evaluar_grupo_lecturas(grupo: pd.Series) -> pd.Series:
    P_acumulada = grupo['sum'][grupo['sum'] > 0].sum()
    correctas   = grupo[TEXTOS['colcorrectas']].sum()
    perdidas    = grupo['size'][grupo['size'] == 0].count()
    duplicadas  = grupo['size'][grupo['size'] > 1].sum()  # sum() y no count() p/contar todas
    corruptas   = grupo['sum'][grupo['sum'] < 0].count()
    atipicas    = grupo[TEXTOS['colatipicas']].sum()

    return {
        TEXTOS['colpacumulada'] : P_acumulada, 
        TEXTOS['colcorrectas']  : correctas, 
        TEXTOS['colperdidas']   : perdidas, 
        TEXTOS['colduplicadas'] : duplicadas, 
        TEXTOS['colcorruptas']  : corruptas,
        TEXTOS['colatipicas']   : atipicas, 
    }

# ---------------------------------------------------------------------------------------------
def relleno_perdidas(df: pd.DataFrame, intervalo: str, relleno: int = 0) -> pd.DataFrame:
    col_fechahora = df.columns[0]
    serie = df.resample(intervalo, on=col_fechahora).first()
    df_perdidas =  serie[serie.isnull().any(axis=1)].fillna(relleno).reset_index()
    return df_perdidas

# ---------------------------------------------------------------------------------------------
def agrupar_lecturas(
    df: pd.DataFrame, 
    intervalo_base: str, 
    intervalo_grupo: str,
    umbral_precipitacion : float = 600.0,
) -> pd.DataFrame:
    
    col_fechahora = df.columns[0]
    col_precipitacion = df.columns[1]

    # Generar secuencia de tiempo con el mismo intervalo para rellenar posibles vacíos
    # y generar valores de conteo "size" y "sum" para detección de valores anormales.
    sec_base = df.resample(
        intervalo_base, on=col_fechahora)[col_precipitacion].agg({'size', 'sum'})
    
    # Agregar columna con lecturas correctas, basadas en evaluar "sum" y "size". 
    # Se vectoriza aparte de la agregación para optimizar velocidad.
    sec_base[TEXTOS['colcorrectas']] = \
        (sec_base['sum'] >= 0) & (sec_base['sum'] <= umbral_precipitacion) \
        & (sec_base['size'] == 1) 

    # Agregar columna con número de lecturas atípicas según parámetro (inicialmente 600)
    # Vectorizado para optimización.
    sec_base[TEXTOS['colatipicas']] = \
        (sec_base['sum'] > umbral_precipitacion) & (sec_base['size'] == 1)

    # Ahora agrupar por intervalo requerido y evaluar estadísticas de cada grupo
    sec_grupo = sec_base.resample(intervalo_grupo).apply(evaluar_grupo_lecturas)

    # Convertir serie en DataFrame
    df_resultado = sec_grupo.apply(lambda row: pd.Series(row)).reset_index()

    return df_resultado

# ---------------------------------------------------------------------------------------------
def controlar_duplicadas(df: pd.DataFrame, control: str) -> pd.DataFrame:
    # control: una de OPCIONES_DUPLICADAS. Cualquier otro valor no modifica.
    col_fechahora = df.columns[0]
    col_precipitacion = df.columns[1]
    if control == DUPLICADAS_PRIMERA:
        df = df.drop_duplicates(subset=col_fechahora, keep='first')
    elif control == DUPLICADAS_ULTIMA:
        df = df.drop_duplicates(subset=col_fechahora, keep='last')
    elif control == DUPLICADAS_SUMAR:
        df = df.groupby(col_fechahora, as_index=False).agg({
            col_fechahora     : 'first',
            col_precipitacion : 'sum',
        })
    elif control == DUPLICADAS_PROMEDIAR:
        df = df.groupby(col_fechahora, as_index=False).agg({
            col_fechahora     : 'first',
            col_precipitacion : 'mean',
        })
    elif control == DUPLICADAS_BORRAR:
        df = df.drop_duplicates(subset=col_fechahora, keep=False)

    return df

# ---------------------------------------------------------------------------------------------
def borrar_corruptas(df: pd.DataFrame) -> pd.DataFrame:
    col_precipitacion = df.columns[1]
    return df[df[col_precipitacion] >= 0]

# ---------------------------------------------------------------------------------------------
def borrar_atipicas(df: pd.DataFrame, umbral_atipicas: float) -> pd.DataFrame:
    col_precipitacion = df.columns[1]
    return df[df[col_precipitacion] <= umbral_atipicas]

# ---------------------------------------------------------------------------------------------
def rellenar_perdidas_con_cero(df: pd.DataFrame, intervalo: int) -> pd.DataFrame:
    col_fechahora = df.columns[0]
    df_relleno = relleno_perdidas(df, intervalo=f'{intervalo}min', relleno=0)
    if not df_relleno.empty:
        df = pd.concat(
            [df, df_relleno]
        ).sort_values(by=col_fechahora).reset_index(drop=True)
    return df

# ---------------------------------------------------------------------------------------------
def procesar_lecturas(
    df: pd.DataFrame,
    intervalo: int,
    control_duplicadas: str = None,
    corruptas_borrar: bool = False,
    atipicas_borrar: bool = False,
    umbral_atipicas: float = UMBRAL_ATIPICAS,
    perdidas_asumir_cero: bool = False,
) -> pd.DataFrame:
    # Aplica los controles de lecturas anormales en el mismo orden que la interfaz.
    # El control de perdidas debe ser el último pues los otros pueden borrar.
    if control_duplicadas is not None:
        df = controlar_duplicadas(df, control_duplicadas)
    if corruptas_borrar:
        df = borrar_corruptas(df)
    if atipicas_borrar:
        df = borrar_atipicas(df, umbral_atipicas)
    if perdidas_asumir_cero:
        df = rellenar_perdidas_con_cero(df, intervalo)
    return df

# ---------------------------------------------------------------------------------------------
def resumir_categorias(df_agrupado: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    # Totales y porcentajes por categoría de lectura
    suma_columnas = df_agrupado[LISTA_CATEGORIAS].sum(numeric_only=True) 
    porcentajes   = suma_columnas / suma_columnas.sum() * 100
    return suma_columnas, porcentajes

# ---------------------------------------------------------------------------------------------
def quedan_anormales(suma_columnas: pd.Series) -> bool:
    return bool((suma_columnas[LISTA_ANORMALES] > 0).any())

# =============================================================================================
# Eventos de precipitación
# =============================================================================================

# ---------------------------------------------------------------------------------------------
def consolidar_lecturas(
    df: pd.DataFrame, 
    fecha_inicial, fecha_final, 
    intervalo: int,
) -> pd.DataFrame:
    # Consolidar lecturas procesadas contiguas. Lecturas de CERO separan.

    col_fechahora     = df.columns[0]
    col_precipitacion = df.columns[1]
    fecha_inicial     = pd.to_datetime(fecha_inicial)
    fecha_final       = pd.to_datetime(fecha_final)

    df_consolidadas = df.loc[
        (df[col_fechahora] >= fecha_inicial) & (df[col_fechahora] <= fecha_final)
    ].copy()

    # Crear una columna adicional para marcar los cambios de 0 a otro valor y viceversa
    df_consolidadas['cambio'] = \
        (df_consolidadas[col_precipitacion] != 0) != \
        (df_consolidadas[col_precipitacion] != 0).shift(1)
    df_consolidadas['grupo'] = df_consolidadas['cambio'].cumsum()

    # Realizar la agregación basada en el grupo
    df_consolidadas = df_consolidadas.groupby('grupo').agg(
        inicia    = (col_fechahora, 'first'),
        termina   = (col_fechahora, 'last'),
        conteo    = (col_precipitacion, 'count'),
        P_acumulada = (col_precipitacion, 'sum'),
        lecturas  = (col_precipitacion, lambda p: p.tolist()),
    ).reset_index(drop=True)

    # Agregar coiumna de duracion
    lapso = df_consolidadas[TEXTOS['coltermina']] - df_consolidadas[TEXTOS['colinicia']]
    df_consolidadas[TEXTOS['colduracion']] = intervalo + lapso.dt.total_seconds() // 60
    
    return df_consolidadas

# ---------------------------------------------------------------------------------------------
def calcular_porcentajes(lecturas, factor=100):
    return (pd.Series(lecturas).cumsum() * factor / sum(lecturas)).to_list()

# ---------------------------------------------------------------------------------------------
def unir_precipitaciones(df: pd.DataFrame, pausa_maxima: int, incluir_pausa_igual: bool) -> pd.DataFrame:
    # Unifica precipitaciones según criterio de contiguidad.

    # Columna auxiliar para indicar si un evento es parte de lluvia continua o no
    if incluir_pausa_igual:
        df[TEXTOS['collluvia']] = \
            (df[TEXTOS['colpacumulada']] > 0) | \
            ((df[TEXTOS['colduracion']] <= pausa_maxima) & (df[TEXTOS['colpacumulada']] == 0))
    else:
        df[TEXTOS['collluvia']] = \
            (df[TEXTOS['colpacumulada']] > 0) | \
            ((df[TEXTOS['colduracion']] < pausa_maxima) & (df[TEXTOS['colpacumulada']] == 0))

    # Columna auxiliar para enumerar eventos continuos con un numero de secuencia
    df[TEXTOS['colsecuencia']] = \
        df[TEXTOS['collluvia']].ne(df[TEXTOS['collluvia']].shift()).cumsum()

    return df

# ---------------------------------------------------------------------------------------------
def determinar_cuartil_huff(acumulados):
    
    # Calcular valor de cuartiles
    Q = np.percentile(acumulados, [25, 50, 75]).tolist()

    # Calcula las diferencias entre los cuartiles
    deltas = [
        Q[0], 
        Q[1] - Q[0], 
        Q[2] - Q[1], 
        100  - Q[2]
    ]

    # Calcular índice del mayor delta para usarlo como clasificacion de tipo de curva Huff
    # El mayor delta indica que en ese lapso el aguacero tuvo su mayor precipitación
    # enumerate genera tuplas (indice, valor), key indica que max debe 
    # comparar por el segundo item de la tupla (x[1]), el valor que retorna 
    # max es una tupla (indice, valor mayor) asi que extraemos el
    # primer elemento [0], el del indice, para usarlo como categoria de cuartil
    indice_mayor_delta = max(enumerate(deltas), key=lambda x: x[1])[0]

    # Nombre del cuartil calculado. Empiezan en cero, el nombre debe empezar en 1
    Qname = f"Q{indice_mayor_delta + 1}"

    return Qname

# ---------------------------------------------------------------------------------------------
def calcular_eventos(
    df_consolidadas: pd.DataFrame,
    duracion_minima: int,
    duracion_maxima: int,
    pausa_maxima: int,
    intensidad_minima: int,
    intervalo: int,
    incluir_pausa_igual: bool = True,
) -> pd.DataFrame:

    # Consolidar eventos que se consideren contiguos
    df = unir_precipitaciones(df_consolidadas, pausa_maxima, incluir_pausa_igual)

    # Realizar la agregación basada en la secuencia de evento
    df = df.groupby(TEXTOS['colsecuencia']).agg(
        inicia      = (TEXTOS['colinicia'], 'first'),
        termina     = (TEXTOS['coltermina'], 'last'),
        lecturas    = (TEXTOS['collecturas'], lambda p: sum(p, [])),
        P_acumulada = (TEXTOS['colpacumulada'], 'sum'),
    )

    # Recalcular columna de duracion
    df[TEXTOS['colduracion']] = intervalo + \
        (df[TEXTOS['coltermina']] - df[TEXTOS['colinicia']]).dt.total_seconds() // 60

    # Agregar intensidad
    df[TEXTOS['colintensidad']] = \
        60 * df[TEXTOS['colpacumulada']] / df[TEXTOS['colduracion']]
    
    # Agregar conteo de mediciones
    df[TEXTOS['colconteo']] = df[TEXTOS['collecturas']].apply(len)

    # # Filtrar precipitaciones por P_acumulada
    df = df[
        (df[TEXTOS['colpacumulada']] > 0)
    ]

    # Filtrar por duracion
    df = df[
        (df[TEXTOS['colduracion']] >= duracion_minima) & \
        (df[TEXTOS['colduracion']] <= duracion_maxima)
    ]

    # # Filtrar por intensidad minima
    df = df[(df[TEXTOS['colintensidad']] >= intensidad_minima)]

    # Calcular y agregar porcentaje acumulado de mediciones
    df[TEXTOS['colporcentajes']] = df[TEXTOS['collecturas']].apply(calcular_porcentajes)

    # Calcular y agregar cuartil de Huff
    df['Q_Huff'] = \
        df[TEXTOS['colporcentajes']].apply(determinar_cuartil_huff)
    
    # Reordenar columnas
    df = df[[
        TEXTOS['colinicia'], TEXTOS['coltermina'], TEXTOS['colduracion'], 
        TEXTOS['colintensidad'], TEXTOS['colpacumulada'], TEXTOS['colconteo'], 
        TEXTOS['collecturas'], TEXTOS['colporcentajes'], 'Q_Huff',
    ]]

    return df.reset_index(drop=True)

# =============================================================================================
# Análisis de eventos
# =============================================================================================

# ---------------------------------------------------------------------------------------------
def calcular_curvas_huff(df, intervalo=5):
    datos_huff = pd.DataFrame()

    # Generar percentiles a partir de porcentajes de aguaceros
    # Usar intervalo especificado como argumento de la función
    datos_huff[TEXTOS['colpercentiles']] = df[TEXTOS['colporcentajes']].apply(
        lambda p: np.percentile(p, range(intervalo, 101, intervalo))
    )

    # Determinar cuartil de cada curva
    datos_huff['Q'] = df['Q_Huff']

    # Calcular curvas Huff como promedio de cada correspondiente valor de percentiles
    curvas_huff = datos_huff.groupby('Q').agg(
        {TEXTOS['colpercentiles']: lambda x: np.mean(list(zip(*x)), axis=1)}
    ).reset_index()

    # Agregar un cero al principio de cada lista en TEXTOS['colpercentiles']
    curvas_huff[TEXTOS['colpercentiles']] = curvas_huff[TEXTOS['colpercentiles']].apply(
        lambda x: [0] + list(x)
    )

    return curvas_huff

# ---------------------------------------------------------------------------------------------
def curva_frecuencia(df: pd.DataFrame, nombrecol: str) -> tuple[list, np.ndarray]:
    # Curva general: valores ordenados de mayor a menor vs probabilidad de excedencia (%)
    valores       = df[[nombrecol]].sort_values(nombrecol, ascending=False).values.flatten()
    num_valores   = len(valores)
    porcentajes_x = [(i + 1) / num_valores * 100 for i in range(num_valores)]
    return porcentajes_x, valores

# ---------------------------------------------------------------------------------------------
def tabla_frecuencia_interpolada(porcentajes_x, valores, nombrecol: str) -> pd.DataFrame:
    p_objetivos = np.array(list(range(1, 11)) + list(range(20, 101, 10)))
    xp = np.array(porcentajes_x)
    fp = np.array(valores)

    valores_interpolados = np.interp(p_objetivos, xp, fp)

    return pd.DataFrame({
        TEXTOS['labelprobabilidad'] : p_objetivos, 
        nombrecol : valores_interpolados,
    })

# ---------------------------------------------------------------------------------------------
def categorias_huff(df: pd.DataFrame):
    # Cuartiles Huff presentes, ordenados
    categorias = df['Q_Huff'].unique()
    categorias.sort()
    return categorias

# ---------------------------------------------------------------------------------------------
def curvas_frecuencia_por_categoria(df: pd.DataFrame, nombrecol: str) -> list[tuple]:
    # Lista de (categoria, porcentajes_x, valores) por cuartil Huff
    curvas = []
    for categoria in categorias_huff(df):
        valores = \
            df[df['Q_Huff'] == categoria][[nombrecol]].sort_values(nombrecol, ascending=False)
        num_valores = valores.shape[0]
        porcentajes_x = [(i + 1) / num_valores * 100 for i in range(num_valores)]
        curvas.append((categoria, porcentajes_x, valores))
    return curvas

# ---------------------------------------------------------------------------------------------
def limites_intensidad(df_eventos: pd.DataFrame) -> tuple[int, int]:
    intensidad_min = floor(df_eventos[TEXTOS['colintensidad']].min())
    intensidad_max = ceil(df_eventos[TEXTOS['colintensidad']].max())
    return intensidad_min, intensidad_max

# ---------------------------------------------------------------------------------------------
def calcular_rangos_intensidad(
    df_eventos: pd.DataFrame, 
    num_rangos: int,
    intensidad_min: int,
    intensidad_max: int,
):
    # Retorna (rangos, conteo_por_categoria, categorias)
    magnitud_rango = (intensidad_max - intensidad_min) / num_rangos
    limites_rangos = \
        [trunc(intensidad_min + i * magnitud_rango) for i in range(num_rangos + 1)]
    rangos = \
        [(limites_rangos[i], limites_rangos[i + 1]) for i in range(num_rangos)]

    df = df_eventos[['Q_Huff', TEXTOS['colintensidad']]].copy()

    df[TEXTOS['colrango']] = pd.cut(
        df_eventos[TEXTOS['colintensidad']],
        bins=limites_rangos,
        labels=[f'{t}' for t in rangos],
    )

    conteo_por_categoria = df.groupby(['Q_Huff', TEXTOS['colrango']], observed=False).size()
    categorias = categorias_huff(df)

    return rangos, conteo_por_categoria, categorias

# ---------------------------------------------------------------------------------------------
def calcular_acumulados_por_lapso(evento, lapsos):
    inicia     = evento[TEXTOS['colinicia']]
    duracion   = evento[TEXTOS['colduracion']]
    lecturas   = np.array(evento[TEXTOS['collecturas']])
    acumulados = lecturas.cumsum()
    conteo_lecturas = len(lecturas)
    intervalo_lecturas = duracion / conteo_lecturas
    lista_acumulados_por_lapso = [inicia]
    for lapso in lapsos:
        conteo_en_lapso = int(lapso / intervalo_lecturas)
        if (lapso < intervalo_lecturas) or (conteo_en_lapso > conteo_lecturas):
            lista_acumulados_por_lapso.append(np.nan)
            continue
        acumulado_lapso = acumulados[conteo_en_lapso - 1]
        lista_acumulados_por_lapso.append(acumulado_lapso)
    return pd.Series(
        data=lista_acumulados_por_lapso, 
        index=[TEXTOS['colinicia'], *[f'lapso {d} min' for d in lapsos]],
    )

# ---------------------------------------------------------------------------------------------
def obtener_acumulados(df: pd.DataFrame, lapsos: list[int] = None) -> pd.DataFrame:
    resultado = df.apply(
        calcular_acumulados_por_lapso, 
        axis=1,
        lapsos=LAPSOS_ACUMULADOS if lapsos is None else lapsos,
    )

    return resultado
