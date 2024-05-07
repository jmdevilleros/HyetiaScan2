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
import matplotlib.pyplot as plt
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
    nombre_col = st.sidebar.selectbox(prompt, lista_columnas, index=0)
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
    
    df_aux = df.groupby(agrupacion)[col_precipitacion].agg(
        positivos = lambda x: (x >= 0).sum(),
        negativos = lambda x: (x < 0).sum(),
        acumulado = 'sum'
    )
    df_aux['duplicados'] \
        = df.groupby(agrupacion)[col_fechahora].apply(lambda x: x.duplicated().sum())
    
    return df_aux.reset_index()

# ---------------------------------------------------------------------------------------------
def ver_dataframe(df: pd.DataFrame, titulo: str = None):
    if titulo:
        st.write(titulo)
    cantidad = st.slider(
        MENSAJES['previsualcantidad'],
        min_value=0, 
        max_value=df.shape[0], 
        value=10, 
        step=10,
    )
    st.dataframe(df.head(cantidad), hide_index=True, use_container_width=True,)

# ---------------------------------------------------------------------------------------------
def desplegar_lecturas(df: pd.DataFrame): 
    col_fechahora = df.columns[0]
    col_precipitacion = df.columns[1]
    agrupaciones = {'Dia' : 'D', 'Mes' : 'ME', 'Año' : 'YE'}
    lista_categorias = ['positivos', 'negativos', 'duplicados']
    
    # -----------------------------------------------------------------------------------------
    zona_control, zona_stats = st.columns([0.75, 0.25], gap='medium')
    zona_chart_agrupadas, zona_chart_categorias = st.columns(2, gap='medium')
    _, zona_agrupadas, zona_lecturas, _ = st.columns([0.1, 0.50, 0.30, 0.1], gap='small')

    with zona_chart_agrupadas.container(border=True):
        zona_criterio = st.empty()
        zona_chart = st.empty()
    
    criterio = zona_criterio.radio(
        'Lecturas agrupadas', 
        options=list(agrupaciones.keys()),
        index=1, horizontal=True
    )

    df_agrupado = agrupar_lecturas(df, agrupaciones[criterio])
    suma_columnas = df_agrupado[lista_categorias].sum(numeric_only=True) 
    porcentajes = suma_columnas / suma_columnas.sum() * 100
    
    zona_chart.bar_chart(
        df_agrupado, x=col_fechahora, y='acumulado', 
        use_container_width=True, height=265,
    )

    with zona_control.container(border=True, height=250):
        control_negativos = st.radio('Control negativos', options=['=', '0'], horizontal=True)
        if control_negativos == '0':
            df[col_precipitacion] = df[col_precipitacion].clip(lower=0)
        control_duplicados = st.radio('Control duplicados', options=['=', '0'], horizontal=True)
        control_vacios = st.radio('Control vacíos', options=['=', '0'], horizontal=True)

    with zona_chart_categorias.container(border=True):
        categorias_elegidas = st.multiselect(
            'Categorías de lecturas', 
            options=lista_categorias, 
            default=[c for c in lista_categorias if c != 'positivos'],
        )
        st.bar_chart(
            df_agrupado, x=col_fechahora, y=categorias_elegidas, 
            use_container_width=True, height=250,
        )

    with zona_stats.container(border=False):
        fig, ax = plt.subplots()
        pie = ax.pie(suma_columnas)
        labels = [
            f'{label}: {value} ({porcentaje:.1f}%)' 
            for label, value, porcentaje in zip(suma_columnas.index, suma_columnas, porcentajes)
        ]
        plt.legend(pie[0], labels,fontsize='large', loc='lower center')
        fig.patch.set_alpha(0)
        st.pyplot(fig)

    with zona_lecturas.container(border=True):
        ver_dataframe(df_lecturas, 'Detalle lecturas individuales')
    with zona_agrupadas.container(border=True):
        ver_dataframe(df_agrupado, f'Detalle lecturas agrupadas ({criterio})')

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
