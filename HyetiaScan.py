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
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import floor, ceil, trunc
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
@st.cache_data(show_spinner=MENSAJES['stcachespinner'])
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

    # Preparar zonas de visualización ---------------------------------------------------------
    with st.container(border=True):
        zona_grafico_agrupadas, zona_metricas = st.columns([0.7, 0.3])
    with st.container(border=True):
        zona_categorias, zona_control = st.columns([0.7, 0.3], gap='medium')
    with st.expander(MENSAJES['detallelecturas'], expanded=False):
        zona_detalle_agrupadas, zona_detalle_individuales = st.columns([0.7, 0.3], gap='medium')

    # -----------------------------------------------------------------------------------------
    # Controles deben ir antes de visualizaciones, pues modifican dataframe
    zona_control.write(MENSAJES['controlanormales'])

    # Control de duplicadas -------------------------------------------------------------------
    control_duplicadas = zona_control.radio(
        MENSAJES['lecturasduplicadas'], 
        options=[
            'No modificar', 
            'Dejar primera', 
            'Dejar última', 
            'Sumar',
            'Promediar',
            'Borrar'
        ], 
        horizontal=True,
    )
    match control_duplicadas:
        case 'Dejar primera': 
            df_individuales = df_individuales.drop_duplicates(subset=col_fechahora, keep='first')
        case 'Dejar última':
            df_individuales = df_individuales.drop_duplicates(subset=col_fechahora, keep='last')
        case 'Sumar':
            df_individuales = df_individuales.groupby(col_fechahora, as_index=False).agg({
                col_fechahora     : 'first',
                col_precipitacion : 'sum',
            })
        case 'Promediar':
            df_individuales = df_individuales.groupby(col_fechahora, as_index=False).agg({
                col_fechahora     : 'first',
                col_precipitacion : 'mean',
            })
        case 'Borrar':
            df_individuales = df_individuales.drop_duplicates(subset=col_fechahora, keep=False)

    # Control corruptas -----------------------------------------------------------------------
    control_corruptas = zona_control.radio(
        MENSAJES['lecturascorruptas'], 
        options=['No modificar', 'Borrar'], horizontal=True,
    )
    match control_corruptas:
        case 'Borrar':
            df_individuales = df_individuales[df_individuales[col_precipitacion] >= 0]

    # Control de perdidas ---------------------------------------------------------------------
    # Debe ser el último contgrol pues los otros pueden borrar
    control_perdidas = zona_control.radio(
        MENSAJES['lecturasperdidas'], 
        options=['No modificar', 'Asumir cero'], horizontal=True,
    )
    match control_perdidas:
        case 'Asumir cero':
            df_relleno = relleno_perdidas(df_individuales, intervalo=f'{intervalo}min', relleno=0)
            if not df_relleno.empty:
                df_individuales = pd.concat(
                    [df_individuales, df_relleno]
                ).sort_values(by=col_fechahora).reset_index(drop=True)

    # Generar datos agrupados según criterio y calcular métricas -------------------------------
    criterio = zona_grafico_agrupadas.radio(MENSAJES['lecturasagrupadas'], 
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
        MENSAJES['lecturasanormales'], options=lista_categorias, default=lista_anormales,
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
        ver_dataframe(df_agrupado, MENSAJES['lecturasagrupadas'])
    with zona_detalle_individuales:
        ver_dataframe(df_individuales, MENSAJES['lecturasindividuales'])

    # Verificar si aún quedan valores anormales por procesar ----------------------------------
    if (suma_columnas[lista_anormales] > 0).any():
        return None
    
    # -----------------------------------------------------------------------------------------
    return df_individuales

# ---------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=MENSAJES['stcachespinner'])
def normalizar_lecturas(df: pd.DataFrame, intervalo_minutos: int) -> pd.DataFrame:
    col_fechahora = df.columns[0]
    df[col_fechahora] = df[col_fechahora].dt.floor(f'{intervalo_minutos}min')
    return df

# ---------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=MENSAJES['stcachespinner'])
def consolidar_lecturas(df: pd.DataFrame, fecha_inicial, fecha_final) -> pd.DataFrame:
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
        acumulado = (col_precipitacion, 'sum'),
        lecturas  = (col_precipitacion, lambda p: p.tolist()),
    ).reset_index(drop=True)

    # Agregar coiumna de duracion
    df_consolidadas['duracion'] = intervalo + \
        (df_consolidadas['termina'] - df_consolidadas['inicia']).dt.total_seconds() // 60
    
    return df_consolidadas


