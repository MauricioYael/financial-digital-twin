import os
import pandas as pd
import numpy as np

BRONZE_DIR = "data/bronze"
SILVER_DIR = "data/silver"
QUARANTINE_DIR = "data/quarantine"

os.makedirs(SILVER_DIR, exist_ok=True)
os.makedirs(QUARANTINE_DIR, exist_ok=True)

def process_silver():
    print("🚀 INICIANDO TRANSFORMACIÓN: BRONZE -> SILVER")
    
    # 1. Cargar datos Bronze
    df_clientes = pd.read_parquet(os.path.join(BRONZE_DIR, "clientes.parquet"))
    df_compromisos = pd.read_parquet(os.path.join(BRONZE_DIR, "compromisos_fijos.parquet"))
    df_tx = pd.read_parquet(os.path.join(BRONZE_DIR, "transacciones.parquet"))
    
    quarantine_records = []
    
    # 2. Validaciones Clientes y Compromisos
    df_clientes.drop_duplicates(subset=["customer_id"], inplace=True)
    df_clientes.to_parquet(os.path.join(SILVER_DIR, "dim_clientes.parquet"), index=False)
    
    df_compromisos.drop_duplicates(subset=["compromiso_id"], inplace=True)
    df_compromisos.to_parquet(os.path.join(SILVER_DIR, "dim_compromisos_fijos.parquet"), index=False)
    
    # 3. Validar y filtrar Transacciones
    valid_customer_ids = set(df_clientes["customer_id"])
    compromisos_categorias = set(df_compromisos["tipo_compromiso"])
    
    indices_to_drop = []
    for idx, row in df_tx.iterrows():
        errors = []
        
        # QC-002: Monto nulo o no positivo
        if pd.isna(row["monto"]) or row["monto"] <= 0:
            errors.append("ERR_INVALID_OR_NEGATIVE_AMOUNT")
            
        # QC-003: Cliente inexistente
        if pd.isna(row["customer_id"]) or row["customer_id"] not in valid_customer_ids:
            errors.append("ERR_ORPHAN_CUSTOMER_ID")
            
        # QC-005: Transaccion no completada
        if row.get("estatus") != "Completada":
            errors.append("ERR_TX_REJECTED_OR_FAILED")
            
        if errors:
            row_dict = row.to_dict()
            row_dict["error_code"] = "; ".join(errors)
            quarantine_records.append(row_dict)
            indices_to_drop.append(idx)
            
    df_tx.drop(index=indices_to_drop, inplace=True)
    
    # QC-001: Deduplicacion en Transacciones
    dups = df_tx[df_tx.duplicated(subset=["transaction_id"], keep="first")]
    for _, row in dups.iterrows():
        row_dict = row.to_dict()
        row_dict["error_code"] = "ERR_DUPLICATE_TX_ID"
        quarantine_records.append(row_dict)
        
    df_tx = df_tx.drop_duplicates(subset=["transaction_id"], keep="first")
    
    # Casting y Enriquecimiento (es_fijo)
    df_tx["fecha"] = pd.to_datetime(df_tx["fecha"]).dt.date
    df_tx["monto"] = df_tx["monto"].astype(float)
    df_tx["es_fijo"] = df_tx.apply(
        lambda r: True if r["tipo_transaccion"] == "Gasto" and r["categoria"] in compromisos_categorias else False, 
        axis=1
    )
    
    # 4. Guardar Silver y Cuarentena
    df_tx.to_parquet(os.path.join(SILVER_DIR, "fct_transacciones.parquet"), index=False)
    print(f"✓ Guardado Silver: {SILVER_DIR}/fct_transacciones.parquet ({len(df_tx)} filas limpias)")
    
    if quarantine_records:
        df_quarantine = pd.DataFrame(quarantine_records)
        df_quarantine.to_parquet(os.path.join(QUARANTINE_DIR, "transacciones_cuarentena.parquet"), index=False)
        print(f"⚠️ Guardado Cuarentena: {QUARANTINE_DIR}/transacciones_cuarentena.parquet ({len(df_quarantine)} filas rechazadas)")
        
    print("✅ TRANSFORMACIÓN SILVER Y CUARENTENA COMPLETADA")

if __name__ == "__main__":
    process_silver()
