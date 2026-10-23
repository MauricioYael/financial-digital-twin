import os
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SILVER_DIR = os.path.join(BASE_DIR, "data", "silver")
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "gold_cliente_mes.parquet")


def find_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def reconcile_customer_period(customer_id=None, periodo=None):
    print("🔎 INICIANDO PRUEBA DE CONCILIACIÓN: SILVER VS GOLD\n" + "=" * 50)

    # 1. Cargar datos con fallback de nombre de archivo
    tx_path = os.path.join(SILVER_DIR, "transacciones.parquet")
    if not os.path.exists(tx_path):
        tx_path = os.path.join(SILVER_DIR, "fct_transacciones.parquet")

    if not os.path.exists(tx_path) or not os.path.exists(GOLD_PATH):
        print("❌ Error: Faltan archivos de la capa Silver o Gold.")
        return

    df_silver_tx = pd.read_parquet(tx_path)
    df_gold = pd.read_parquet(GOLD_PATH)

    # Detectar nombres de columnas dinámicamente
    col_fecha = find_column(df_silver_tx, ['fecha_operacion', 'fecha', 'fecha_transaccion', 'date'])
    col_cliente = find_column(df_silver_tx, ['customer_id', 'cliente_id', 'id_cliente'])
    col_tipo = find_column(df_silver_tx, ['tipo_movimiento', 'tipo_transaccion', 'tipo', 'type'])
    col_monto = find_column(df_silver_tx, ['monto', 'monto_total', 'amount'])

    if not col_fecha or not col_cliente or not col_tipo or not col_monto:
        print(f"❌ Error: Columnas no encontradas en Silver. Presentes: {list(df_silver_tx.columns)}")
        return

    # Normalizar fechas a periodo YYYY-MM
    df_silver_tx['fecha_normalizada'] = pd.to_datetime(df_silver_tx[col_fecha], errors='coerce')
    df_silver_tx['periodo'] = df_silver_tx['fecha_normalizada'].dt.strftime('%Y-%m')

    # Seleccionar cliente y periodo por defecto si no se especifican
    if not customer_id or not periodo:
        sample_row = df_gold.iloc[0]
        customer_id = sample_row['customer_id']
        periodo = sample_row['periodo']

    print(f"📌 Auditando Cliente: {customer_id} | Periodo: {periodo}")

    # 2. Sumar directamente desde SILVER
    silver_sub = df_silver_tx[(df_silver_tx[col_cliente] == customer_id) & (df_silver_tx['periodo'] == periodo)]

    if 'categoria' in silver_sub.columns:
        silver_sub = silver_sub[silver_sub['categoria'].astype(str).str.upper() != 'TRANSFERENCIA_PROPIA']

    tipo_series = silver_sub[col_tipo].astype(str).str.upper()
    silver_ingresos = silver_sub[tipo_series.isin(['INGRESO', 'INGRESOS', 'INCOME'])][col_monto].sum()
    silver_gastos = silver_sub[tipo_series.isin(['EGRESO', 'EGRESOS', 'GASTO', 'GASTOS', 'EXPENSE'])][col_monto].sum()
    silver_flujo = silver_ingresos - silver_gastos

    # 3. Leer fila consolidada en GOLD
    gold_sub = df_gold[(df_gold['customer_id'] == customer_id) & (df_gold['periodo'] == periodo)]

    if gold_sub.empty:
        print(f"❌ Error: El cliente {customer_id} no existe en Gold para el periodo {periodo}")
        return

    gold_ingresos = gold_sub.iloc[0]['ingresos_totales']
    gold_gastos = gold_sub.iloc[0]['gastos_totales']
    gold_flujo = gold_sub.iloc[0]['flujo_neto']

    # 4. Comparación y Cuadre
    diff_ing = abs(silver_ingresos - gold_ingresos)
    diff_gas = abs(silver_gastos - gold_gastos)
    diff_flujo = abs(silver_flujo - gold_flujo)

    print("\n--- RESULTADOS DE AUDITORÍA ---")
    print(f"Métrica\t\tSilver (Suma Directa)\tGold (Consolidado)\tDiferencia")
    print(f"Ingresos:\t${silver_ingresos:,.2f}\t\t\t${gold_ingresos:,.2f}\t\t\t${diff_ing:,.2f}")
    print(f"Gastos:\t\t${silver_gastos:,.2f}\t\t\t${gold_gastos:,.2f}\t\t\t${diff_gas:,.2f}")
    print(f"Flujo Neto:\t${silver_flujo:,.2f}\t\t\t${gold_flujo:,.2f}\t\t\t${diff_flujo:,.2f}")

    if diff_ing < 0.01 and diff_gas < 0.01 and diff_flujo < 0.01:
        print("\n✅ CONCILIACIÓN EXITOSA: Los números en Gold cuadran perfectamente con Silver.")
    else:
        print("\n❌ CONCILIACIÓN FALLIDA: Existen discrepancias entre Silver y Gold.")


if __name__ == "__main__":
    reconcile_customer_period()