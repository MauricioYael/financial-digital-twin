import os
import hashlib
import datetime
import json
import pandas as pd

RAW_DIR = "data/raw"
BRONZE_DIR = "data/bronze"
LOGS_DIR = "logs"
LOG_FILE = os.path.join(LOGS_DIR, "ingestion_log.csv")
MANIFEST_FILE = os.path.join(BRONZE_DIR, "manifest.json")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(BRONZE_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

SCHEMAS_CONTRATO = {
    "clientes.csv": ["customer_id", "nombre", "fecha_registro"],
    "compromisos_fijos.csv": ["compromiso_id", "customer_id", "tipo_compromiso", "monto_esperado"],
    "transacciones.csv": ["transaction_id", "customer_id", "fecha", "monto", "tipo_transaccion"]
}

def calculate_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def log_execution(source_file: str, file_hash: str, rows: int, cols: int, status: str, message: str):
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_entry = pd.DataFrame([{
        "timestamp": timestamp,
        "source_file": source_file,
        "file_hash": file_hash,
        "row_count": rows,
        "column_count": cols,
        "status": status,
        "message": message
    }])
    if not os.path.exists(LOG_FILE):
        log_entry.to_csv(LOG_FILE, index=False)
    else:
        log_entry.to_csv(LOG_FILE, mode="a", header=False, index=False)

def load_manifest() -> dict:
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_manifest(manifest: dict):
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

def ingest_file(filename: str, required_columns: list, force: bool = False) -> bool:
    filepath = os.path.join(RAW_DIR, filename)
    print(f"\n🔍 [CONTRATO] Validando entrada para: {filename}")
    
    # 1. Validación: Existencia
    if not os.path.exists(filepath):
        msg = f"Archivo inexistente en ruta {RAW_DIR}"
        print(f"❌ [FALLA CONTROLADA] {msg}")
        log_execution(filename, "N/A", 0, 0, "FAILED", msg)
        return False

    # 2. Validación: Extensión
    if not filename.lower().endswith(".csv"):
        msg = "Formato no soportado (se requiere .csv)"
        print(f"❌ [RECHAZADO] {msg}")
        log_execution(filename, "N/A", 0, 0, "REJECTED", msg)
        return False

    # 3. Validación: No vacío (bytes)
    if os.path.getsize(filepath) == 0:
        msg = "Archivo vacío (0 bytes en disco)"
        print(f"❌ [RECHAZADO] {msg}")
        log_execution(filename, "N/A", 0, 0, "REJECTED", msg)
        return False

    file_hash = calculate_sha256(filepath)
    manifest = load_manifest()

    # 4. Validación: Idempotencia por Hash SHA-256
    if not force and filename in manifest and manifest[filename].get("hash") == file_hash:
        msg = "Archivo idéntico ya procesado (Idempotencia activa)"
        print(f"⏭️ [OMITIDO] {msg}")
        log_execution(filename, file_hash, manifest[filename]["rows"], 0, "SKIPPED", msg)
        return True

    # Lectura cruda
    try:
        df_raw = pd.read_csv(filepath)
    except Exception as e:
        msg = f"Error crítico al parsear CSV: {str(e)}"
        print(f"❌ [RECHAZADO] {msg}")
        log_execution(filename, file_hash, 0, 0, "REJECTED", msg)
        return False

    if len(df_raw) == 0 or len(df_raw.columns) == 0:
        msg = "Dataset con 0 filas o 0 columnas"
        print(f"❌ [RECHAZADO] {msg}")
        log_execution(filename, file_hash, 0, 0, "REJECTED", msg)
        return False

    # 5. Validación: Columnas mínimas
    missing_cols = [col for col in required_columns if col not in df_raw.columns]
    if missing_cols:
        msg = f"Esquema inválido. Faltan columnas: {missing_cols}"
        print(f"❌ [RECHAZADO] {msg}")
        log_execution(filename, file_hash, len(df_raw), len(df_raw.columns), "REJECTED", msg)
        return False

    # 6. Advertencias de tipos (sin bloquear Bronze)
    warnings = []
    if "fecha" in df_raw.columns:
        invalid_dates = pd.to_datetime(df_raw["fecha"], errors="coerce").isna().sum()
        if invalid_dates > 0:
            warnings.append(f"{invalid_dates} fechas no estándar")
    if "monto" in df_raw.columns:
        invalid_amounts = pd.to_numeric(df_raw["monto"], errors="coerce").isna().sum()
        if invalid_amounts > 0:
            warnings.append(f"{invalid_amounts} montos no numéricos")

    # Ingesta Bronze: Preservación + Metadatos de auditoría
    df_bronze = df_raw.copy()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    df_bronze["_ingestion_timestamp"] = now_iso
    df_bronze["_source_file"] = filename
    df_bronze["_raw_sha256"] = file_hash

    output_parquet = os.path.join(BRONZE_DIR, filename.replace(".csv", ".parquet"))
    df_bronze.to_parquet(output_parquet, index=False)

    status = "WARNING" if warnings else "SUCCESS"
    msg = "; ".join(warnings) if warnings else "Ingesta exitosa en Capa Bronze"
    
    manifest[filename] = {
        "hash": file_hash,
        "ingested_at": now_iso,
        "rows": len(df_bronze),
        "columns": len(df_bronze.columns),
        "parquet_path": output_parquet,
        "status": status
    }
    save_manifest(manifest)
    log_execution(filename, file_hash, len(df_bronze), len(df_bronze.columns), status, msg)
    print(f"✅ [{status}] Guardado: {output_parquet} ({len(df_bronze)} filas)")
    return True

def run_pipeline(force: bool = False):
    print("=" * 60)
    print("🚀 EJECUTANDO PIPELINE DE INGESTA (SEMANA 6)")
    print("=" * 60)
    for filename, required_cols in SCHEMAS_CONTRATO.items():
        ingest_file(filename, required_cols, force=force)
    print("\n📦 Logs: 'logs/ingestion_log.csv' | Manifest: 'data/bronze/manifest.json'")

if __name__ == "__main__":
    run_pipeline()
