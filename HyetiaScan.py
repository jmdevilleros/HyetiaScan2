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
    st.write(MENSAJES['appdescription'])

# ---------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=MENSAJES['stcachespinner'])
def cargar_archivo_de_cache(archivo_io: BytesIO) -> pd.DataFrame:
    try:
        df_origen = pd.read_csv(archivo_io)
    except:
        df_origen = None
    return df_origen

# ---------------------------------------------------------------------------------------------
def verificar_archivo_lecturas(df: pd.DataFrame) -> bool:
    return (df is not None) and (df.shape[1] >= 2)

# ---------------------------------------------------------------------------------------------
def obtener_lecturas() -> pd.DataFrame:
    with st.sidebar:
        # Obtener archivo fuente de datos de precipitación (lecturas)
        archivo_lecturas = st.file_uploader(
            MENSAJES['fileuploaderprompt'], type=['csv'], 
            help=MENSAJES['fileuploaderhelp']
        )
    if archivo_lecturas is None:
        return None
    df = cargar_archivo_de_cache(archivo_lecturas)
    if not verificar_archivo_lecturas(df):
        st.sidebar.error(MENSAJES['errorlecturas'])
        return None
    else:
        st.sidebar.caption(MENSAJES['shapelecturas'](df.shape))
        return df

# ---------------------------------------------------------------------------------------------
def obtener_col_fechahora(lista_columnas: list[str]) -> str:
    columna = st.sidebar.selectbox('Fecha-hora', lista_columnas, index=None)
    return columna

# ---------------------------------------------------------------------------------------------
def obtener_col_precipitacion(lista_columnas: list[str]) -> str:
    columna =  st.sidebar.selectbox('Precipitacion', lista_columnas, index=None)
    return columna

# =============================================================================================
# Sección principal
# =============================================================================================

inicializar()
df_lecturas = obtener_lecturas()
if df_lecturas is None:
    st.info(MENSAJES['nohaylecturas'])
    st.stop()

lista_columnas = list(df_lecturas.columns)
col_fechahora = obtener_col_fechahora(lista_columnas)
if (col_fechahora is None):
    st.info(MENSAJES['elegircolfechahora'])
    st.stop()

col_precipitacion = obtener_col_precipitacion(lista_columnas)
if (col_precipitacion is None):
    st.info(MENSAJES['elegircolprecipitacion'])
    st.stop()

if st.toggle('Ver contenido'):
    st.dataframe(df_lecturas[[col_fechahora, col_precipitacion]])