# ---------------------------------------------------------------------------------------------
def calcular_eventos(
        df_consolidadas: pd.DataFrame, 
        duracion_minima: int,
        duracion_maxima: int,
        pausa_maxima: int, 
        intensidad_minima: int,
        intervalo: int,
) -> pd.DataFrame:

    # -----------------------------------------------------------------------------------------
    def calcular_porcentajes(lecturas, factor=100):
        return (pd.Series(lecturas).cumsum() * factor / sum(lecturas)).to_list()

    # -----------------------------------------------------------------------------------------
    def unir_precipitaciones(df: pd.DataFrame, pausa_maxima: int) -> pd.DataFrame:
        # Unifica precipitaciones según criterio de contiguidad.

        # Columna auxiliar para indicar si un evento es parte de lluvia continua o no
        # True = Evento es parte de lluvia continua
        # False = No hay lluvia (duracion > pausa_maxima)
        df['lluvia'] = \
            (df['acumulado'] > 0) | ((df['duracion'] <= pausa_maxima) & (df['acumulado'] == 0))

        # Columna auxiliar para enumerar eventos continuos con un numero de secuencia
        df['secuencia'] = df['lluvia'].ne(df['lluvia'].shift()).cumsum()

        return df

    # -----------------------------------------------------------------------------------------
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

        # Calcular el índice del mayor delta para usarlo como clasificacion de tipo de curva Huff
        # El mayor delta indica que en ese lapso el aguacero tuvo su mayor precipitación
        # enumerate genera tuplas (indice, valor), key indica que max debe 
        # comparar por el segundo item de la tupla (x[1]), el valor que retorna 
        # max es una tupla (indice, valor mayor) asi que extraemos el
        # primer elemento [0], el del indice, para usarlo como categoria de cuartil
        indice_mayor_delta = max(enumerate(deltas), key=lambda x: x[1])[0]

        # Nombre del cuartil calculado. Empiezan en cero, el nombre debe empezar en 1
        Qname = f"Q{indice_mayor_delta + 1}"

        return Qname

    # -----------------------------------------------------------------------------------------

    # Consolidar eventos que se consideren contiguos
    df = unir_precipitaciones(df_consolidadas, pausa_maxima)

    # Realizar la agregación basada en la secuencia de evento
    df = df.groupby('secuencia').agg(
        inicia    = ('inicia', 'first'),
        termina   = ('termina', 'last'),
        lecturas  = ('lecturas', lambda p: sum(p, [])),
        acumulado = ('acumulado', 'sum'),
    )

    # Recalcular columna de duracion
    df['duracion'] = \
        (df['termina'] - df['inicia']).dt.total_seconds() // 60 + intervalo

    # Agregar intensidad
    df['intensidad'] = \
        60 * df['acumulado'] / df['duracion']
    
    # Agregar conteo de mediciones
    df['conteo'] = df['lecturas'].apply(len)

    # # Filtrar precipitaciones por acumulado
    df = df[
        (df['acumulado'] > 0)
    ]

    # Filtrar por duracion
    df = df[(df['duracion'] >= duracion_minima) & (df['duracion'] <= duracion_maxima)]

    # # Filtrar por intensidad minima
    df = df[(df['intensidad'] >= intensidad_minima)]

    # Calcular y agregar porcentaje acumulado de mediciones
    df['porcentajes'] = df['lecturas'].apply(calcular_porcentajes)

    # Calcular y agregar cuartil de Huff
    df['Q_Huff'] = \
        df['porcentajes'].apply(determinar_cuartil_huff)
    
    # Reordenar columnas
    df = df[[
        'inicia', 'termina', 'duracion', 
        'intensidad', 'acumulado', 'conteo', 
        'lecturas', 'porcentajes', 'Q_Huff',
    ]]

    return df.reset_index(drop=True)

