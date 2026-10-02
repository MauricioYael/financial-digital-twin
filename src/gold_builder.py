import os
import pandas as pd
import numpy as np

# Definición de rutas
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SILVER_DIR = os.path.join(BASE_DIR, "data", "silver")
GOLD_DIR = os.path.join(BASE_DIR, "data", "gold")

os.makedirs(GOLD_DIR, exist_ok=True)

def build_gold_layer():
    print("🚀 Iniciando generación de la Capa Gold (gold_cliente_mes)...")
    
    # 1. Cargar fuentes Silver
    tx_path = os.path.join(SILVER_DIR, "transacciones.parquet")
    cred_path = os.path.join(SILVER_DIR, "creditos.parquet")
    cli_path = os.path.join(SILVER_DIR, "clientes.parquet")
    
    if not os.path.exists(tx_path):
        print("❌ Error: No se encontró la capa Silver de transacciones.")
        return

    df_tx = pd.read_parquet(tx_path)
    df_cred = pd.read_parquet(cred_path) if os.path.exists(cred_path) else pd.DataFrame()
    df_cli = pd.read_parquet(cli_path) if os.path.exists(cli_path) else pd.DataFrame()

    # 2. Preparar periodos (Mes Calendario: YYYY-MM)
    df_tx['fecha_operacion'] = pd.to_datetime(df_tx['fecha_operacion'])
    df_tx['periodo'] = df_tx['fecha_operacion'].dt.strftime('%Y-%m')

    # Excluir transferencias internas
    if 'categoria' in df_tx.columns:
        df_tx = df_tx[df_tx['categoria'] != 'TRANSFERENCIA_PROPIA']

    # 3. Calcular Agregaciones de Transacciones
    # Ingresos Totales
    ingresos = df_tx[df_tx['tipo_movimiento'] == 'INGRESO'].groupby(['customer_id', 'periodo'])['monto'].sum().reset_index()
    ingresos.rename(columns={'monto': 'ingresos_totales'}, inplace=True)

    # Gastos Totales
    gastos = df_tx[df_tx['tipo_movimiento'] == 'EGRESO'].groupby(['customer_id', 'periodo'])['monto'].sum().reset_index()
    gastos.rename(columns={'monto': 'gastos_totales'}, inplace=True)

    # Gastos Fijos vs Variables
    gastos_fijos = df_tx[(df_tx['tipo_movimiento'] == 'EGRESO') & (df_tx['es_fijo'] == True)].groupby(['customer_id', 'periodo'])['monto'].sum().reset_index()
    gastos_fijos.rename(columns={'monto': 'gastos_fijos'}, inplace=True)

    gastos_var = df_tx[(df_tx['tipo_movimiento'] == 'EGRESO') & (df_tx['es_fijo'] == False)].groupby(['customer_id', 'periodo'])['monto'].sum().reset_index()
    gastos_var.rename(columns={'monto': 'gastos_variables'}, inplace=True)

    # 4. Agregación de Créditos (Deuda mensual)
    if not df_cred.empty and 'pago_mensual' in df_cred.columns:
        deuda = df_cred.groupby('customer_id')['pago_mensual'].sum().reset_index()
        deuda.rename(columns={'pago_mensual': 'pago_deuda_mensual'}, inplace=True)
    else:
        deuda = pd.DataFrame(columns=['customer_id', 'pago_deuda_mensual'])

    # 5. Consolidación de Tabla Gold
    # Obtener todas las combinaciones cliente-periodo
    base_keys = df_tx[['customer_id', 'periodo']].drop_duplicates()

    df_gold = base_keys.merge(ingresos, on=['customer_id', 'periodo'], how='left')
    df_gold = df_gold.merge(gastos, on=['customer_id', 'periodo'], how='left')
    df_gold = df_gold.merge(gastos_fijos, on=['customer_id', 'periodo'], how='left')
    df_gold = df_gold.merge(gastos_var, on=['customer_id', 'periodo'], how='left')
    df_gold = df_gold.merge(deuda, on='customer_id', how='left')

    # Rellenar ceros en montos
    fill_cols = ['ingresos_totales', 'gastos_totales', 'gastos_fijos', 'gastos_variables', 'pago_deuda_mensual']
    df_gold[fill_cols] = df_gold[fill_cols].fillna(0.0)

    # 6. Cálculo de KPIs Derivados
    df_gold['flujo_neto'] = df_gold['ingresos_totales'] - df_gold['gastos_totales']
    
    # Tasa de ahorro (evitar división por cero)
    df_gold['tasa_ahorro'] = np.where(
        df_gold['ingresos_totales'] > 0,
        np.maximum(0.0, df_gold['flujo_neto'] / df_gold['ingresos_totales']),
        0.0
    )

    # Ratio Fijo
    df_gold['ratio_fijo'] = np.where(
        df_gold['gastos_totales'] > 0,
        df_gold['gastos_fijos'] / df_gold['gastos_totales'],
        0.0
    )

    # Ratio Endeudamiento
    df_gold['ratio_endeudamiento'] = np.where(
        df_gold['ingresos_totales'] > 0,
        df_gold['pago_deuda_mensual'] / df_gold['ingresos_totales'],
        0.0
    )

    # Redondeo de decimales para analítica
    cols_round = ['ingresos_totales', 'gastos_totales', 'gastos_fijos', 'gastos_variables', 'flujo_neto', 'pago_deuda_mensual']
    df_gold[cols_round] = df_gold[cols_round].round(2)
    
    cols_ratios = ['tasa_ahorro', 'ratio_fijo', 'ratio_endeudamiento']
    df_gold[cols_ratios] = df_gold[cols_ratios].round(4)

    # 7. Guardar Parquet de salida
    output_path = os.path.join(GOLD_DIR, "gold_cliente_mes.parquet")
    df_gold.to_parquet(output_path, index=False)
    print(f"✅ Tabla Gold generada exitosamente en: {output_path}")
    print(f"📊 Registros procesados: {len(df_gold)}")

if __name__ == "__main__":
    build_gold_layer()