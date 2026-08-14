import os
import glob
import hashlib
import logging
from datetime import datetime, timezone
import pandas as pd
import yaml
from dotenv import load_dotenv

load_dotenv()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

with open("config/pipeline.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.get("log_path", "logs/ingestion.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def compute_sha256(file_path: str) -> str:
    """Calcula el hash SHA-256 inmutable de un archivo de origen."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def create_dummy_raw_if_empty(raw_dir: str):
    """Crea los datasets sinteticos de prueba si la carpeta raw esta vacia."""
    os.makedirs(raw_dir, exist_ok=True)
    
    # 1. transacciones_dummy.csv
    csv_transacciones = os.path.join(raw_dir, "transacciones_dummy.csv")
    if not os.path.exists(csv_transacciones):
        dummy_df = pd.DataFrame([
            {"transaction_id": "T000001", "customer_id": "C0001", "fecha": "2026-01-02", "tipo_transaccion": "Ingreso", "categoria": "Nomina", "monto": 2850.00, "canal": "Transferencia", "estatus": "Completada"},
            {"transaction_id": "T000002", "customer_id": "C0001", "fecha": "2026-01-04", "tipo_transaccion": "Gasto", "categoria": "Vivienda", "monto": 670.01, "canal": "Domiciliacion", "estatus": "Completada"},
            {"transaction_id": "T000003", "customer_id": "C0001", "fecha": "2026-01-05", "tipo_transaccion": "Gasto", "categoria": "Supermercado", "monto": 145.50, "canal": "Tarjeta Debito", "estatus": "Completada"}
        ])
        dummy_df.to_csv(csv_transacciones, index=False)
        logging.info("Generado dataset sintetico: %s", csv_transacciones)

    # 2. clientes_dummy.csv
    csv_clientes = os.path.join(raw_dir, "clientes_dummy.csv")
    if not os.path.exists(csv_clientes):
        dummy_clientes = pd.DataFrame([
            {"customer_id": "C0001", "nombre": "Ana", "edad": 29, "ocupacion": "Analista de datos", "ingreso_mensual_base": 2850.00, "saldo_inicial_cuenta": 1200.00, "fecha_alta": "2024-01-15"}
        ])
        dummy_clientes.to_csv(csv_clientes, index=False)
        logging.info("Generado dataset sintetico: %s", csv_clientes)

    # 3. compromisos_fijos_dummy.csv
    csv_compromisos = os.path.join(raw_dir, "compromisos_fijos_dummy.csv")
    if not os.path.exists(csv_compromisos):
        dummy_comp = pd.DataFrame([
            {"compromiso_id": "K00001", "customer_id": "C0001", "concepto": "Renta Depa", "tipo_compromiso": "Vivienda", "monto_mensual": 670.00, "dia_pago_mes": 5, "estado": "Activo"}
        ])
        dummy_comp.to_csv(csv_compromisos, index=False)
        logging.info("Generado dataset sintetico: %s", csv_compromisos)

def run_pipeline():
    raw_dir = config.get("raw_path", "data/raw")
    bronze_dir = config.get("bronze_path", "data/bronze")
    os.makedirs(bronze_dir, exist_ok=True)

    # Asegurar existencia de datos sinteticos
    create_dummy_raw_if_empty(raw_dir)

    raw_files = glob.glob(os.path.join(raw_dir, "*.csv"))
    logging.info("==========================================")
    logging.info("🚀 INICIANDO PIPELINE DE INGESTA A BRONZE")
    logging.info("==========================================")
    logging.info("Archivos CSV encontrados en raw: %d", len(raw_files))

    for file_path in raw_files:
        filename = os.path.basename(file_path)
        base_name = os.path.splitext(filename)[0]
        
        # 1. Auditoria e Integridad SHA-256
        file_hash = compute_sha256(file_path)
        ingested_at = datetime.now(timezone.utc).isoformat()

        logging.info("Procesando: %s | SHA-256: %s", filename, file_hash)

        # 2. Lectura inmutable de los datos crudos
        df = pd.read_csv(file_path)

        # 3. Insercion de columnas de trazabilidad y gobernanza
        df["_ingested_at"] = ingested_at
        df["_source_file"] = filename
        df["_sha256_hash"] = file_hash

        # 4. Persistencia en formato columnar Parquet (Capa Bronze)
        output_parquet = os.path.join(bronze_dir, f"{base_name}.parquet")
        df.to_parquet(output_parquet, index=False)

        logging.info("✓ Guardado exitoso en Bronze: %s (%d registros)", output_parquet, len(df))

    logging.info("==========================================")
    logging.info("🎉 PIPELINE RAW -> BRONZE COMPLETADO")
    logging.info("==========================================")

if __name__ == "__main__":
    run_pipeline()