# ---------------------------------------------------------------------------------------------
def definir_parametros(df_procesadas: pd.DataFrame, intervalo: int) -> pd.DataFrame:
    col_fechahora = df_procesadas.columns[0]
    col_precipitacion = df_procesadas.columns[1]

    # Definir zonas de visualización
    with st.form('Parámetros'):
        c1, c2 = st.columns(2)
        primera_fecha = c1.date_input(
            'Fecha inicial',
            value=df_procesadas[col_fechahora].min(),
            min_value=df_procesadas[col_fechahora].min(),
            max_value=df_procesadas[col_fechahora].max(),
        )
        ultima_fecha = c2.date_input(
            'Fecha final',
            value=df_procesadas[col_fechahora].max(),
            min_value=df_procesadas[col_fechahora].min(),
            max_value=df_procesadas[col_fechahora].max(),
        )
        duracion_minima = st.slider(
            'Duración mínima', 
            value=20,
            min_value=intervalo, 
            max_value=1440,
            step=intervalo,
        )
        duracion_maxima = st.slider(
            "Duración maxima", 
            value=1440,
            min_value=intervalo * 2,
            max_value=1440,
            step=intervalo,
        )
        pausa_maxima = st.slider(
            'Pausa máxima',
            value=intervalo * 2,
            min_value=0,
            max_value=120,
            step=intervalo,
            help='''
                Criterio de continuidad en minutos. \n
                Tiempo tope entre precipitaciones para considerarlas un solo evento continuo.
            '''
        )
        intensidad_minima = st.slider(
            'Intensidad mínima',
            min_value=3,
            max_value=50,
            step=1,
        )
        aplicar_parametros = st.form_submit_button('Aplicar parámetros', type='primary')
    
    df_consolidadas = consolidar_lecturas(df_procesadas, primera_fecha, ultima_fecha)
    df_eventos = calcular_eventos(
        df_consolidadas, 
        duracion_minima, duracion_maxima,
        pausa_maxima, intensidad_minima, 
        intervalo
    )

    # Desplegar
    # if st.toggle('Ver detalle de eventos'):
    #     st.write(df_eventos.describe(include='all'))
    #     st.dataframe(df_eventos)

    return df_eventos

