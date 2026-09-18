import os
import hashlib
from datetime import datetime
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze")
SILVER_DIR = os.path.join(BASE_DIR, "data", "silver")
QUARANTINE_DIR = os.path.join(BASE_DIR, "data", "quarantine")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

for folder in [SILVER_DIR, QUARANTINE_DIR, REPORTS_DIR]:
    os.makedirs(folder, exist_ok=True)

def build_audit_meta(row_num, file_name, file_hash, err_code, err_detail):
    return {
        "_source_file": file_name,
        "_file_hash": file_hash,
        "_row_number": row_num,
        "_error_code": err_code,
        "_error_detail": err_detail,
        "_rejected_at": datetime.now().isoformat()
    }

def run_pipeline():
    validation_summary = []

    # 1. CLIENTES: Unicidad y Completitud de ID
    c_file = "clientes.parquet"
    c_path = os.path.join(BRONZE_DIR, c_file)
    df_c = pd.read_parquet(c_path)
    c_hash = hashlib.sha256(df_c.to_json().encode()).hexdigest()

    c_valid, c_quarantine, seen_cids = [], [], set()
    for idx, row in df_c.iterrows():
        cid = str(row.get("customer_id", "")).strip()
        if not cid or cid == "nan":
            c_quarantine.append({**row.to_dict(), **build_audit_meta(idx, c_file, c_hash, "ERR_ID_NULO", "customer_id vacio")})
        elif cid in seen_cids:
            c_quarantine.append({**row.to_dict(), **build_audit_meta(idx, c_file, c_hash, "ERR_ID_DUPLICADO", f"customer_id duplicado: {cid}")})
        else:
            seen_cids.add(cid)
            r = row.to_dict()
            r["nombre"] = str(row.get("nombre", "")).strip().title()
            c_valid.append(r)

    df_c_silver = pd.DataFrame(c_valid)
    df_c_silver.to_parquet(os.path.join(SILVER_DIR, "clientes.parquet"), index=False)
    if c_quarantine:
        pd.DataFrame(c_quarantine).to_parquet(os.path.join(QUARANTINE_DIR, "clientes_rechazados.parquet"), index=False)

    valid_cids = set(df_c_silver["customer_id"].astype(str))
    validation_summary.append({
        "dataset": "clientes",
        "bronze": len(df_c),
        "silver": len(df_c_silver),
        "rechazados": len(c_quarantine),
        "regla_critica": "customer_id único",
        "estado": "WARN" if len(c_quarantine) > 0 else "OK",
        "promueve": "si"
    })

    # 2. TRANSACCIONES: Parseo de Fechas, Montos y Referencialidad
    t_file = "transacciones.parquet"
    t_path = os.path.join(BRONZE_DIR, t_file)
    df_t = pd.read_parquet(t_path)
    t_hash = hashlib.sha256(df_t.to_json().encode()).hexdigest()

    t_valid, t_quarantine = [], []
    valid_movs = {"ingreso", "gasto", "transferencia"}

    for idx, row in df_t.iterrows():
        cid = str(row.get("customer_id", "")).strip()
        raw_monto = row.get("monto")
        raw_fecha = str(row.get("fecha", ""))
        tipo_mov = str(row.get("tipo_transaccion", "")).strip().lower()

        try:
            monto = float(raw_monto)
            monto_ok = True
        except (ValueError, TypeError):
            monto_ok = False

        try:
            fecha = pd.to_datetime(raw_fecha).strftime("%Y-%m-%d")
            fecha_ok = True
        except Exception:
            fecha_ok = False

        if not fecha_ok:
            t_quarantine.append({**row.to_dict(), **build_audit_meta(idx, t_file, t_hash, "ERR_FECHA_INVALIDA", f"Fecha no parseable: {raw_fecha}")})
        elif not monto_ok:
            t_quarantine.append({**row.to_dict(), **build_audit_meta(idx, t_file, t_hash, "ERR_MONTO_INVALIDO", f"Monto no numerico: {raw_monto}")})
        elif cid not in valid_cids:
            t_quarantine.append({**row.to_dict(), **build_audit_meta(idx, t_file, t_hash, "ERR_CLIENTE_INEXISTENTE", f"customer_id {cid} huerfano")})
        elif tipo_mov not in valid_movs:
            t_quarantine.append({**row.to_dict(), **build_audit_meta(idx, t_file, t_hash, "ERR_CATALOGO_INVALIDO", f"Tipo invalido: {tipo_mov}")})
        else:
            r = row.to_dict()
            r["fecha"] = fecha
            r["monto"] = monto
            r["tipo_transaccion"] = tipo_mov
            t_valid.append(r)

    df_t_silver = pd.DataFrame(t_valid)
    df_t_silver.to_parquet(os.path.join(SILVER_DIR, "transacciones.parquet"), index=False)
    if t_quarantine:
        pd.DataFrame(t_quarantine).to_parquet(os.path.join(QUARANTINE_DIR, "transacciones_rechazadas.parquet"), index=False)

    validation_summary.append({
        "dataset": "transacciones",
        "bronze": len(df_t),
        "silver": len(df_t_silver),
        "rechazados": len(t_quarantine),
        "regla_critica": "monto y fecha validos",
        "estado": "WARN" if len(t_quarantine) > 0 else "OK",
        "promueve": "si"
    })

    # 3. CRÉDITOS / COMPROMISOS FIJOS: Referencialidad Crítica
    cr_file = "compromisos_fijos.parquet"
    cr_path = os.path.join(BRONZE_DIR, cr_file)
    df_cr = pd.read_parquet(cr_path)
    cr_hash = hashlib.sha256(df_cr.to_json().encode()).hexdigest()

    cr_valid, cr_quarantine = [], []
    for idx, row in df_cr.iterrows():
        cid = str(row.get("customer_id", "")).strip()
        if cid not in valid_cids:
            cr_quarantine.append({**row.to_dict(), **build_audit_meta(idx, cr_file, cr_hash, "ERR_CLIENTE_INEXISTENTE", f"Cliente {cid} no existe")})
        else:
            cr_valid.append(row.to_dict())

    df_cr_silver = pd.DataFrame(cr_valid)
    df_cr_silver.to_parquet(os.path.join(SILVER_DIR, "creditos.parquet"), index=False)
    if cr_quarantine:
        pd.DataFrame(cr_quarantine).to_parquet(os.path.join(QUARANTINE_DIR, "creditos_rechazados.parquet"), index=False)

    # Si hay registros huérfanos en créditos, la regla crítica marca fallo de promoción[cite: 13]
    cr_promueve = "no" if len(cr_quarantine) > 0 else "si"
    validation_summary.append({
        "dataset": "creditos",
        "bronze": len(df_cr),
        "silver": len(df_cr_silver),
        "rechazados": len(cr_quarantine),
        "regla_critica": "cliente existente",
        "estado": "FAIL" if len(cr_quarantine) > 0 else "OK",
        "promueve": cr_promueve
    })

    # Guardar reporte de validación
    df_rep = pd.DataFrame(validation_summary)
    rep_path = os.path.join(REPORTS_DIR, "validation_report.csv")
    df_rep.to_csv(rep_path, index=False)

    print("\n" + "="*80)
    print("REPORTE MÍNIMO DE VALIDACIÓN GENERADO")
    print("="*80)
    print(df_rep.to_string(index=False))
    print(f"\nArchivo guardado en: {rep_path}\n")

if __name__ == "__main__":
    run_pipeline()