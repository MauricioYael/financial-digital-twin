import os
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SILVER_DIR = os.path.join(BASE_DIR, "data", "silver")
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "gold_cliente_mes.parquet")

def reconcile_customer_period(customer_id=None, periodo=None):
    print("🔎 INICIANDO PRUEBA DE CONCILIACIÓN: SILVER VS GOLD\n" + "="*50)
    
    # 1. Cargar datos
    tx_path = os.path.join(SILVER_DIR, "fct_transacciones.parquet")
    if not os.path.exists(tx_path) or not os.path.exists(GOLD_PATH):
        print("❌ Error: Faltan archivos de la capa Silver o Gold.")
        return

    df_silver_tx = pd.read_parquet(tx_path)
    df_gold = pd.read_parquet(GOLD_PATH)

    # Normalizar fechas a periodo YYYY-MM
    df_silver_tx['fecha_operacion'] = pd.to_datetime(df_silver_tx['fecha_operacion'])
    df_silver_tx['periodo'] = df_silver_tx['fecha_operacion'].dt.strftime('%Y-%m')

    # Seleccionar cliente y periodo si no se especifican
    if not customer_id or not periodo:
        sample_row = df_gold.iloc[0]
        customer_id = sample_row['customer_id']
        periodo = sample_row['periodo']

    print(f"📌 Auditando Cliente: {customer_id} | Periodo: {periodo}")

    # 2. Sumar directamente desde SILVER
    silver_sub = df_silver_tx[(df_silver_tx['customer_id'] == customer_id) & (df_silver_tx['periodo'] == periodo)]
    
    # Excluir transferencias propias según la regla de negocio
    if 'categoria' in silver_sub.columns:
        silver_sub = silver_sub[silver_sub['categoria'] != 'TRANSFERENCIA_PROPIA']

    silver_ingresos = silver_sub[silver_sub['tipo_movimiento'] == 'INGRESO']['monto'].sum()
    silver_gastos = silver_sub[silver_sub['tipo_movimiento'] == 'EGRESO']['monto'].sum()
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