# ---------------------------------------------------------------------------------------------
def seccion_graficar_curvas_huff(df_eventos: pd.DataFrame):

    # -----------------------------------------------------------------------------------------
    def calcular_curvas_huff(df, intervalo=5):
        datos_huff = pd.DataFrame()

        # Generar percentiles a partir de porcentaje_acumulado de aguaceros
        # Usar intervalo especificado como argumento de la función
        datos_huff['percentiles'] = df['porcentajes'].apply(
            lambda p: np.percentile(p, range(intervalo, 101, intervalo))
        )

        # Determinar cuartil de cada curva
        datos_huff['Q'] = df['Q_Huff']

        # Calcular curvas Huff como promedio de cada correspondiente valor de percentiles
        curvas_huff = datos_huff.groupby('Q').agg(
            {'percentiles': lambda x: np.mean(list(zip(*x)), axis=1)}
        ).reset_index()

        # Agregar un cero al principio de cada lista en 'percentiles'
        curvas_huff['percentiles'] = curvas_huff['percentiles'].apply(
            lambda x: [0] + list(x)
        )

        return curvas_huff

    # -----------------------------------------------------------------------------------------

    zona_grafico = st.empty()
    intervalo_percentiles = st.select_slider(
        'Intervalo de percentiles',
        options=[5, 10, 20, 25, 50],
        value=10,
    )

    curvas_huff = calcular_curvas_huff(df_eventos, intervalo=intervalo_percentiles)
    valores_eje_x = range(0, 101, intervalo_percentiles)

    fig, ax = plt.subplots(figsize=(7, 4))
    marcas = "vDo^"
    for indice, curva in curvas_huff.iterrows():
        ax.plot(
            valores_eje_x,
            list(curva['percentiles']),
            label=curva['Q'],
            marker=marcas[indice]
        )

    ax.set_xticks(range(0, 101, intervalo_percentiles))
    ax.set_yticks(range(0, 101, 5))

    ax.grid(which='both', linestyle='--', linewidth=0.5)
    ax.grid(which='minor', linestyle=':', linewidth=0.5)

    ax.set_xlabel('% duración')
    ax.set_ylabel('% precipitación')
    
    ax.legend(fontsize=8)
    # legend.get_frame().set_facecolor('lightblue')
    #legend.get_frame().set_alpha(0)

    #plt.title(f'Curvas de Huff')
    # pie = generar_piedepagina(datos)
    # plt.text(100, 5, 
    #     pie, fontsize=6, ha='right', 
    #     bbox={'facecolor': 'white', 'alpha': 1, 'pad': 2}
    # )

    #fig.patch.set_alpha(0)
    # ax.tick_params(axis='x', colors='lightblue')
    # ax.tick_params(axis='y', colors='lightblue')
    # fig.patch.set_facecolor('none')
    # ax.patch.set_facecolor('none')

    # ax.xaxis.label.set_color('lightblue')
    # ax.yaxis.label.set_color('lightblue')

    zona_grafico.pyplot(fig)

    # if st.toggle('Ver valores percentiles'):
    #     curvas_huff['percentiles'] = curvas_huff['percentiles'].apply(
    #         lambda x: [round(i, 2) for i in x]
    #     )
    #     st.dataframe(curvas_huff, column_order=('Q', 'percentiles'), hide_index=True)

    return

# ---------------------------------------------------------------------------------------------
def preparar_curva_frecuencia(ax, df, columna):

    # Curva general
    valores       = df[[columna]].sort_values(columna, ascending=False)
    num_valores   = valores.shape[0]
    porcentajes_x = [(i + 1) / num_valores * 100 for i in range(num_valores)]
    ax.plot(porcentajes_x, valores, label='General', linestyle='-', linewidth=1.2)

    # Curvas por categoría Huff
    categorias = df['Q_Huff'].unique()
    categorias.sort()
    for categoria in categorias:
        valores       = df[df['Q_Huff'] == categoria][[columna]].sort_values(columna, ascending=False)
        num_valores   = valores.shape[0]
        porcentajes_x = [(i + 1) / num_valores * 100 for i in range(num_valores)]
        ax.plot(porcentajes_x, valores, label=categoria, linewidth=0.9, linestyle='-.')

    ax.set_ylabel(columna.capitalize())
    ax.set_xlabel('Probabilidad')
    
    ax.legend(fontsize=8)
    #legend.get_frame().set_facecolor('lightblue')

    ax.grid(which='both', linestyle='--', linewidth=0.5)
    ax.minorticks_on()
    ax.grid(which='minor', linestyle=':', linewidth=0.5)


    # ax.tick_params(axis='x', colors='lightblue')
    # ax.tick_params(axis='y', colors='lightblue')
    # ax.patch.set_facecolor('none')

    # ax.xaxis.label.set_color('lightblue')
    # ax.yaxis.label.set_color('lightblue')

    return

# ---------------------------------------------------------------------------------------------
def seccion_graficar_curvas_frecuencia(df_eventos):
    if df_eventos.shape[0] <= 1:
        st.warning('Se requieren dos o mas eventos para calcular frecuencias.')
        return
    
    fig, (ax_duracion, ax_precipit) = plt.subplots(1, 2, figsize=(7, 4))
    
    preparar_curva_frecuencia(ax_duracion, df_eventos, 'duracion')
    preparar_curva_frecuencia(ax_precipit, df_eventos, 'acumulado')

    #fig.patch.set_facecolor('none')
    st.pyplot(fig)

    return

