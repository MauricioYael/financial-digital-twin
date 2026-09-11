import os
import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ingestion.pipeline import ingest_file

DEFAULT_ARGS = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}
def task_validate_files(**context):
    print("[validate_files] Verificando existencia de archivos en data/raw/...")
    raw_dir = os.path.join(PROJECT_ROOT, 'data', 'raw')
    files = ["clientes.csv", "compromisos_fijos.csv", "transacciones.csv"]
    for f in files:
        path = os.path.join(raw_dir, f)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise ValueError(f"Falla de forma temprana: El archivo {f} no existe o esta vacio.")
    print("Todos los archivos crudos existen y son validos para continuar con la ingesta.")

def task_ingest_files(**context):
    ingest_files("clientes.csv", ["customer_id", "nombre", "fecha_registro"])

def task_ingest_transacciones(**context):
    ingest_files("transacciones.csv", ["transaction_id", "customer_id", "fecha", "monto", "tipo_transaccion"])

def task_ingest_loans(**context):
    print(" [validate_bronze] Confirmando la existencia de las salidas Parquet correspondientes...")
    excepted = ["clientes.parquet", "compromisos_fijos.parquet", "transacciones.parquet"]
    for e in excepted:
        path = os.path.join(bronze_dir, e)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Salida Bronze incompleta: Falta {e}")
    print("✅ Todas las salidas Parquet están validadas correctamente.")

def task_write_control_log(**context):
    print("📝 [write_control_log] Consolidando bitácora de control y manifest...")
    log_path = os.path.join(PROJECT_ROOT, "logs", "ingestion_log.csv")
    if os.path.exists(log_path):
        print(f"✅ Log operativo verificado en {log_path}")
    else:
        raise FileNotFoundError("No se encontró el archivo de log de control.")

with DAG(
    dag_id="financial_bronze_ingestion_v1",
    default_args=DEFAULT_ARGS,
    description="Pipeline gráfico de Ingesta Raw a Bronze para Financial Digital Twin",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["finance", "bronze", "ingestion", "semana8"],
) as dag:

    validate_files = PythonOperator(
        task_id="validate_files",
        python_callable=task_validate_files,
    )

    ingest_clients = PythonOperator(
        task_id="ingest_clients",
        python_callable=task_ingest_clients,
    )

    ingest_transactions = PythonOperator(
        task_id="ingest_transactions",
        python_callable=task_ingest_transactions,
    )

    ingest_loans = PythonOperator(
        task_id="ingest_loans",
        python_callable=task_ingest_loans,
    )

    validate_bronze = PythonOperator(
        task_id="validate_bronze",
        python_callable=task_validate_bronze,
    )

    write_control_log = PythonOperator(
        task_id="write_control_log",
        python_callable=task_write_control_log,
    )

    # Definición de dependencias gráficas (Paralelismo de ingesta)
    validate_files >> [ingest_clients, ingest_transactions, ingest_loans] >> validate_bronze >> write_control_log