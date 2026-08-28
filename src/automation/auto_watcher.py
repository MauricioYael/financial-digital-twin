import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.orchestration.run_pipeline_e2e import execute_full_pipeline

WATCH_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
POLL_INTERVAL_SECONDS = 3  # Frecuencia de revisión

def get_directory_state(directory: str) -> dict:
    state = {}
    if not os.path.exists(directory):
        return state

    for filename in os.listdir(directory):
        if filename.endswith(".csv"):
            filepath = os.path.join(directory, filename)
            try:
                mtime = os.path.getmtime(filepath)
                size = os.path.getsize(filepath)
                state[filename] = (mtime, size)
            except OSError:
                continue
    return state

def start_watching():
    print("\n" + "🔍" * 25)
    print("🤖 SERVICIO DE AUTOMATIZACIÓN ACTIVO")
    print(f"📁 Monitoreando carpeta: {WATCH_DIR}")
    print("💡 Al guardar o actualizar un CSV, el pipeline correrá solo.")
    print("🛑 Para detenerlo: Presiona Ctrl + C en la terminal.")
    print("🔍" * 25 + "\n")

    last_state = get_directory_state(WATCH_DIR)

    # Ingesta y validación inicial
    execute_full_pipeline(trigger_source="INICIALIZACIÓN_WATCHER")

    while True:
        try:
            time.sleep(POLL_INTERVAL_SECONDS)
            current_state = get_directory_state(WATCH_DIR)

            has_changes = False
            changed_files = []

            for filename, signature in current_state.items():
                if filename not in last_state:
                    has_changes = True
                    changed_files.append(f"Nuevo: {filename}")
                elif last_state[filename] != signature:
                    has_changes = True
                    changed_files.append(f"Modificado: {filename}")

            if has_changes:
                print(f"\n🔔 [CAMBIO DETECTADO] -> {', '.join(changed_files)}")
                time.sleep(1)
                execute_full_pipeline(trigger_source=f"EVENTO_RAW ({', '.join(changed_files)})")
                last_state = current_state

        except KeyboardInterrupt:
            print("\n🛑 Centinela detenido por el usuario.")
            break
        except Exception as e:
            print(f"⚠️ Error en monitoreo: {e}")
            time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    start_watching()