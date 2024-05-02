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
    st.subheader(MENSAJES['appdescription'])

# ---------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=MENSAJES['stcachespinner'])
def cargar_archivo_de_cache(archivo_io: BytesIO) -> pd.DataFrame:
    try:
        df = pd.read_csv(archivo_io)
    except:
        df = None
    return df

# ---------------------------------------------------------------------------------------------
def verificar_archivo_lecturas(df: pd.DataFrame) -> bool:
    return (df is not None) and (df.shape[1] >= 2)

# ---------------------------------------------------------------------------------------------
def obtener_lecturas() -> pd.DataFrame:
    archivo_lecturas = st.sidebar.file_uploader(
        MENSAJES['fileuploaderprompt'], type=['csv'], help=MENSAJES['fileuploaderhelp']
    )
    if archivo_lecturas is None:
        return None
    df = cargar_archivo_de_cache(archivo_lecturas)
    if not verificar_archivo_lecturas(df):
        st.sidebar.error(MENSAJES['errorlecturas'])
        return None
    else:
        return df

# ---------------------------------------------------------------------------------------------
def elegir_nombre_columna(prompt: str, tipos_validos: list[str], df: pd.DataFrame) -> str:
    lista_columnas = list(df.columns)
    nombre_col = st.sidebar.selectbox(prompt, lista_columnas, index=None)
    if nombre_col is None:
        return None
    tipo_col = df[nombre_col].dtype
    if tipo_col not in tipos_validos:
        st.sidebar.error(MENSAJES['errortipocolumna'])
        return None
    return nombre_col

# =============================================================================================
# Sección principal
# =============================================================================================

inicializar()

zona_mensajes = st.empty()
tab_archivo, tab_lecturas = st.tabs(['Archivo', 'Lecturas'])

# ---------------------------------------------------------------------------------------------
df_lecturas = obtener_lecturas()
if df_lecturas is None:
    zona_mensajes.info(MENSAJES['nohaylecturas'])
    st.stop()
else:
    with tab_archivo:
        st.write(MENSAJES['previsualizararchivo'])
        st.caption(MENSAJES['shapelecturas'](df_lecturas.shape))
        c1, c2, c3 = st.columns([0.2, 0.4, 0.4])
        c1.dataframe(df_lecturas.dtypes, column_config={'': 'Columna', '0': 'Tipo'})
        c2.dataframe(df_lecturas.head(50))
        c3.dataframe(df_lecturas.tail(50))

# ---------------------------------------------------------------------------------------------
col_fechahora = elegir_nombre_columna(
    prompt=MENSAJES['elegircolfechahora'], 
    tipos_validos=['object', 'datetime64'],
    df=df_lecturas
)
if (col_fechahora is None):
    zona_mensajes.info(MENSAJES['elegircolfechahora'])
    st.stop()

# ---------------------------------------------------------------------------------------------
col_precipitacion = elegir_nombre_columna(
    prompt=MENSAJES['elegircolprecipitacion'], 
    tipos_validos=['int64', 'float64'],
    df=df_lecturas
)
if (col_precipitacion is None):
    zona_mensajes.info(MENSAJES['elegircolprecipitacion'])
    st.stop()

# ---------------------------------------------------------------------------------------------
if (col_fechahora == col_precipitacion):
    st.sidebar.error(MENSAJES['elegircolsdiferentes'])
    st.stop()

# ---------------------------------------------------------------------------------------------
tab_lecturas.dataframe(df_lecturas[[col_fechahora, col_precipitacion]])