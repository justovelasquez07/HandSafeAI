# HandSafe AI — detector de gestos con cámara

Aplicación local de Python que utiliza la cámara para detectar una mano, dibujar sus 21 puntos de referencia y clasificar cinco gestos estáticos. Muestra subtítulos en pantalla, puede pronunciar mensajes y guarda un historial local en JSON.

## Gestos incluidos

- Mano abierta — neutral
- Pulgar arriba — positivo
- Puño cerrado — neutral
- Señal de paz — positivo
- Dedo medio levantado — inapropiado

**Importante:** el programa identifica patrones visuales definidos para una demostración. No determina la intención de la persona ni establece una clasificación universal de gestos. El significado depende del contexto cultural. Tampoco traduce la Lengua de Señas Nicaragüense (LSN); esa sería una ampliación distinta que requiere datos específicos.

## Requisitos

- macOS con cámara y permisos habilitados, Windows o Linux.
- Python 3.11 o 3.12 de 64 bits recomendado.
- Cámara web.
- En macOS, el comando `say` se usa para voz. En otros sistemas se intenta utilizar `pyttsx3`.

## Instalación en macOS

Abre Terminal en VS Code dentro de esta carpeta:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Si no tienes Python 3.12, instálalo con Homebrew:

```bash
brew install python@3.12
```

Después vuelve a ejecutar la creación del entorno virtual con `python3.12`.

## Instalación en Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## Controles

- `Q`: salir.
- `V`: activar/desactivar voz.
- `H`: mostrar/ocultar ayuda.

## Archivos

- `main.py`: ciclo principal de cámara e interfaz.
- `hand_tracking.py`: detección y dibujo de landmarks con MediaPipe.
- `recognition.py`: clasificación geométrica inicial.
- `voice.py`: salida de voz.
- `storage.py`: lectura y escritura del historial/configuración JSON.
- `data/history.json`: historial local de detecciones.
- `data/config.json`: parámetros de funcionamiento.

## Privacidad

El procesamiento se realiza localmente. No se envían imágenes a servidores y no se necesita una base de datos. El historial guarda únicamente la fecha, el nombre del gesto, su categoría y la confianza estimada; no guarda fotografías ni video.

## Limitaciones conocidas

- Los gestos se clasifican mediante reglas geométricas, no mediante una red neuronal entrenada.
- La clasificación funciona mejor con la mano orientada hacia la cámara, buena iluminación y una sola mano visible.
- El detector inicial reconoce gestos estáticos; no interpreta secuencias, expresiones faciales ni gramática de una lengua de señas.
- La cifra de confianza es orientativa, no una probabilidad estadística calibrada.
- Si la cámara no abre en macOS, concede permiso de cámara a Terminal o Visual Studio Code en Ajustes del Sistema > Privacidad y seguridad > Cámara.
