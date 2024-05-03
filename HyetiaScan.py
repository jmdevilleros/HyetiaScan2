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
def cargar_archivo_de_cache(archivo_io: BytesIO, decimal: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(archivo_io, decimal=decimal)
    except:
        df = None
    
    # Intentar deteccion de tipos fecha
    for col in df.select_dtypes(include='object'): 
        try:
            df[col] = pd.to_datetime(df[col])
        except:
            pass

    return df

# ---------------------------------------------------------------------------------------------
def verificar_lecturas_cargadas(df: pd.DataFrame) -> bool:
    # Mínimo dos registros y dos columnas
    return (df is not None) and (df.shape[1] >= 2) and (df.shape[0] >= 2)

# ---------------------------------------------------------------------------------------------
def obtener_archivo_lecturas() -> pd.DataFrame:
    tab_carga, tab_config = st.sidebar.tabs(['Cargar archivo', 'Configurar carga'])
    with tab_config:
        decimal = st.radio(
            'Separador decimal', 
            options=['.', ','], 
            captions=['Punto', 'Coma'],
            horizontal=True,
        )
        st.divider()
    archivo = tab_carga.file_uploader(
        ' ', type=['csv'], help=MENSAJES['fileuploaderhelp'], label_visibility='collapsed'
    )
    if archivo is None:
        return None
    df = cargar_archivo_de_cache(archivo, decimal=decimal)
    if not verificar_lecturas_cargadas(df):
        st.sidebar.error(MENSAJES['errorlecturas'])
        return None

    return df

# ---------------------------------------------------------------------------------------------
def elegir_nombre_columna(prompt: str, tipos_validos: list[str], df: pd.DataFrame) -> str:
    lista_columnas = df.select_dtypes(include=tipos_validos).columns #list(df.columns)
    nombre_col = st.sidebar.selectbox(prompt, lista_columnas, index=0)
    if nombre_col is None:
        return None
    tipo_col = df[nombre_col].dtype
    if tipo_col not in tipos_validos:
        st.sidebar.error(MENSAJES['errortipocolumna'])
        return None
    return nombre_col

# ---------------------------------------------------------------------------------------------
def extraer_error_fechahora(mensaje_error):
    buscar_fechas_fallidas = re.findall(r'\"(.*?)\"', mensaje_error)
    if len(buscar_fechas_fallidas) > 0:
        fecha_fallida = buscar_fechas_fallidas[0]
        position = re.findall(r'position (\d+)', mensaje_error)[0]
        return fecha_fallida, int(position)
    else:
        return mensaje_error, 0

# =============================================================================================
# Sección principal
# =============================================================================================

inicializar()

zona_mensajes = st.empty()
lista_tabs = [
    MENSAJES['tabarchivo'],
    MENSAJES['tablecturas'],
    'Eventos',
    'Gráficas',
]
tab_archivo, tab_lecturas, tab_eventos, tab_graficas = st.tabs(lista_tabs)

# ---------------------------------------------------------------------------------------------
df_archivo = obtener_archivo_lecturas()
if df_archivo is None:
    zona_mensajes.info(MENSAJES['elegirarchivo'])
    st.stop()
else:
    with tab_archivo:
        # TODO: mostrar nombre de archivo
        st.write(MENSAJES['previsualarchivo'])
        st.caption(MENSAJES['shapelecturas'](df_archivo.shape))
        zona_msg_archivo = st.empty()
        c1, c2, c3 = st.columns([0.2, 0.4, 0.4])
        num_vista = c1.slider(
            ' ', min_value=10, max_value=df_archivo.shape[0], value=10, step=100, 
            label_visibility='collapsed',
        )
        c1.dataframe(
            df_archivo.dtypes, 
            column_config={'': MENSAJES['previsualcolnom'], '0': MENSAJES['previsualtipnom']}
        )
        c2.dataframe(df_archivo.head(num_vista))
        c3.dataframe(df_archivo.tail(num_vista)[::-1])  # Mostrar al revés

# ---------------------------------------------------------------------------------------------
# Detectar si se encontraron columnas de fecha-hora
if sum(df_archivo.dtypes == 'datetime64[ns]') < 1:
    st.sidebar.warning('No se detectan columnas de tipo fecha-hora (datetime64[ns])')
    try:
        for col in df_archivo.select_dtypes(include='object'): 
            temp_col = pd.to_datetime(df_archivo[col])
    except ValueError as ve:
        val, reg = extraer_error_fechahora(str(ve))    
        zona_msg_archivo.error(f'Error en registro {reg}: [:orange[{val}]].')    
    st.stop()

# ---------------------------------------------------------------------------------------------
# Detectar si se encontraron columnas apropiadas de precipitación
tipos_numericos = ['int64', 'float64']
columnas_numericas = df_archivo.select_dtypes(include=tipos_numericos).columns

if len(columnas_numericas) < 1:
    zona_mensajes.warning('No se detectan columnas de tipo numérico.')
    st.stop()

# ---------------------------------------------------------------------------------------------
col_fechahora = elegir_nombre_columna(
    prompt=MENSAJES['elegircolfechahora'], 
    tipos_validos=['datetime64[ns]'],
    df=df_archivo
)
if (col_fechahora is None):
    zona_mensajes.info(MENSAJES['elegircolfechahora'])
    st.stop()

# ---------------------------------------------------------------------------------------------
col_precipitacion = elegir_nombre_columna(
    prompt=MENSAJES['elegircolprecipitacion'], 
    tipos_validos=tipos_numericos,
    df=df_archivo
)
if (col_precipitacion is None):
    zona_mensajes.info(MENSAJES['elegircolprecipitacion'])
    st.stop()

# ---------------------------------------------------------------------------------------------
if (col_fechahora == col_precipitacion):
    st.sidebar.error(MENSAJES['elegircolsdiferentes'])
    st.stop()

# ---------------------------------------------------------------------------------------------
st.sidebar.success(MENSAJES['columnasok'])
df_lecturas = df_archivo[[col_fechahora, col_precipitacion]].copy()
c1, c2, c3 = tab_lecturas.columns(3)
c1.latex(r'''
    \sum_{k=0}^{n-1} ar^k =
    a \left(\frac{1-r^{n}}{1-r}\right)
    ''')
c1.latex(r'''
    \sum_{k=0}^{n-1} ar^k =
    a \left(\frac{1-r^{n}}{1-r}\right)
    ''')
c1.latex(r'''
    \sum_{k=0}^{n-1} ar^k =
    a \left(\frac{1-r^{n}}{1-r}\right)
    ''')
c2.write(df_lecturas.describe())
c3.dataframe(df_lecturas)