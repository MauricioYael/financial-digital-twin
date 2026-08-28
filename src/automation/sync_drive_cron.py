import time
from src.ingestion.fetch_drive_data import download_sheet, SOURCES, RAW_DIR
from src.orchestration.run_pipeline_e2e import execute_full_pipeline
import os

SYNC_INTERVAL_MINUTES = 2  # Intervalo de chequeo con Google Drive

def sync_and_execute():
    print(f"🌐 Sincronizador de Google Drive activo cada {SYNC_INTERVAL_MINUTES} minutos...")
    while True:
        try:
            print(f"\n📡 [{time.strftime('%H:%M:%S')}] Verificando actualizaciones en Google Drive...")
            for filename, sheet_id in SOURCES.items():
                download_sheet(sheet_id, os.path.join(RAW_DIR, filename))
            
            # Ejecutar validación de capas
            execute_full_pipeline(trigger_source="GOOGLE_DRIVE_POLLER")
            
            time.sleep(SYNC_INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            print("🛑 Detenido.")
            break

if __name__ == "__main__":
    sync_and_execute()