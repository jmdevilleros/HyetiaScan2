# *********************************************************************************************
# HyetiaScan
# Análisis de lluvias
# Juan Manuel de Villeros Arias
# Mónica Liliana Gallego Jaramillo
# Mayo 2024
#
# Archivo: HyetiaScan.py - Punto de entrada a aplicación Streamlit
# *********************************************************************************************

# =============================================================================================
# Bibliotecas
# =============================================================================================

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import re

from mensajes_es import MENSAJES

# =============================================================================================
# Globales
# =============================================================================================

# =============================================================================================
# Procedimientos y funciones
# =============================================================================================

# ---------------------------------------------------------------------------------------------
def inicializar():
    if 'iniciado' not in st.session_state:
        st.session_state.iniciado = True
        st.set_page_config(
            page_title=f'{MENSAJES["appname"]} {MENSAJES["appversion"]}', 
            layout='wide', 
            initial_sidebar_state='expanded', 
            page_icon=':rain_cloud:',
            menu_items={'About' : MENSAJES['about']}
        )
    st.sidebar.subheader(f':blue[{MENSAJES["appname"]} {MENSAJES["appversion"]}] :rain_cloud:')
    st.sidebar.caption(MENSAJES['appdescription'])

# ---------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=MENSAJES['stcachespinner'])
def cargar_archivo_de_cache(archivo: BytesIO, decimal: str, codificacion: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(
            archivo, 
            decimal=decimal, 
            encoding=codificacion, 
            parse_dates=True, 
            engine='pyarrow',
        )
    except Exception as ex:
        st.sidebar.error(ex)
        return None
    return df

# ---------------------------------------------------------------------------------------------
def verificar_lecturas_cargadas(df: pd.DataFrame) -> bool:
    # Mínimo dos registros y dos columnas
    return (df is not None) and (df.shape[1] >= 2) and (df.shape[0] >= 2)

# ---------------------------------------------------------------------------------------------
def obtener_archivo_lecturas() -> tuple[pd.DataFrame, str]:
    tab_carga, tab_config = st.sidebar.tabs([MENSAJES['tabcarga'], MENSAJES['tabconfig']])
    with tab_config:
        decimal = st.radio(
            MENSAJES['elegirdecimal'], 
            options=['.', ','], 
            captions=['Punto', 'Coma'],
            horizontal=True,
        )
        codificacion = st.selectbox(
            MENSAJES['elegircodificacion'],
            options=['utf-8', 'utf-16', 'utf-32', 'latin-1', 'iso-8859-1', 'ascii'],
        )
        st.divider()

    archivo = tab_carga.file_uploader(
        ' ', type=['csv'], help=MENSAJES['fileuploaderhelp'], label_visibility='collapsed',
    )
    if archivo is None:
        return None, None
    
    df = cargar_archivo_de_cache(archivo, decimal=decimal, codificacion=codificacion)
    if not verificar_lecturas_cargadas(df):
        st.sidebar.error(MENSAJES['errorlecturas'])
        return None, None

    return df, archivo.name

# ---------------------------------------------------------------------------------------------
def elegir_nombre_columna(prompt: str, tipos_validos: list[str], df: pd.DataFrame) -> str:
    lista_columnas = df.select_dtypes(include=tipos_validos).columns
    nombre_col = st.sidebar.selectbox(prompt, lista_columnas, index=0)
    if len(lista_columnas) < 1:
        st.sidebar.warning(MENSAJES['errortipocols'](tipos_validos))
        return None
    if nombre_col is None:
        return None
    return nombre_col

# ---------------------------------------------------------------------------------------------
def buscar_errores_fechahora(df):
    # Verificar explícitamente si hay columnas tipo object (strings) 
    # que no se pueden convertir a tipo fechahora por errores de formato
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
        st.error(MENSAJES['errorfechahora'](col, indice, f':orange[{valor_fechahora}]'))

# ---------------------------------------------------------------------------------------------
def desplegar_archivo(df: pd.DataFrame):
    st.write(MENSAJES['previsualarchivo'])

    if sum(df.dtypes == 'datetime64') < 1: 
        buscar_errores_fechahora(df) 

    c1, c2 = st.columns([0.3, 0.7])

    # Obtener columnas y sus tipos (df.dtypes genera warnings)
    tipos_columna = pd.DataFrame({
        MENSAJES['previsualcolnom']: df.dtypes.index,
        MENSAJES['previsualtipnom']: df.dtypes.values.astype(str)
    })
    c1.dataframe(tipos_columna, hide_index=True, use_container_width=True)

    c1.divider()

    # Mostrar cantidad de registros deseados
    num_vista = c1.slider(
        MENSAJES['previsualcantidad'], 
        min_value=10, max_value=df.shape[0], 
        value=10, step=int(df.shape[0] / 100) + 1,
        key='num_enarchivo',
    )
    c2.dataframe(
        df.head(num_vista), 
        use_container_width=True,
        column_config={'_index': MENSAJES['previsualindice']},
    )

# ---------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=MENSAJES['stcachespinner'])
def extraer_lecturas(df: pd.DataFrame, col1: str, col2: str) -> pd.DataFrame:
    return df[[col1, col2]].copy()

# ---------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=MENSAJES['stcachespinner'])
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
def evaluar_grupo_lecturas(grupo: pd.Series) -> pd.Series:
    acumulado  = grupo['sum'][grupo['sum'] > 0].sum()
    correctas  = grupo['correctas'].sum()
    perdidas   = grupo['size'][grupo['size'] == 0].count()
    duplicadas = grupo['size'][grupo['size'] > 1].sum()  # sum() en vez de count() para contar todas
    corruptas  = grupo['sum'][grupo['sum'] < 0].count()
    return {
        'acumulado'  : acumulado, 
        'correctas'  : correctas, 
        'perdidas'   : perdidas, 
        'duplicadas' : duplicadas, 
        'corruptas'  : corruptas,
    }

# ---------------------------------------------------------------------------------------------
def relleno_perdidas(df: pd.DataFrame, intervalo: str, relleno: int = 0) -> pd.DataFrame:
    col_fechahora = df.columns[0]
    serie = df.resample(intervalo, on=col_fechahora).first()
    df_perdidas =  serie[serie.isnull().any(axis=1)].fillna(relleno).reset_index()
    return df_perdidas

# ---------------------------------------------------------------------------------------------
#@st.cache_data(show_spinner=MENSAJES['stcachespinner'])
def agrupar_lecturas(df: pd.DataFrame, intervalo_base: str, intervalo_grupo: str) -> pd.DataFrame:
    col_fechahora = df.columns[0]
    col_precipitacion = df.columns[1]

    # Generar secuencia de tiempo con el mismo intervalo para rellenar posibles vacíos
    # y generar valores de conteo "size" y "sum" para detección de valores anormales.
    sec_base = df.resample(intervalo_base, on=col_fechahora)[col_precipitacion].agg({'size', 'sum'})

    # Agregar columna con lecturas correctas, basadas en evaluar "sum" y "size". 
    # Se vectoriza aparte de la agregación para optimizar velocidad.
    sec_base['correctas'] =  (sec_base['sum'] >= 0) & (sec_base['size'] == 1)

    # Ahora agrupar por intervalo requerido y evaluar estadísticas de cada grupo
    sec_grupo = sec_base.resample(intervalo_grupo).apply(evaluar_grupo_lecturas)

    # Convertir serie en DataFrame
    df_resultado = sec_grupo.apply(lambda row: pd.Series(row)).reset_index()

    return df_resultado

# ---------------------------------------------------------------------------------------------
def ver_dataframe(df: pd.DataFrame, titulo: str = None):
    if titulo:
        st.write(titulo)
    cantidad = st.slider(
        MENSAJES['previsualcantidad'],
        min_value=0, 
        max_value=df.shape[0], 
        value=10, 
        step=int(df.shape[0] / 100) + 1,
        key=f'slider_{titulo}'
    )
    st.dataframe(df.head(cantidad), hide_index=True, use_container_width=True,)

# ---------------------------------------------------------------------------------------------
def desplegar_lecturas(df_individuales: pd.DataFrame, intervalo: float) -> pd.DataFrame : 
    col_fechahora = df_individuales.columns[0]
    col_precipitacion = df_individuales.columns[1]
    agrupaciones = {'Dia' : 'D', 'Mes' : 'ME', 'Año' : 'YE'}
    lista_categorias = ['correctas', 'perdidas', 'duplicadas', 'corruptas']
    lista_anormales = lista_categorias[1:]

    st.write(f'Intervalo entre lecturas individuales: {intervalo} minutos')

    # Preparar zonas de visualización ---------------------------------------------------------
    with st.container(border=True):
        zona_grafico_agrupadas, zona_metricas = st.columns([0.7, 0.3])
    with st.container(border=True):
        zona_categorias, zona_control = st.columns([0.7, 0.3], gap='medium')
    with st.expander('Detalle de lecturas', expanded=False):
        zona_detalle_agrupadas, zona_detalle_individuales = st.columns([0.7, 0.3], gap='medium')

    # -----------------------------------------------------------------------------------------
    # Controles deben ir antes de visualizaciones, pues modifican dataframe
    zona_control.write('Control de lecturas anormales:')

    # Control de duplicadas -------------------------------------------------------------------
    control_duplicadas = zona_control.radio(
        f'Duplicadas por [{col_fechahora}]', 
        options=['No modificar', 'Dejar primera', 'Dejar última', 'Borrar'], horizontal=True,
    )
    match control_duplicadas:
        case 'Dejar primera': 
            df_individuales = df_individuales.drop_duplicates(subset=col_fechahora, keep='first')
        case 'Dejar última':
            df_individuales = df_individuales.drop_duplicates(subset=col_fechahora, keep='last')
        case 'Borrar':
            df_individuales = df_individuales.drop_duplicates(subset=col_fechahora, keep=False)

    # Control corruptas -----------------------------------------------------------------------
    control_corruptas = zona_control.radio(f'Corruptas en [{col_precipitacion}]', 
        options=['No modificar', 'Asumir cero', 'Borrar'], horizontal=True,
    )
    match control_corruptas:
        case 'Asumir cero':
            df_individuales[col_precipitacion] = df_individuales[col_precipitacion].clip(lower=0)
        case 'Borrar':
            df_individuales = df_individuales[df_individuales[col_precipitacion] >= 0]

    # Control de perdidas ---------------------------------------------------------------------
    # Debe ser el último contgrol pues los otros pueden borrar
    control_perdidas = zona_control.radio(
        'Perdidas', options=['No modificar', 'Asumir cero'], horizontal=True,
    )
    match control_perdidas:
        case 'Asumir cero':
            df_relleno = relleno_perdidas(df_individuales, intervalo=f'{intervalo}min', relleno=0)
            if not df_relleno.empty:
                df_individuales = pd.concat(
                    [df_individuales, df_relleno]
                ).sort_values(by=col_fechahora).reset_index(drop=True)

    # Generar datos agrupados según criterio y calcular métricas -------------------------------
    criterio = zona_grafico_agrupadas.radio('Lecturas agrupadas', 
        options=list(agrupaciones.keys()), index=1, horizontal=True,
    )
    df_agrupado   = agrupar_lecturas(
        df_individuales, intervalo_base=f'{intervalo}min', intervalo_grupo=agrupaciones[criterio],
    )
    suma_columnas = df_agrupado[lista_categorias].sum(numeric_only=True) 
    porcentajes   = suma_columnas / suma_columnas.sum() * 100
    metricas = [
        f'{label}: {value:.0f} ({porcentaje:.2f}%)' 
        for label, value, porcentaje in zip(suma_columnas.index, suma_columnas, porcentajes)
    ]

    # Mostrar gráfico de precipitaciones ------------------------------------------------------
    zona_grafico_agrupadas.line_chart(df_agrupado, x=col_fechahora, y='acumulado')

    # Mostrar gráfico de categoria de lecturas -----------------------------------------------
    categorias_elegidas = zona_categorias.multiselect(
        'Categorías de lecturas', options=lista_categorias, default=lista_anormales,
    )
    zona_categorias.bar_chart(df_agrupado, x=col_fechahora, y=categorias_elegidas)

    # Diagrama de tarta con métricas ----------------------------------------------------------
    fig, ax = plt.subplots()
    pie = ax.pie(suma_columnas)
    plt.legend(pie[0], metricas, fontsize='medium', loc='lower center')
    fig.patch.set_alpha(0)
    zona_metricas.pyplot(fig)

    # Detalle de lecturas ---------------------------------------------------------------------
    with zona_detalle_agrupadas:
        ver_dataframe(df_agrupado, f'Detalle lecturas agrupadas ({criterio})')
    with zona_detalle_individuales:
        ver_dataframe(df_individuales, 'Detalle lecturas individuales')

    # Verificar si aún quedan valores anormales por procesar ----------------------------------
    if (suma_columnas[lista_anormales] > 0).any():
        return None
    
    # -----------------------------------------------------------------------------------------
    return df_individuales

# ---------------------------------------------------------------------------------------------
def calcular_eventos(df_procesadas: pd.DataFrame, intervalo: float):
    st.write('Aca cálculo de eventos')

    return

# =============================================================================================
# Sección principal
# =============================================================================================

inicializar()

zona_descripcion = st.empty()
zona_mensajes = st.empty()
lista_tabs = [
    MENSAJES['tabarchivo'],
    MENSAJES['tablecturas'],
    MENSAJES['tabeventos']
]
tab_archivo, tab_lecturas, tab_eventos = st.tabs(lista_tabs)

# ---------------------------------------------------------------------------------------------
df_archivo, nombre_archivo = obtener_archivo_lecturas()
if df_archivo is None:
    zona_mensajes.info(MENSAJES['elegirarchivo'])
    st.stop()

# ---------------------------------------------------------------------------------------------
zona_descripcion.subheader(nombre_archivo)
with tab_archivo:
    desplegar_archivo(df_archivo)

# ---------------------------------------------------------------------------------------------
col_fechahora = elegir_nombre_columna(
    prompt=MENSAJES['elegircolfechahora'], 
    tipos_validos=['datetime64'],
    df=df_archivo,
)
if (col_fechahora is None):
    zona_mensajes.info(MENSAJES['elegircolfechahora'])
    st.stop()

# ---------------------------------------------------------------------------------------------
col_precipitacion = elegir_nombre_columna(
    prompt=MENSAJES['elegircolprecipitacion'], 
    tipos_validos=['int64', 'float64'],
    df=df_archivo
)
if (col_precipitacion is None):
    zona_mensajes.info(MENSAJES['elegircolprecipitacion'])
    st.stop()

# ---------------------------------------------------------------------------------------------
st.sidebar.success(MENSAJES['columnasok'])
df_lecturas = extraer_lecturas(df_archivo, col_fechahora, col_precipitacion)

intervalo = estimar_intervalo_lecturas(df_lecturas)

with tab_lecturas:
    df_lecturas_procesadas = desplegar_lecturas(df_lecturas, intervalo)

with tab_eventos:
    if df_lecturas_procesadas is None:
        st.warning('Aún quedan lecturas anormales por controlar.')
        st.stop()

    calcular_eventos(df_lecturas_procesadas, intervalo)
