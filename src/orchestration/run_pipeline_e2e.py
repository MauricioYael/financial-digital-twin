import os
import sys
import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ingestion.pipeline import run_pipeline as ingest_bronze_pipeline
from src.quality.profile_data import run_profiling
from src.transformations.transform_silver import process_silver

def execute_full_pipeline(trigger_source: str = "MANUAL"):
    start_time = datetime.datetime.now()
    print("\n" + "=" * 70)
    print(f"⚡ DISPARO AUTOMÁTICO DE PIPELINE | Origen: {trigger_source}")
    print(f"🕒 Inicio: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        # FASE 1: Contrato de Ingesta y Persistencia Bronze
        print("\n--- [FASE 1/3] Ingesta a Capa Bronze & Validación de Contrato ---")
        ingest_bronze_pipeline(force=False)

        # FASE 2: Perfilado Estadístico y Calidad de Datos
        print("\n--- [FASE 2/3] Auditoría y Perfilado de Datos ---")
        run_profiling()

        # FASE 3: Transformación a Capa Silver y Cuarentena
        print("\n--- [FASE 3/3] Transformación a Silver y Aislamiento de Errores ---")
        process_silver()

        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 70)
        print(f"🎉 PIPELINE COMPLETADO EXITOSAMENTE en {elapsed:.2f} segundos")
        print("=" * 70 + "\n")
        return True

    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO EN LA EJECUCIÓN AUTOMÁTICA: {str(e)}")
        return False

if __name__ == "__main__":
    execute_full_pipeline("EJECUCIÓN MANUAL")