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

from mensajes_es import MENSAJES
import streamlit as st
import pandas as pd
from io import BytesIO
import re

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
    nombre_col = st.sidebar.selectbox(prompt, lista_columnas, index=None)
    if len(lista_columnas) < 1:
        st.sidebar.warning(MENSAJES['errortipocols'](tipos_validos))
        return None
    if nombre_col is None:
        return None
    return nombre_col

# ---------------------------------------------------------------------------------------------
# Verificar explícitamente si hay columnas tipo object (strings) 
# que no se pueden convertir a tipo fechahora por errores de formato
def buscar_errores_fechahora(df):
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
        value=10, step=100,
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
def estimar_intervalo_lecturas(df: pd.DataFrame) -> float:
    # Calcular intervalo con la moda de los delta_t entre los primeros registros
    try:
        col_t = df.columns[0]
        s_delta_t = pd.to_timedelta(df[col_t].head(1000).diff().fillna(0))
        moda_dt = s_delta_t.mode()[0]
        intervalo = moda_dt.total_seconds() / 60
    except:
        intervalo = 0
    return intervalo

# ---------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=MENSAJES['stcachespinner'])
def agrupar_lecturas(df: pd.DataFrame, frecuencia: str) -> pd.DataFrame:
    col_fechahora = df.columns[0]
    col_precipitacion = df.columns[1]
    agrupacion = pd.Grouper(key=col_fechahora, freq=frecuencia)
    funcion_agregacion = {col_precipitacion: 'sum'}  
    return df.groupby(agrupacion).agg(funcion_agregacion).reset_index()
    
# ---------------------------------------------------------------------------------------------
def desplegar_lecturas(df: pd.DataFrame):
    col_fechahora = df.columns[0]
    col_precipitacion = df.columns[1]

    zona_stats = st.container(border=False)
    zona_visual = st.container(border=True)
    zona_params, zona_grafico = zona_visual.columns([0.3, 0.7])
    zona_tablas = st.container(border=True)
    zona_lecturas, zona_agrupadas = zona_tablas.columns(2)


    # Estadísticas ----------------------------------------------------------------------------
    intervalo = estimar_intervalo_lecturas(df)
    num_totales = df.shape[0]
    num_correctas = df[df[col_precipitacion] >= 0].shape[0]

    stats = {'Estadística' : [], 'Valor' : []} 

    stats['Estadística'].append('Intervalo')
    stats['Valor'].append(f'{intervalo} minutos')

    stats['Estadística'].append('Lecturas totales')
    stats['Valor'].append(f'{num_totales}')

    stats['Estadística'].append('Lecturas correctas (P<=0)')
    stats['Valor'].append(f'{num_correctas} ({num_correctas / num_totales :.2%})')

    df_stats = pd.DataFrame(stats)
    zona_stats.dataframe(df_stats, hide_index=True, width=400)

    # Visualización ---------------------------------------------------------------------------
    agrupaciones = {'Hora' : 'h', 'Dia' : 'D', 'Semana' : 'W', 'Mes' : 'ME', 'Año' : 'YE'}
    criterio = zona_params.select_slider(
        'Criterio de agrupación', 
        options=list(agrupaciones.keys()),
        value='Dia',
    )
    df_agrupado = agrupar_lecturas(df, agrupaciones[criterio])
    zona_grafico.scatter_chart(
        data=df_agrupado, x=col_fechahora, y=col_precipitacion, size=30,
    )

    # Tablas ----------------------------------------------------------------------------------
    zona_lecturas.subheader('Lecturas individuales')
    num_lecturas = zona_lecturas.slider(
        MENSAJES['previsualcantidad'], key='num_enlecturas',
        min_value=10, max_value=df.shape[0], value=10, step=10,
    )
    zona_lecturas.dataframe(
        df.head(num_lecturas), hide_index=True, use_container_width=True,
    )

    zona_agrupadas.subheader(f'Lecturas agrupadas ({criterio})')
    num_agrupadas = zona_agrupadas.slider(
        MENSAJES['previsualcantidad'], key='num_enagrupadas',
        min_value=10, max_value=df_agrupado.shape[0], value=10, step=10,
    )
    zona_agrupadas.dataframe(
        df_agrupado.head(num_agrupadas), hide_index=True, use_container_width=True,
    )


    return

    reemplazar_incorrectas = zona_params.checkbox('Asumir CERO en lecturas incorrectas')
    if reemplazar_incorrectas: 
        # TODO: ofrecer con selectbox varias opciones de relleno (0, -1, minimo, maximo, promedio...)
        df.loc[df[col_precipitacion] == -1, col_precipitacion] = 0 # Cambiar lecturas no válidas a 0

    # -----------------------------------------------------------------------------------------
    # todo: revisar si hay que calcular con acumulado o full. creo que acum
    # todo: o revisar si solo se usa el acum para la graficaque ya estoy dormido



    # Cambiar lecturas no válidas a -1
    df_acumulado.loc[df_acumulado[col_precipitacion] < 0, col_precipitacion] = -1 

# =============================================================================================
# Sección principal
# =============================================================================================

inicializar()

zona_descripcion = st.empty()
zona_mensajes = st.empty()
lista_tabs = [
    MENSAJES['tabarchivo'],
    MENSAJES['tablecturas'],
]
tab_archivo, tab_lecturas = st.tabs(lista_tabs)

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
with tab_lecturas:
    desplegar_lecturas(df_lecturas)
