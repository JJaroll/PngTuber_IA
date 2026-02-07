from pynput import keyboard
import time

print("Iniciando prueba de hotkeys...")

def on_press(key):
    try:
        print(f"Tecla presionada: {key}")
    except Exception as e:
        print(f"Error: {e}")

try:
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    print("Listener iniciado. Presiona teclas (Ctrl+C para salir)...")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Saliendo...")
except Exception as e:
    print(f"Error fatal: {e}")
