import os
import sys
import time
import hashlib
import urllib.request
import pandas as pd

# Asegurar ruta raíz del proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ingestion.fetch_drive_data import SOURCES, RAW_DIR
from src.orchestration.run_pipeline_e2e import execute_full_pipeline

CHECK_INTERVAL_SECONDS = 5  # Frecuencia de revisión en Drive (segundos)

def get_drive_sheet_content(sheet_id: str) -> bytes:
    """Descarga el contenido crudo de Google Sheets en memoria para verificar si cambió."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return response.read()

def start_live_sync():
    print("\n" + "🌐" * 30)
    print("🤖 SERVICIO DE SINCRONIZACIÓN EN TIEMPO REAL (DRIVE ➔ PIPELINE)")
    print(f"⏱️  Monitoreando Google Drive cada {CHECK_INTERVAL_SECONDS} segundos...")
    print("💡 Cualquier cambio hecho en el navegador disparará el pipeline automáticamente.")
    print("🛑 Para detenerlo: Presiona Ctrl + C en la terminal de VS Code.")
    print("🌐" * 30 + "\n")

    last_hashes = {}

    # Estado inicial de los archivos locales
    for filename, sheet_id in SOURCES.items():
        local_path = os.path.join(RAW_DIR, filename)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                last_hashes[filename] = hashlib.sha256(f.read()).hexdigest()
        else:
            last_hashes[filename] = None

    while True:
        try:
            changes_detected = []

            for filename, sheet_id in SOURCES.items():
                try:
                    content_bytes = get_drive_sheet_content(sheet_id)
                    current_hash = hashlib.sha256(content_bytes).hexdigest()

                    # Si el hash cambió respecto a lo que tenemos guardado
                    if last_hashes.get(filename) != current_hash:
                        local_path = os.path.join(RAW_DIR, filename)
                        with open(local_path, "wb") as f:
                            f.write(content_bytes)

                        last_hashes[filename] = current_hash
                        changes_detected.append(filename)

                except Exception as err:
                    print(f"⚠️ Error consultando {filename} en Drive: {err}")

            if changes_detected:
                print(f"\n🔔 [CAMBIO DETECTADO EN GOOGLE DRIVE] -> {', '.join(changes_detected)}")
                # Dispara todo el pipeline completo
                execute_full_pipeline(trigger_source=f"GOOGLE_DRIVE_UPDATE ({', '.join(changes_detected)})")

            time.sleep(CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n🛑 Monitoreo de Google Drive detenido por el usuario.")
            break
        except Exception as e:
            print(f"⚠️ Error general en monitoreo: {e}")
            time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    start_live_sync()