# ---------------------------------------------------------------------------------------------
def seccion_graficar_rangos_intensidad(df_eventos):
    
    num_aguaceros = df_eventos.shape[0]
    if num_aguaceros <= 2:
        st.warning('Requiere mas de dos eventos.')
        return

    intensidad_min = floor(df_eventos['intensidad'].min())
    intensidad_max = ceil(df_eventos['intensidad'].max())
    intensidad_med = (intensidad_max - intensidad_min) // 2

    if intensidad_min == intensidad_max:
        st.warning('No hay diferencia de intensidades.')
        return
    
    zona_grafico = st.empty()
    num_rangos = st.slider(
        'Número de rangos:', 
        value=3,
        min_value=2, 
        max_value=10,
    )
    tamaño_rango = (intensidad_max - intensidad_min) / num_rangos
    limites_rangos = \
        [trunc(intensidad_min + i * tamaño_rango) for i in range(num_rangos + 1)]
    rangos = \
        [(limites_rangos[i], limites_rangos[i + 1]) for i in range(num_rangos)]

    df = df_eventos[['Q_Huff', 'intensidad']].copy()

    df['rango'] = pd.cut(
        df_eventos['intensidad'], 
        bins=limites_rangos,
        labels=[f'{t}' for t in rangos],
    )

    conteo_por_categoria = df.groupby(['Q_Huff', 'rango'], observed=False).size()
    categorias = df['Q_Huff'].unique()
    categorias.sort()
    
    fig, ax = plt.subplots(figsize=(7, 4))
    colores = ['lightblue', 'cyan', 'blue', 'navy']
    for i, categoria in enumerate(categorias):
        ax.bar(
            [p + i * 0.15 for p in range(num_rangos)], 
            conteo_por_categoria.loc[categoria],
            width=0.15,
            label=categoria,
            color=colores[i]
        )

    ax.legend(title='Cuartil', loc='upper left', bbox_to_anchor=(1, 1))
    ax.set_xticks(range(num_rangos))
    ax.set_xticklabels(rangos, rotation=45, fontsize=8)
    ax.set_xlabel('Rangos de intensidad')
    ax.set_ylabel('Frecuencia')
    ax.grid(which='both', linestyle='--', linewidth=0.5, axis='y')
    ax.grid(which='minor', linestyle=':', linewidth=0.5, axis='y')

    #fig.patch.set_facecolor('none')
    zona_grafico.pyplot(fig)

    return

# ---------------------------------------------------------------------------------------------
def desplegar_graficas(df_eventos: pd.DataFrame):
    t1, t2, t3 = st.tabs(['Huff', 'Frecuencia', 'Rangos'])

    with t1:
        seccion_graficar_curvas_huff(df_eventos)
    with t2:
        seccion_graficar_curvas_frecuencia(df_eventos)
    with t3:
        seccion_graficar_rangos_intensidad(df_eventos)
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
zona_descripcion.write(f'**{nombre_archivo}**')
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
df_lecturas = extraer_lecturas(df_archivo, col_fechahora, col_precipitacion)

# Detectar intervalo y normalizar/alinear lecturas a él ---------------------------------------
intervalo = estimar_intervalo_lecturas(df_lecturas)
df_lecturas = normalizar_lecturas(df_lecturas, intervalo)
st.sidebar.caption(
    f'*{MENSAJES["lecturasnormalizadas"](intervalo)}*'
)

# Procesamiento de lecturas -------------------------------------------------------------------
with tab_lecturas:
    df_lecturas_procesadas = desplegar_lecturas(df_lecturas, intervalo)

# Prcesamiento de eventos ---------------------------------------------------------------------
with tab_eventos:
    if df_lecturas_procesadas is None:
        st.warning(MENSAJES['lecturasporcontrolar'])
        st.stop()

    c1, c2 = st.columns([0.3, 0.7], gap='large')
    with c1:
        df_eventos = definir_parametros(df_lecturas_procesadas, intervalo)
    with c2:
        desplegar_graficas(df_eventos)
