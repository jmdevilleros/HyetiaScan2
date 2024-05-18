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

    'fileuploaderhelp'        : '''
            El archivo debe contener lecturas de precipitación consecutivas en serie 
            de tiempo ordenada, con al menos una columna de fecha/hora (datetime) y
            al menos una columna numérica de precipitación.
            ''',

    'stcachespinner'          : 'Cargando...',

    'errorlecturas'           : 'Error en archivo seleccionado.',
    'errorfechahora'          : lambda c, i, v: f'Error de formato en columna "{c}", índice {i}: [{v}]',
    'errortipocols'           : lambda t: f'No se detectan columnas de tipo {t}',
    
    'elegirdecimal'           : 'Separador decimal',
    'elegircodificacion'      : 'Codificación',
    'elegirarchivo'           : 'Seleccione archivo de lecturas.',
    'elegircolfechahora'      : 'Seleccione columna de fecha-hora.',
    'elegircolprecipitacion'  : 'Seleccione columna de precipitación.',
    'columnasok'              : 'Columnas seleccionadas.',

    'tabcarga'                : 'Cargar archivo',
    'tabconfig'               : 'Configurar carga',
    'tabarchivo'              : 'Archivo',
    'tablecturas'             : 'Lecturas',
    'tabeventos'              : 'Eventos',

    'previsualarchivo'        : 'Previsualizar registros.',
    'previsualcolnom'         : 'Columna',
    'previsualtipnom'         : 'Tipo',
    'previsualcantidad'       : 'Cantidad a visualizar',
    'previsualindice'         : 'Índice',

    'lecturasnormalizadas'    : lambda i: f'Lecturas normalizadas a intervalos de {i} minuto{"s" if i > 1 else ""}'
}