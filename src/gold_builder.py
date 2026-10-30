import os
import sys
import pandas as pd
import numpy as np

# Configurar rutas para importar módulos internos de forma segura
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

SRC_DIR = os.path.dirname(__file__)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Importación segura de feature_engineering
try:
    from feature_engineering import build_feature_matrix
except ModuleNotFoundError:
    try:
        from src.feature_engineering import build_feature_matrix
    except ModuleNotFoundError:
        print("⚠️ Advertencia: No se encontró el módulo 'feature_engineering'. Se omitirá la matriz ML.")
        def build_feature_matrix():
            pass

SILVER_DIR = os.path.join(BASE_DIR, "data", "silver")
GOLD_DIR = os.path.join(BASE_DIR, "data", "gold")

os.makedirs(GOLD_DIR, exist_ok=True)


def find_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def build_gold_layer():
    print("🚀 Iniciando generación de la Capa Gold (gold_cliente_mes)...")

    # 1. Cargar fuentes Silver con fallback de compatibilidad
    tx_path = os.path.join(SILVER_DIR, "transacciones.parquet")
    if not os.path.exists(tx_path):
        tx_path = os.path.join(SILVER_DIR, "fct_transacciones.parquet")

    cred_path = os.path.join(SILVER_DIR, "creditos.parquet")
    if not os.path.exists(cred_path):
        cred_path = os.path.join(SILVER_DIR, "dim_compromisos_fijos.parquet")

    cli_path = os.path.join(SILVER_DIR, "clientes.parquet")
    if not os.path.exists(cli_path):
        cli_path = os.path.join(SILVER_DIR, "dim_clientes.parquet")

    if not os.path.exists(tx_path):
        print(f"❌ Error: No se encontró el archivo de transacciones en {tx_path}")
        return

    df_tx = pd.read_parquet(tx_path)
    df_cred = pd.read_parquet(cred_path) if os.path.exists(cred_path) else pd.DataFrame()
    df_cli = pd.read_parquet(cli_path) if os.path.exists(cli_path) else pd.DataFrame()

    # 2. Identificar columnas clave
    col_fecha = find_column(df_tx, ['fecha_operacion', 'fecha', 'fecha_transaccion', 'date', 'fecha_tx', 'timestamp'])
    col_cliente = find_column(df_tx, ['customer_id', 'cliente_id', 'id_cliente', 'user_id'])
    col_tipo = find_column(df_tx, ['tipo_movimiento', 'tipo', 'tipo_transaccion', 'type'])
    col_monto = find_column(df_tx, ['monto', 'monto_total', 'amount', 'valor'])

    if not col_fecha or not col_cliente:
        print("❌ Error: Faltan columnas clave de fecha o cliente en transacciones.")
        return

    # 3. Normalizar nombres
    rename_map = {col_fecha: 'fecha_operacion', col_cliente: 'customer_id'}
    if col_tipo: rename_map[col_tipo] = 'tipo_movimiento'
    if col_monto: rename_map[col_monto] = 'monto'

    df_tx = df_tx.rename(columns=rename_map)

    # Limpieza de montos formato texto ($ o comas)
    if df_tx['monto'].dtype == 'object':
        df_tx['monto'] = (
            df_tx['monto']
            .astype(str)
            .str.replace('$', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        df_tx['monto'] = pd.to_numeric(df_tx['monto'], errors='coerce').fillna(0.0)

    # 4. Preparar periodos (YYYY-MM)
    df_tx['fecha_operacion'] = pd.to_datetime(df_tx['fecha_operacion'], errors='coerce')
    df_tx['periodo'] = df_tx['fecha_operacion'].dt.strftime('%Y-%m')

    # Excluir transferencias propias
    if 'categoria' in df_tx.columns:
        df_tx = df_tx[df_tx['categoria'].astype(str).str.upper() != 'TRANSFERENCIA_PROPIA']

    # 5. Agregaciones flexibles (Ingreso vs Gasto)
    tipo_series = df_tx['tipo_movimiento'].astype(str).str.upper()

    mask_ingreso = tipo_series.isin(['INGRESO', 'INGRESOS', 'INCOME'])
    ingresos = df_tx[mask_ingreso].groupby(['customer_id', 'periodo'])['monto'].sum().reset_index()
    ingresos.rename(columns={'monto': 'ingresos_totales'}, inplace=True)

    mask_gasto = tipo_series.isin(['EGRESO', 'EGRESOS', 'GASTO', 'GASTOS', 'EXPENSE'])
    gastos = df_tx[mask_gasto].groupby(['customer_id', 'periodo'])['monto'].sum().reset_index()
    gastos.rename(columns={'monto': 'gastos_totales'}, inplace=True)

    if 'es_fijo' in df_tx.columns:
        gastos_fijos = df_tx[mask_gasto & (df_tx['es_fijo'] == True)].groupby(['customer_id', 'periodo'])['monto'].sum().reset_index()
        gastos_fijos.rename(columns={'monto': 'gastos_fijos'}, inplace=True)

        gastos_var = df_tx[mask_gasto & (df_tx['es_fijo'] == False)].groupby(['customer_id', 'periodo'])['monto'].sum().reset_index()
        gastos_var.rename(columns={'monto': 'gastos_variables'}, inplace=True)
    else:
        gastos_fijos = pd.DataFrame(columns=['customer_id', 'periodo', 'gastos_fijos'])
        gastos_var = pd.DataFrame(columns=['customer_id', 'periodo', 'gastos_variables'])

    # 6. Agregación de Compromisos Fijos / Créditos (Deuda)
    col_cred_cliente = find_column(df_cred, ['customer_id', 'cliente_id', 'id_cliente']) if not df_cred.empty else None
    col_cred_monto = find_column(df_cred, ['monto_mensual', 'pago_mensual', 'monto', 'monto_cuota']) if not df_cred.empty else None

    if not df_cred.empty and col_cred_cliente and col_cred_monto:
        if df_cred[col_cred_monto].dtype == 'object':
            df_cred[col_cred_monto] = (
                df_cred[col_cred_monto]
                .astype(str)
                .str.replace('$', '', regex=False)
                .str.replace(',', '', regex=False)
                .str.strip()
            )
            df_cred[col_cred_monto] = pd.to_numeric(df_cred[col_cred_monto], errors='coerce').fillna(0.0)

        deuda = df_cred.groupby(col_cred_cliente)[col_cred_monto].sum().reset_index()
        deuda.rename(columns={col_cred_cliente: 'customer_id', col_cred_monto: 'pago_deuda_mensual'}, inplace=True)
    else:
        deuda = pd.DataFrame(columns=['customer_id', 'pago_deuda_mensual'])

    # 7. Consolidación de Tabla Gold
    base_keys = df_tx[['customer_id', 'periodo']].dropna().drop_duplicates()

    df_gold = base_keys.merge(ingresos, on=['customer_id', 'periodo'], how='left')
    df_gold = df_gold.merge(gastos, on=['customer_id', 'periodo'], how='left')
    df_gold = df_gold.merge(gastos_fijos, on=['customer_id', 'periodo'], how='left')
    df_gold = df_gold.merge(gastos_var, on=['customer_id', 'periodo'], how='left')
    df_gold = df_gold.merge(deuda, on='customer_id', how='left')

    fill_cols = ['ingresos_totales', 'gastos_totales', 'gastos_fijos', 'gastos_variables', 'pago_deuda_mensual']
    df_gold[fill_cols] = df_gold[fill_cols].fillna(0.0)

    # 8. KPIs Derivados
    df_gold['gastos_operativos'] = (df_gold['gastos_totales'] - df_gold['pago_deuda_mensual']).clip(lower=0.0)
    df_gold['flujo_neto'] = df_gold['ingresos_totales'] - df_gold['gastos_totales']

    df_gold['tasa_ahorro'] = (
        df_gold['flujo_neto']
        .div(df_gold['ingresos_totales'].replace(0, np.nan))
        .clip(lower=0)
        .fillna(0.0)
    )

    df_gold['ratio_fijo'] = (
        df_gold['gastos_fijos']
        .div(df_gold['gastos_totales'].replace(0, np.nan))
        .fillna(0.0)
    )

    df_gold['ratio_endeudamiento'] = (
        df_gold['pago_deuda_mensual']
        .div(df_gold['ingresos_totales'].replace(0, np.nan))
        .fillna(0.0)
    )

    # 9. Redondeo final
    cols_round = ['ingresos_totales', 'gastos_totales', 'gastos_operativos', 'gastos_fijos', 'gastos_variables', 'flujo_neto', 'pago_deuda_mensual']
    df_gold[cols_round] = df_gold[cols_round].round(2)

    cols_ratios = ['tasa_ahorro', 'ratio_fijo', 'ratio_endeudamiento']
    df_gold[cols_ratios] = df_gold[cols_ratios].round(4)

    # 10. Guardar Parquet final
    output_path = os.path.join(GOLD_DIR, "gold_cliente_mes.parquet")
    df_gold.to_parquet(output_path, index=False)

    print(f"✅ Tabla Gold generada exitosamente en: {output_path}")
    print(f"📊 Registros procesados: {len(df_gold)}")

    # Disparo automático a Feature Engineering
    print("🔄 Ejecutando Feature Engineering automático para ML...")
    build_feature_matrix()


if __name__ == "__main__":
    build_gold_layer()