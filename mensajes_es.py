# *********************************************************************************************
# HyetiaScan
# Análisis de lluvias
# Juan Manuel de Villeros Arias
# Mónica Liliana Gallego Jaramillo
# Mayo 2024
#
# Archivo: mensajes_es.py - Texto de mensajes en español
# *********************************************************************************************

MENSAJES = {
    'appname'                 : 'HyetiaScan',
    'appversion'              : '2.0',
    'appdescription'          : 'Análisis de eventos de precipitación.',

    'about' : '''
        ### HyetiaScan - Análisis de lluvias
        - Juan Manuel de Villeros Arias
        - Mónica Liliana Gallego Jaramillo
        ### Contacto: hyetiascan@teoktonos.com
        ''',

    'fileuploaderprompt'      : 'Selección de archivo de lecturas',
    'fileuploaderhelp'        : '''
            El archivo debe contener lecturas de precipitación consecutivas en serie 
            de tiempo ordenada, con al menos una columna de fecha/hora (datetime) y
            al menos una columna numérica de precipitación.
            ''',

    'stcachespinner'          : 'Cargando...',

    'errorlecturas'           : 'Error en archivo seleccionado.',
    'nohaylecturas'           : 'Archivo de lecturas requerido.',
    'shapelecturas'           : lambda s: f'Cargados {s[0]} registros, {s[1]} columnas.',

    'elegircolfechahora'      : 'Seleccione columna de fecha-hora.',
    'elegircolprecipitacion'  : 'Seleccione columna de precipitación.',
    'elegircolsdiferentes'    : 'No puede seleccionar la misma columna.',

    'errortipocolumna'        : 'Error en tipo de columna',

    'previsualizararchivo'    : 'Previsualizar primeros y últimos registros.',
}