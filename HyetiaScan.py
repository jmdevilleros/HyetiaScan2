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
        df = pd.read_csv(archivo_io)
    except:
        df = None
    return df

# ---------------------------------------------------------------------------------------------
def verificar_lecturas_cargadas(df: pd.DataFrame) -> bool:
    # Mínimo dos registros y dos columnas
    return (df is not None) and (df.shape[1] >= 2) and (df.shape[0] >= 2)

# ---------------------------------------------------------------------------------------------
def obtener_archivo_lecturas() -> pd.DataFrame:
    archivo = st.sidebar.file_uploader(
        '', type=['csv'], help=MENSAJES['fileuploaderhelp'], label_visibility='collapsed'
    )
    if archivo is None:
        return None
    df = cargar_archivo_de_cache(archivo)
    if not verificar_lecturas_cargadas(df):
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
        st.write(MENSAJES['previsualarchivo'])
        st.caption(MENSAJES['shapelecturas'](df_archivo.shape))
        c1, c2, c3 = st.columns([0.2, 0.4, 0.4])
        num_vista = c1.slider(
            '', min_value=10, max_value=df_archivo.shape[0], value=10, step=100, 
            label_visibility='collapsed',
        )
        c1.dataframe(
            df_archivo.dtypes, 
            column_config={'': MENSAJES['previsualcolnom'], '0': MENSAJES['previsualtipnom']}
        )
        c2.dataframe(df_archivo.head(num_vista))
        c3.dataframe(df_archivo.tail(num_vista)[::-1])  # Mostrar al revés

# ---------------------------------------------------------------------------------------------
col_fechahora = elegir_nombre_columna(
    prompt=MENSAJES['elegircolfechahora'], 
    tipos_validos=['object', 'datetime64'],
    df=df_archivo
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