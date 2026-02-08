# 🎙️ AI PNGTuber (Python + PyTorch)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-red) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green)

Un **PNGTuber inteligente** y moderno escrito en Python. A diferencia de los PNGTubers tradicionales que solo reaccionan al volumen, este proyecto utiliza **Inteligencia Artificial (Wav2Vec2)** para analizar tu tono de voz en tiempo real y cambiar la expresión de tu avatar automáticamente (Feliz, Enojado, Triste o Neutral).

Ideal para streamers, creadores de contenido o simplemente para divertirse en Discord/Zoom.

## ✨ Características Principales

* **🧠 Cerebro IA:** Detecta emociones en tu voz usando un modelo de HuggingFace (`wav2vec2-base-finetuned-sentiment-classification`).
* **🗣️ Lip Sync:** Movimiento de boca reactivo al volumen del micrófono.
* **🐇 Efectos Visuales:**
    * **Rebote (Bounce):** El avatar salta sutilmente cuando hablas.
    * **Sombra Suave:** Sombra realista debajo del avatar.
* **🎨 Sistema de Skins (.ptuber):**
    * Crea tus propios avatares con el **Creador Integrado**.
    * Importa y exporta skins fácilmente para compartir con amigos.
*   **⚙️ Configuración Persistente:** Guarda automáticamente tu micrófono preferido, sensibilidad, skin y colores.
*   **🎹 Atajos Rápidos:** Botones en pantalla para cambiar emociones o volver al modo IA.
*   **🖥️ Interfaz Moderna:**
    *   Ventana sin bordes (Frameless).
    *   Fondo transparente real (compatible con macOS y Windows).
    *   Controles estilo Mac.

## 🛠️ Instalación

### Requisitos Previos
* Python 3.10 o superior.
* Un micrófono.

### Pasos
1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/JJaroll/pngtuber-ia.git
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
    `PyQt6`, `torch`, `torchaudio`, `transformers`, `pyaudio`, `numpy`.

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
*   **Clic Derecho:** Abrir el Menú Contextual (Ajustes avanzados).
*   **Esquina Inferior Derecha:** Redimensionar al personaje.
*   **Botones Inferiores:**
    *   🔊: Silenciar/Activar micrófono.
    *   🤖: Activar **Modo IA** (Automático).
    *   😐, 😄, 😠, 😢: Forzar una emoción (Modo Manual).

### Menú Contextual (Clic Derecho)
Desde aquí puedes controlar todo:

*   **🎚️ Ajustes de Audio:**
    *   **Sensibilidad:** Aumenta si el avatar no te escucha bien.
    *   **Umbral:** Aumenta si el avatar se mueve con el ruido de fondo.
*   **🎨 Fondo:** Cambiar entre Transparente (para OBS/Desktop) o Verde/Azul (Chroma Key).
*   **👕 Skins:** Cambiar de avatar, crear uno nuevo o importar/exportar.
*   **⚙️ Otras Opciones:**
    *   Seleccionar Micrófono.
    *   Activar/Desactivar Rebote y Sombra.
    *   Ajustar intensidad del rebote.

## 📁 Estructura del Proyecto

El código está modularizado para facilitar el mantenimiento:

* **main.py:** Punto de entrada. Conecta la interfaz con la lógica.
* **core_systems.py:** El Cerebro. Contiene los hilos de Audio (PyAudio) y de IA (Transformers).
* **background.py:** Gestiona el menú contextual y las opciones visuales.
* **profile_manager.py:** Lógica para guardar, cargar, importar y exportar skins (.ptuber).
*   **config_manager.py:** Sistema de guardado de preferencias (settings.json).
*   **mac_gui.py:** Botones personalizados de la ventana.
*   **hotkey_manager.py:** Gestión de atajos de teclado globales.

## 🤝 Contribuir

¡Las contribuciones son bienvenidas!

1.  Haz un **Fork** del proyecto.
2.  Crea una rama (`git checkout -b feature/NuevaFuncion`).
3.  Haz tus cambios y commits.
4.  Haz Push a la rama (`git push origin feature/NuevaFuncion`).
5.  Abre un **Pull Request**.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

Creado con ❤️