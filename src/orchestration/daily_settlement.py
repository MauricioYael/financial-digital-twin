import os
import sys
import datetime
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SILVER_DIR = os.path.join(PROJECT_ROOT, "data", "silver")
SETTLEMENT_DIR = os.path.join(SILVER_DIR, "settlements")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

os.makedirs(SETTLEMENT_DIR, exist_ok=True)

def execute_daily_settlement(target_date: str = None):
    """
    Genera el corte de caja diario, sella el balance del día y abre el archivo del nuevo día.
    """
    if not target_date:
        target_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    print("\n" + "🏁" * 30)
    print(f"💼 INICIANDO CORTE DE CAJA DIARIO: Fecha [{target_date}]")
    print("🏁" * 30)

    silver_tx_path = os.path.join(SILVER_DIR, "fct_transacciones.parquet")
    if not os.path.exists(silver_tx_path):
        print("❌ No existe fct_transacciones.parquet en Silver para conciliar.")
        return

    df_tx = pd.read_parquet(silver_tx_path)
    df_tx["fecha_str"] = pd.to_datetime(df_tx["fecha"]).dt.strftime("%Y-%m-%d")

    # Filtrar solo el día de corte
    daily_tx = df_tx[df_tx["fecha_str"] == target_date]
    if daily_tx.empty:
        print(f"⚠️ No hay transacciones registradas para el día {target_date}.")
        return

    # Cálculos del corte
    ingresos = daily_tx[daily_tx["tipo_transaccion"] == "Ingreso"]["monto"].sum()
    gastos = daily_tx[daily_tx["tipo_transaccion"] == "Gasto"]["monto"].sum()
    balance_neto = ingresos - gastos
    total_operaciones = len(daily_tx)

    settlement_report = {
        "fecha_corte": target_date,
        "timestamp_cierre": datetime.datetime.now().isoformat(),
        "total_operaciones": total_operaciones,
        "total_ingresos": float(ingresos),
        "total_gastos": float(gastos),
        "balance_neto": float(balance_neto)
    }

    # Guardar reporte de corte inmutable
    report_path = os.path.join(SETTLEMENT_DIR, f"corte_{target_date}.json")
    pd.Series(settlement_report).to_json(report_path, indent=4)

    print("\n📊 BALANCE FINAL DEL DÍA:")
    print(f"   • Total de Operaciones: {total_operaciones}")
    print(f"   • Total Ingresos:       ${ingresos:,.2f}")
    print(f"   • Total Gastos:         ${gastos:,.2f}")
    print(f"   • Balance Neto Diario:  ${balance_neto:,.2f}")
    print(f"🔒 Corte sellado y guardado en: {report_path}")

    # Preparar el archivo de trabajo para el nuevo día sin sobreescribir el historial
    tomorrow_date = datetime.datetime.now().strftime("%Y-%m-%d")
    new_day_file = os.path.join(RAW_DIR, f"transacciones_{tomorrow_date}.csv")
    if not os.path.exists(new_day_file):
        cols = ["transaction_id", "customer_id", "fecha", "monto", "tipo_transaccion", "categoria", "estatus"]
        pd.DataFrame(columns=cols).to_csv(new_day_file, index=False)
        print(f"✨ Plantilla para nuevo día creada: {new_day_file}")

    print("🏁 Corte de caja finalizado exitosamente.\n")

if __name__ == "__main__":
    # Si no se pasa fecha, toma la fecha de hoy
    execute_daily_settlement(datetime.datetime.now().strftime("%Y-%m-%d"))