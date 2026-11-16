# Simulación de control de nivel en un banco de flotación

Aplicación Python + HTML para ejecutar localmente o publicar en Render. Las ecuaciones se calculan en `modelo.py`, en el servidor Python. JavaScript solicita avances y dibuja las respuestas; no contiene una segunda implementación del modelo.

## Fuente y alcance

Quintanilla, P., Navia, D., Moreno, F., Neethling, S. J., & Brito-Parada, P. R. (2023). *A methodology to implement a closed-loop feedback-feedforward level control in a laboratory-scale flotation bank using peristaltic pumps*. MethodsX, 10, 102081. https://doi.org/10.1016/j.mex.2023.102081

Se adapta el banco de tres celdas y sus modelos integradores identificados de la tabla 2. Se incluyen PI (opción por defecto del artículo), SIMC, feedforward adaptado, IAE y una extensión PID opcional con Td > 0. No es una reproducción de los datos experimentales de la figura 14. Lea `NOTA_MODELO.md`: documenta ecuaciones, unidades, supuestos y diferencias con la fuente.

Esta entrega Python funciona sin OpenPLC. No existe conexión de datos con el proyecto Ladder anterior: ambos son implementaciones independientes. No se atribuye el modelo de una celda con válvula usado anteriormente al artículo de tres celdas con bombas.

## Ejecución en Windows (docente o estudiante)

Requiere Python 3.11 o posterior, navegador e Internet para instalar dependencias la primera vez.

1. Extraer **todo** el ZIP.
2. Abrir la carpeta `flotacion_nube`.
3. Ejecutar `iniciar_windows.bat`.
4. Abrir http://127.0.0.1:5000.
5. Mantener abierta la consola mientras se utiliza la aplicación. Ctrl+C detiene el servidor.

Alternativa manual en PowerShell, desde esa carpeta:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

No abrir `index.html` mediante doble clic: necesita el servidor Python. Si el puerto 5000 está ocupado, usar `$env:PORT="5001"` antes de iniciar y abrir http://127.0.0.1:5001.

Linux/macOS: `sh iniciar_local.sh`. También puede crear un entorno virtual, instalar `requirements.txt` y ejecutar `python app.py`.

## Revisar el modelo sin interfaz ni dependencias externas

El módulo matemático usa solo la biblioteca estándar de Python:

```powershell
py -3 modelo.py --duration 900 --csv resultados.csv
py -3 modelo.py --compare
py -3 modelo.py --feedforward --csv resultados_ff.csv
py -3 modelo.py --config experimento.json --csv repeticion.csv
```

En Linux/macOS sustituir `py -3` por `python3`. `--compare` calcula y muestra IAE PI, IAE PI+FF y cambio porcentual. El fichero JSON exportado desde el panel permite repetir exactamente la configuración. Los resultados son deterministas para la misma configuración y versión del código.

## Publicar en Render y obtener las dos URL de entrega

1. Crear en GitHub un repositorio nuevo, por ejemplo `flotacion-pid-nube`.
2. Subir **el contenido** de `flotacion_nube` a la raíz: deben verse allí `app.py`, `modelo.py`, `requirements.txt`, `render.yaml`, `templates/` y `static/`. No subir `.venv/`, cachés o contraseñas. Si se sube la carpeta contenedora completa, configurar **Root Directory = flotacion_nube** en Render.
3. En https://dashboard.render.com elegir **New > Web Service** y conectar ese repositorio.
4. Configurar:

