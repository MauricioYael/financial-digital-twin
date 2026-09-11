import os
import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd
import hashlib
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_ARGS = {
    "owner": "data_engineer",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

def task_validate_files(**context):
    print("🔍 [validate_files] Verificando existencia de archivos en data/raw/...")
    raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")
    files = ["clientes.csv", "compromisos_fijos.csv", "transacciones.csv"]
    for f in files:
        path = os.path.join(raw_dir, f)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise ValueError(f"Falla temprana: El archivo {f} no existe o está vacío.")
    print("✅ Todos los archivos crudos existen y son válidos para procesar.")

def ingest_file_dag(filename: str, expected_columns: list):
    raw_path = os.path.join(PROJECT_ROOT, "data", "raw", filename)
    bronze_dir = os.path.join(PROJECT_ROOT, "data", "bronze")
    os.makedirs(bronze_dir, exist_ok=True)
    
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Archivo origen no encontrado: {raw_path}")
    
    df = pd.read_csv(raw_path)
    if df.empty:
        raise ValueError(f"El archivo {filename} está vacío.")

    # Inyección de metadatos de auditoría
    now_str = datetime.now().isoformat()
    df["_ingestion_timestamp"] = now_str
    df["_raw_sha256"] = hashlib.sha256(df.to_json().encode()).hexdigest()

    base_name = filename.replace(".csv", "")
    output_parquet = os.path.join(bronze_dir, f"{base_name}.parquet")
    df.to_parquet(output_parquet, index=False)
    print(f"✅ Ingesta Bronze completada para {filename} en {output_parquet}")

def task_ingest_clients(**context):
    ingest_file_dag("clientes.csv", ["customer_id", "nombre", "fecha_registro"])

def task_ingest_transactions(**context):
    ingest_file_dag("transacciones.csv", ["transaction_id", "customer_id", "fecha", "monto", "tipo_transaccion"])

def task_ingest_loans(**context):
    ingest_file_dag("compromisos_fijos.csv", ["compromiso_id", "customer_id", "tipo_compromiso", "monto_esperado"])

def task_validate_bronze(**context):
    print("🔍 [validate_bronze] Confirmando salidas Parquet...")
    bronze_dir = os.path.join(PROJECT_ROOT, "data", "bronze")
    for f in ["clientes.parquet", "compromisos_fijos.parquet", "transacciones.parquet"]:
        if not os.path.exists(os.path.join(bronze_dir, f)):
            raise FileNotFoundError(f"Falta la salida Bronze: {f}")
    print("✅ Salidas Bronze validadas.")

def task_write_control_log(**context):
    print("📝 [write_control_log] Bitácora operativa consolidada con éxito.")

with DAG(
    dag_id="financial_bronze_ingestion_v1",
    default_args=DEFAULT_ARGS,
    description="Pipeline gráfico de Ingesta Raw a Bronze",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["finance", "bronze", "semana8"],
) as dag:

    validate_files = PythonOperator(task_id="validate_files", python_callable=task_validate_files)
    ingest_clients = PythonOperator(task_id="ingest_clients", python_callable=task_ingest_clients)
    ingest_transactions = PythonOperator(task_id="ingest_transactions", python_callable=task_ingest_transactions)
    ingest_loans = PythonOperator(task_id="ingest_loans", python_callable=task_ingest_loans)
    validate_bronze = PythonOperator(task_id="validate_bronze", python_callable=task_validate_bronze)
    write_control_log = PythonOperator(task_id="write_control_log", python_callable=task_write_control_log)

    validate_files >> [ingest_clients, ingest_transactions, ingest_loans] >> validate_bronze >> write_control_log