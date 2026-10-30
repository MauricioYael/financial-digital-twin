import os
import sys
import datetime
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ingestion.fetch_drive_data import download_sheet, SOURCES, RAW_DIR
from src.ingestion.incremental_pipeline import ingest_incremental
from src.quality.queue_and_alerts import inspect_traffic_and_queue
from src.quality.profile_data import run_profiling
from src.transformations.transform_silver import process_silver

# Importar el generador de la Capa Gold
from src.gold_builder import build_gold_layer

def execute_full_pipeline(trigger_source: str = "MANUAL"):
    start_time = datetime.datetime.now()
    print("\n" + "=" * 70)
    print(f"⚡ PIPELINE E2E UNIFICADO | Origen: {trigger_source}")
    print(f"🕒 Inicio: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        # FASE 0: Sincronización automática desde Google Drive
        print("\n--- [FASE 0/4] Sincronización con Google Drive ---")
        for filename, sheet_id in SOURCES.items():
            download_sheet(sheet_id, os.path.join(RAW_DIR, filename))

        # FASE 1: Ingesta Incremental
        print("\n--- [FASE 1/4] Ingesta Incremental y Análisis de Tráfico ---")
        tx_path = os.path.join(RAW_DIR, "transacciones.csv")
        if os.path.exists(tx_path):
            df_tx_raw = pd.read_csv(tx_path)
            inspect_traffic_and_queue(df_tx_raw)
            ingest_incremental(tx_path)

        # FASE 2: Perfilado de Datos
        print("\n--- [FASE 2/4] Perfilado y Auditoría de Calidad ---")
        run_profiling()

        # FASE 3: Transformación Silver
        print("\n--- [FASE 3/4] Transformación Silver y Aislamiento de Errores ---")
        process_silver()

        # FASE 4: Consolidación Capa Gold y Feature Engineering
        print("\n--- [FASE 4/4] Consolidación Capa Gold y Feature Engineering ---")
        build_gold_layer()

        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 70)
        print(f"🎉 PIPELINE E2E COMPLETADO EXITOSAMENTE en {elapsed:.2f} segundos")
        print("=" * 70 + "\n")
        return True

    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO EN PIPELINE E2E: {str(e)}")
        return False

if __name__ == "__main__":
    execute_full_pipeline("EJECUCIÓN MANUAL")