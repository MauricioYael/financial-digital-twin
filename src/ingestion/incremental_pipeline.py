import os
import sys
import glob
import datetime
import hashlib
import json
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
BRONZE_DIR = os.path.join(DATA_DIR, "bronze")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
WATERMARK_FILE = os.path.join(DATA_DIR, "bronze", "watermark.json")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(BRONZE_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

def get_watermark() -> dict:
    if os.path.exists(WATERMARK_FILE):
        with open(WATERMARK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_processed_timestamp": "1970-01-01T00:00:00"}

def update_watermark(latest_ts: str):
    with open(WATERMARK_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_processed_timestamp": latest_ts}, f, indent=4)

def ingest_incremental(source_file_path: str, is_reprocess: bool = False, reprocess_date: str = None):
    """
    Ingesta incremental con particionamiento por fecha y trazabilidad temporal desacoplada.
    """
    print("\n" + "=" * 65)
    print(f"📥 EJECUTANDO INGESTA {'[REPROCESAMIENTO]' if is_reprocess else '[INCREMENTAL]'}")
    print(f"📄 Archivo origen: {source_file_path}")
    print("=" * 65)

    if not os.path.exists(source_file_path):
        print(f"❌ Error: Archivo {source_file_path} no existe.")
        return

    df = pd.read_csv(source_file_path)
    if df.empty:
        print("⚠️ Archivo sin registros.")
        return

    # Normalizar timestamp del evento
    df["fecha_evento_dt"] = pd.to_datetime(df["fecha"])
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # Tiempos de Carga Desacoplados (Auditoría Técnica)
    df["fecha_carga"] = now_utc.strftime("%Y-%m-%d")
    df["hora_carga"] = now_utc.strftime("%H:%M:%S")
    
    # Tiempos del Evento de Negocio
    df["fecha_evento"] = df["fecha_evento_dt"].dt.strftime("%Y-%m-%d")
    df["hora_evento"] = df["fecha_evento_dt"].dt.strftime("%H:%M:%S")

    # Lógica Incremental vs Reprocesamiento
    if is_reprocess and reprocess_date:
        print(f"🔄 Filtrando únicamente fecha para reprocesamiento: {reprocess_date}")
        df_to_process = df[df["fecha_evento"] == reprocess_date].copy()
    else:
        watermark = get_watermark()
        last_ts = watermark["last_processed_timestamp"]
        print(f"⏱️ Watermark actual: {last_ts}")
        df_to_process = df[df["fecha_evento_dt"] > pd.to_datetime(last_ts)].copy()

    if df_to_process.empty:
        print("⏭️ No hay registros nuevos posteriores al Watermark. Carga omitida.")
        return

    # Almacenar en RAW Histórico particionado por Día para evitar sobreescritura
    for date_str, group in df_to_process.groupby("fecha_evento"):
        daily_raw_dir = os.path.join(RAW_DIR, date_str)
        os.makedirs(daily_raw_dir, exist_ok=True)
        
        # Archivo particionado por hora o lote de carga
        batch_filename = f"transacciones_batch_{now_utc.strftime('%H%M%S')}.csv"
        raw_partition_path = os.path.join(daily_raw_dir, batch_filename)
        group.to_csv(raw_partition_path, index=False)
        print(f"📁 Partición RAW guardada: {raw_partition_path} ({len(group)} filas)")

    # Almacenar en Bronze Particionado (Parquet)
    # Metadatos Bronze
    df_to_process["_raw_sha256"] = hashlib.sha256(df_to_process.to_json().encode()).hexdigest()
    df_to_process["_ingestion_mode"] = "REPROCESS" if is_reprocess else "INCREMENTAL"

    bronze_partition_dir = os.path.join(BRONZE_DIR, "transacciones_particionadas")
    # Escritura particionada por fecha_evento nativa en Parquet
    df_to_process.drop(columns=["fecha_evento_dt"]).to_parquet(
        bronze_partition_dir,
        partition_cols=["fecha_evento"],
        index=False,
        existing_data_behavior="overwrite_or_ignore"
    )
    print(f"✅ Ingesta Bronze particionada exitosa en: {bronze_partition_dir}")

    # Actualizar watermark si no es reprocesamiento histórico
    if not is_reprocess:
        max_ts = df_to_process["fecha_evento_dt"].max().isoformat()
        update_watermark(max_ts)
        print(f"🎯 Watermark actualizado a: {max_ts}")

if __name__ == "__main__":
    # Prueba con archivo base
    sample_file = os.path.join(RAW_DIR, "transacciones.csv")
    if os.path.exists(sample_file):
        ingest_incremental(sample_file)
    else:
        print(f"Coloca un archivo transacciones.csv en {RAW_DIR} para probar.")