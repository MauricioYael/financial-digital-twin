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
    df_clientes.to_parquet(os.path.join(SILVER_DIR, "clientes.parquet"), index=False)
    
    df_compromisos.drop_duplicates(subset=["compromiso_id"], inplace=True)
    df_compromisos.to_parquet(os.path.join(SILVER_DIR, "dim_compromisos_fijos.parquet"), index=False)
    df_compromisos.to_parquet(os.path.join(SILVER_DIR, "creditos.parquet"), index=False)
    
    # 3. Validar y filtrar Transacciones
    valid_customer_ids = set(df_clientes["customer_id"].astype(str))
    compromisos_categorias = set(df_compromisos["tipo_compromiso"].astype(str).str.strip().str.title())
    
    indices_to_drop = []
    for idx, row in df_tx.iterrows():
        errors = []
        
        # Validar parseo de fecha flexible (evita que el 31 de febrero rompa el script)
        parsed_date = pd.to_datetime(row.get("fecha"), errors="coerce")
        if pd.isna(parsed_date):
            errors.append("ERR_INVALID_DATE_FORMAT")

        # QC-002: Monto nulo o no positivo
        raw_monto = row.get("monto")
        try:
            monto_val = float(raw_monto)
            if monto_val <= 0:
                errors.append("ERR_INVALID_OR_NEGATIVE_AMOUNT")
        except (ValueError, TypeError):
            errors.append("ERR_NON_NUMERIC_AMOUNT")
            
        # QC-003: Cliente inexistente
        cid = str(row.get("customer_id", "")).strip()
        if not cid or cid not in valid_customer_ids:
            errors.append("ERR_ORPHAN_CUSTOMER_ID")
            
        # QC-005: Transaccion no completada
        if str(row.get("estatus", "")).strip().lower() != "completada":
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
    
    # Casting seguro y Enriquecimiento (es_fijo)
    df_tx["fecha"] = pd.to_datetime(df_tx["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")
    df_tx["monto"] = df_tx["monto"].astype(float)
    
    # Matching de tipo_transaccion insensible a mayúsculas/minúsculas
    df_tx["es_fijo"] = df_tx.apply(
        lambda r: True if str(r.get("tipo_transaccion", "")).strip().title() == "Gasto" 
                          and str(r.get("categoria", "")).strip().title() in compromisos_categorias else False, 
        axis=1
    )
    
    # 4. Guardar Silver (ambos nombres para asegurar compatibilidad total)
    df_tx.to_parquet(os.path.join(SILVER_DIR, "fct_transacciones.parquet"), index=False)
    df_tx.to_parquet(os.path.join(SILVER_DIR, "transacciones.parquet"), index=False)
    print(f"✓ Guardado Silver: {SILVER_DIR}/transacciones.parquet ({len(df_tx)} filas limpias)")
    
    if quarantine_records:
        df_quarantine = pd.DataFrame(quarantine_records)
        df_quarantine.to_parquet(os.path.join(QUARANTINE_DIR, "transacciones_cuarentena.parquet"), index=False)
        print(f"⚠️ Guardado Cuarentena: {QUARANTINE_DIR}/transacciones_cuarentena.parquet ({len(df_quarantine)} filas rechazadas)")
        
    print("✅ TRANSFORMACIÓN SILVER Y CUARENTENA COMPLETADA")

if __name__ == "__main__":
    process_silver()