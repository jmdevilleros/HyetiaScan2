# *********************************************************************************************
# HyetiaScan - Prueba de humo
#
# Uso (desde la raíz del repositorio, con el entorno virtual activo):
#   python tests/smoke_test.py
#
# 1. CLI con el archivo de ejemplo y control de anormales: código 0 y 30 eventos.
# 2. CLI sin control de anormales: código 2 y sin eventos.
# 3. Aplicación Streamlit (AppTest) sin archivo cargado: se ejecuta sin excepciones.
# *********************************************************************************************

import json
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / 'ejemplos' / 'lluvia_ejemplo_5min.csv'
EVENTOS_ESPERADOS = 30
CONTROLES = ['--duplicadas', 'primera', '--corruptas', 'borrar',
             '--atipicas', 'borrar', '--perdidas', 'cero']

# ---------------------------------------------------------------------------------------------
def correr_cli(salida: Path, *opciones: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RAIZ / 'hyetiascan_cli.py'), str(EJEMPLO), '--salida', str(salida), *opciones],
        capture_output=True, text=True, cwd=RAIZ,
    )

# ---------------------------------------------------------------------------------------------
def probar_cli_con_controles():
    with tempfile.TemporaryDirectory() as tmp:
        salida = Path(tmp)
        r = correr_cli(salida, *CONTROLES, '--json')
        assert r.returncode == 0, f'Código {r.returncode}\n{r.stdout}\n{r.stderr}'
        for archivo in ['lecturas_procesadas.csv', 'lecturas_agrupadas.csv', 'eventos.csv',
                        'acumulados.csv', 'curvas_huff.csv', 'resumen.json']:
            assert (salida / archivo).is_file(), f'Falta {archivo}'
        resumen = json.loads((salida / 'resumen.json').read_text(encoding='utf-8'))
        cantidad = resumen['eventos']['cantidad']
        filas = len((salida / 'eventos.csv').read_text(encoding='utf-8').strip().splitlines()) - 1
        assert cantidad == filas == EVENTOS_ESPERADOS, \
            f'Se esperaban {EVENTOS_ESPERADOS} eventos; resumen={cantidad}, eventos.csv={filas}'
        assert f'Eventos: {EVENTOS_ESPERADOS}' in r.stdout
    print(f'OK  CLI con controles: código 0, {EVENTOS_ESPERADOS} eventos')

# ---------------------------------------------------------------------------------------------
def probar_cli_sin_controles():
    with tempfile.TemporaryDirectory() as tmp:
        salida = Path(tmp)
        r = correr_cli(salida)
        assert r.returncode == 2, f'Código {r.returncode}, se esperaba 2\n{r.stderr}'
        assert not (salida / 'eventos.csv').exists()
        assert (salida / 'lecturas_procesadas.csv').is_file()
    print('OK  CLI sin controles: código 2 (quedan lecturas anormales), sin eventos')

# ---------------------------------------------------------------------------------------------
def probar_app_sin_archivo():
    from streamlit.testing.v1 import AppTest
    from mensajes_es import TEXTOS
    at = AppTest.from_file(str(RAIZ / 'HyetiaScan.py'), default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert TEXTOS['elegirarchivo'] in [i.value for i in at.info]
    print('OK  App Streamlit sin archivo: sin excepciones')

# =============================================================================================
# Sección principal
# =============================================================================================

if __name__ == '__main__':
    sys.path.insert(0, str(RAIZ))
    probar_cli_con_controles()
    probar_cli_sin_controles()
    probar_app_sin_archivo()
    print('Prueba de humo superada.')