| Campo | Valor |
|---|---|
| Language | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 60` |
| Health Check Path | `/health` |
| Instance Type | Free para demostración |

El archivo `.python-version` solicita Python 3.11. Si el servicio tiene una variable `PYTHON_VERSION` anterior, debe retirarla o poner una versión completa compatible. Alternativa: crear un Blueprint con el `render.yaml` incluido.

5. Pulsar Deploy Web Service. Esperar a que indique **Live**. Copiar la URL **real** que Render asigne; no se proporciona un hostname inventado.
6. Abrir esa URL, pulsar **Iniciar**, verificar avance del tiempo y cambios de nivel.
7. Enviar al docente:
   - URL de la simulación: la URL asignada por Render.
   - URL del código descargable: la misma URL seguida de `/descargar-proyecto`.

La página contiene un botón para esa descarga. El ZIP incluye el servidor, el módulo matemático, HTML, CSS, JavaScript, pruebas y estas instrucciones. ZIP cumple la función de un archivo comprimido descargable; no se requiere RAR para ejecutar el código.

Documentación oficial: https://render.com/docs/deploy-flask

### Límites de la demostración

Render Free puede suspender el servicio tras 15 minutos sin tráfico; el primer acceso posterior puede tardar alrededor de un minuto. El estado es temporal, por visitante y en memoria: desaparece al reiniciar/republicar, al recargar la página (nuevo experimento), o al expirar 30 minutos sin solicitudes. Descargar CSV/JSON antes de cerrar. No promete operación 24/7 ni almacenamiento permanente. Ver https://render.com/docs/free.

Se utiliza **un worker** porque las sesiones están en memoria; no aumentar workers ni instancias sin mover el estado a un almacén compartido. Máximo 32 sesiones activas. Para una exposición/ensayo docente esto evita mezclar experimentos entre visitantes.

## Guion de demostración (2 minutos)

1. Mantener los valores iniciales y pulsar Iniciar a 15× o 30×.
2. Explicar el equilibrio inicial: niveles de 25 cm y alimentación/descargas de 45 L/min.
3. A 30 s simulados se solicita subir las tres consignas a 26 cm. Las bombas reducen inicialmente la descarga; el nivel comienza a aumentar después de los retardos.
4. A 300 s la alimentación externa aumenta 20 %, de 45 a 54 L/min. Observar el rechazo de perturbación y la propagación entre celdas.
5. Al completar 900 s, descargar CSV y configuración JSON.
6. Pulsar Calcular comparación. Se ejecutan dos experimentos independientes completos en Python: PI y PI+FF. Revisar el IAE calculado; no se garantiza mejora para cualquier configuración elegida.
7. Abrir la sección Modelo matemático, explicar el signo de Kc, la integral, los retardos y las fórmulas SIMC. Dejar Td=0 para el caso del artículo; Td>0 muestra la extensión PID.
8. Descargar el ZIP desde la web y ejecutar `modelo.py --compare` localmente: debe devolver los mismos resultados de referencia.

El tiempo es **tiempo de simulación**, no tiempo real industrial. La velocidad solo cambia cuántos pasos Python se solicitan por actualización. Al pausar o cerrar el navegador el experimento deja de avanzar. No hay una animación previamente grabada: cada avance recalcula estado y control en el servidor.

## Arquitectura y archivos

| Archivo | Responsabilidad |
|---|---|
| `modelo.py` | Ecuaciones, retardos, PI/PID, feedforward, SIMC y cálculo del IAE/ISE |
| `app.py` | API Flask, sesiones independientes, exportación CSV/JSON y ZIP |
| `templates/index.html` | Panel de experimentación y explicación matemática |
| `static/app.js` | Solicitudes a Python y visualización de datos recibidos |
| `static/style.css` | Diseño adaptable a computadora y móvil |
| `render.yaml` | Configuración de despliegue |
| `NOTA_MODELO.md` | Trazabilidad científica y límites |
| `RESULTADOS_VERIFICADOS.json` | Valores calculados para el escenario predeterminado |
| `tests/` | Comprobaciones del modelo y de la API |
| `referencias/articulo_fuente.pdf` | Fuente proporcionada, CC BY 4.0 |

## Pruebas

Desde la carpeta que contiene `app.py`:

```powershell
py -3 -m pip install -r requirements-dev.txt
py -3 -m pytest -q
```

Incluyen equilibrio, signo del controlador, retardo de siete segundos, pendiente ante perturbación, acoplamiento, finitud, límites, determinismo, rechazo de entradas inválidas, independencia de sesiones y contenido descargable. Los resultados numéricos propios no son mediciones de planta.

## API de revisión

- `GET /health`: confirma motor Python y paso 0.1 s.
- `GET /api/modelo`: parámetros de la fuente, SIMC recalculado y ecuaciones.
- `POST /api/nueva`: JSON de configuración, devuelve identificador de sesión.
- `POST /api/paso/<session>`: `{"steps": 10}` avanza 1 s; máximo 500 pasos por solicitud.
- `GET /api/csv/<session>`: datos calculados, muestreados cada segundo.
- `GET /api/config/<session>`: configuración reproducible.
- `POST /api/comparar`: misma configuración, dos estrategias.
- `GET /descargar-proyecto`: código completo comprimido.

El archivo del artículo es de sus autores y se distribuye con atribución bajo la licencia CC BY 4.0 que figura en su primera página. El código y los escenarios de este paquete son una adaptación académica independiente.
