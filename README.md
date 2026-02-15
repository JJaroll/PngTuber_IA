# 🎙️ (AI)terEgo (Python + PyTorch)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-red) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green) ![Version](https://img.shields.io/badge/Version-1.0.0-blue)

**(AI)terEgo** es una aplicación de avatar virtual inteligente y moderna escrita en Python. A diferencia de los PNGTubers tradicionales que solo reaccionan al volumen, este proyecto utiliza **Inteligencia Artificial (Wav2Vec2)** para analizar tu tono de voz en tiempo real y cambiar la expresión de tu avatar automáticamente.

Ideal para streamers, creadores de contenido o simplemente para divertirse en Discord/Zoom.

## ✨ Características Principales

* **🧠 Cerebro IA Multi-Modelo:**
    *   **Español (SomosNLP):** Detecta *Neutral, Feliz, Triste, Enojado*.
    *   **Inglés/Global (XLS-R):** Detecta *Neutral, Feliz, Triste, Enojado, Sorpresa, Asco, Miedo*.
    *   *Nota: Puedes cambiar de modelo en tiempo real desde los Ajustes.*
* **🗣️ Lip Sync:** Movimiento de boca reactivo al volumen del micrófono.
* **🐇 Efectos Visuales:**
    *   **Rebote (Bounce):** El avatar salta sutilmente cuando hablas.
    *   **Sombra Suave:** Sombra realista debajo del avatar.
* **🎨 Sistema de Skins (.ptuber):**
    *   Crea tus propios avatares con el **Creador Integrado**.
    *   Soporte para hasta **7 emociones** y estados de boca (cerrada/abierta).
    *   Importa y exporta skins fácilmente para compartir con amigos.
*   **⚙️ Configuración Personalizable:**
    *   **Pestaña Sistema:** Selector de modelo IA y control de actualizaciones automáticas.
    *   **Atajos:** Configura teclas globales para cada emoción.
    *   **Persistencia:** Guarda automáticamente tu micrófono, sensibilidad y colores.
*   **🖥️ Interfaz Moderna:**
    *   Ventana sin bordes (Frameless) con fondo transparente.
    *   **Sistema de Actualizaciones:** Notificaciones discretas tipo "pill" cuando hay nuevas versiones.

## 🛠️ Instalación

### Requisitos Previos
* Python 3.10 o superior.
* Un micrófono.

### Pasos
1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/JJaroll/PngTuber_IA.git
    cd pngtuber-ia
    ```

2.  **Crear un entorno virtual (Recomendado):**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instalar dependencias:**
    *(Nota: PyTorch puede requerir una instalación específica según tu sistema. Revisa [pytorch.org](https://pytorch.org))*
    ```bash
    pip install -r requirements.txt
    ```
    *Si no tienes el archivo requirements.txt, las librerías principales son:*
    `PyQt6`, `torch`, `torchaudio`, `transformers`, `huggingface_hub`, `pyaudio`, `numpy`.

4.  **Instalar PyAudio (Si da error):**
    * **Windows:** `pip install pipwin && pipwin install pyaudio`
    * **macOS:** `brew install portaudio && pip install pyaudio`
    * **Linux:** `sudo apt-get install python3-pyaudio`

## 🚀 Uso

Ejecuta el archivo principal:

```bash
python main.py
```

## 🎨 Controles

*   **Clic Izquierdo + Arrastrar:** Mover al personaje por la pantalla.
*   **Clic Derecho:** Abrir el Menú Contextual (Ajustes rápidos).
*   **Esquina Inferior Derecha:** Redimensionar al personaje.
*   **Botones Inferiores (Dock):**
    *   🔊: Silenciar/Activar micrófono.
    *   🤖: Activar **Modo IA** (Automático).
    *   😐, 😄, etc.: Forzar una emoción manualmente.
    *   *Nota: Las emociones no soportadas por el modelo actual (ej. Miedo en español) aparecerán ocultas pero pueden ser activadas manualmente.*

### Atajos de Teclado (Por defecto)
*   **1-4:** Emociones básicas (Neutral, Feliz, Triste, Enojado).
*   **7-9:** Emociones extra (Sorpresa, Miedo, Asco).
*   **X:** Activar Modo IA.
*   **M:** Mutear micrófono.

### Configuración Avanzada (Clic Derecho -> Ajustes)
Desde aquí puedes controlar todo:
*   **Sistema:** Cambiar Modelo IA (Español/Inglés), verificar actualizaciones.
*   **Audio:** Ajustar sensibilidad y umbral de silencio.
*   **Apariencia:** Cambiar color de fondo (Transparente/Chroma).
*   **Avatar:** Gestionar y editar Skins.
*   **Atajos:** Personalizar las teclas rápidas.

## 📁 Estructura del Proyecto

* **main.py:** Punto de entrada. Conecta la interfaz con la lógica.
* **core_systems.py:** El Cerebro. Contiene los hilos de Audio (PyAudio) y de IA (Transformers).
* **background.py:** Gestiona el menú contextual y las opciones visuales.
* **profile_manager.py:** Lógica para guardar, cargar, importar y exportar skins (.ptuber).
*   **config_manager.py:** Sistema de guardado de preferencias (settings.json).
*   **settings_window.py:** Ventana de configuración completa.

## 🤝 Contribuir

¡Las contribuciones son bienvenidas!

1.  Haz un **Fork** del proyecto.
2.  Crea una rama (`git checkout -b feature/NuevaFuncion`).
3.  Haz tus cambios y commits.
4.  Haz Push a la rama (`git push origin feature/NuevaFuncion`).
5.  Abre un **Pull Request**.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

Creado con ❤️ por **JJaroll**
