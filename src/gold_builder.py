import os
import pandas as pd
import numpy as np

# Definición de rutas alineada a la estructura del proyecto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SILVER_DIR = os.path.join(BASE_DIR, "data", "silver")
GOLD_DIR = os.path.join(BASE_DIR, "data", "gold")

os.makedirs(GOLD_DIR, exist_ok=True)


def find_column(df, candidates):
    """Busca dinámicamente el nombre de una columna según posibles candidatos."""
    for col in candidates:
        if col in df.columns:
            return col
    return None


def build_gold_layer():
    print("🚀 Iniciando generación de la Capa Gold (gold_cliente_mes)...")

    # 1. Cargar fuentes Silver
    tx_path = os.path.join(SILVER_DIR, "fct_transacciones.parquet")
    cred_path = os.path.join(SILVER_DIR, "dim_compromisos_fijos.parquet")
    cli_path = os.path.join(SILVER_DIR, "dim_clientes.parquet")

    if not os.path.exists(tx_path):
        print(f"❌ Error: No se encontró el archivo de hechos en {tx_path}")
        return

    df_tx = pd.read_parquet(tx_path)
    df_cred = (
        pd.read_parquet(cred_path)
        if os.path.exists(cred_path)
        else pd.DataFrame()
    )
    df_cli = (
        pd.read_parquet(cli_path)
        if os.path.exists(cli_path)
        else pd.DataFrame()
    )

    # 2. Identificar nombres de columnas clave en fct_transacciones
    col_fecha = find_column(
        df_tx,
        [
            'fecha_operacion',
            'fecha',
            'fecha_transaccion',
            'date',
            'fecha_tx',
            'timestamp'
        ]
    )

    col_cliente = find_column(
        df_tx,
        [
            'customer_id',
            'cliente_id',
            'id_cliente',
            'user_id'
        ]
    )

    col_tipo = find_column(
        df_tx,
        [
            'tipo_movimiento',
            'tipo',
            'tipo_transaccion',
            'type'
        ]
    )

    col_monto = find_column(
        df_tx,
        [
            'monto',
            'monto_total',
            'amount',
            'valor'
        ]
    )

    if not col_fecha:
        print(
            "❌ Error: No se encontró columna de fecha en "
            f"fct_transacciones. Columnas presentes: {list(df_tx.columns)}"
        )
        return

    if not col_cliente:
        print(
            "❌ Error: No se encontró columna de cliente. "
            f"Columnas presentes: {list(df_tx.columns)}"
        )
        return

    # 3. Normalizar nombres de columnas a la convención estándar
    rename_map = {
        col_fecha: 'fecha_operacion',
        col_cliente: 'customer_id'
    }

    if col_tipo:
        rename_map[col_tipo] = 'tipo_movimiento'

    if col_monto:
        rename_map[col_monto] = 'monto'

    df_tx = df_tx.rename(columns=rename_map)

    # 4. Preparar periodos (Mes Calendario: YYYY-MM)
    df_tx['fecha_operacion'] = pd.to_datetime(
        df_tx['fecha_operacion']
    )

    df_tx['periodo'] = df_tx['fecha_operacion'].dt.strftime('%Y-%m')

    # --- REGLA DE NEGOCIO: LIMPIEZA DE FLUJOS REPETIDOS ---
    if 'categoria' in df_tx.columns:
        df_tx = df_tx[
            df_tx['categoria'] != 'TRANSFERENCIA_PROPIA'
        ]

    # 5. Calcular Agregaciones sobre fct_transacciones

    # Ingresos Totales
    ingresos = (
        df_tx[df_tx['tipo_movimiento'] == 'INGRESO']
        .groupby(['customer_id', 'periodo'])['monto']
        .sum()
        .reset_index()
    )

    ingresos.rename(
        columns={'monto': 'ingresos_totales'},
        inplace=True
    )

    # Gastos Totales
    gastos = (
        df_tx[df_tx['tipo_movimiento'] == 'EGRESO']
        .groupby(['customer_id', 'periodo'])['monto']
        .sum()
        .reset_index()
    )

    gastos.rename(
        columns={'monto': 'gastos_totales'},
        inplace=True
    )

    # Gastos Fijos vs Variables
    if 'es_fijo' in df_tx.columns:

        gastos_fijos = (
            df_tx[
                (df_tx['tipo_movimiento'] == 'EGRESO') &
                (df_tx['es_fijo'] == True)
            ]
            .groupby(['customer_id', 'periodo'])['monto']
            .sum()
            .reset_index()
        )

        gastos_fijos.rename(
            columns={'monto': 'gastos_fijos'},
            inplace=True
        )

        gastos_var = (
            df_tx[
                (df_tx['tipo_movimiento'] == 'EGRESO') &
                (df_tx['es_fijo'] == False)
            ]
            .groupby(['customer_id', 'periodo'])['monto']
            .sum()
            .reset_index()
        )

        gastos_var.rename(
            columns={'monto': 'gastos_variables'},
            inplace=True
        )

    else:

        gastos_fijos = pd.DataFrame(
            columns=[
                'customer_id',
                'periodo',
                'gastos_fijos'
            ]
        )

        gastos_var = pd.DataFrame(
            columns=[
                'customer_id',
                'periodo',
                'gastos_variables'
            ]
        )

    # 6. Agregación de Compromisos Fijos / Créditos
    col_cred_cliente = (
        find_column(
            df_cred,
            [
                'customer_id',
                'cliente_id',
                'id_cliente'
            ]
        )
        if not df_cred.empty
        else None
    )

    col_cred_monto = (
        find_column(
            df_cred,
            [
                'pago_mensual',
                'monto',
                'monto_cuota'
            ]
        )
        if not df_cred.empty
        else None
    )

    if (
        not df_cred.empty
        and col_cred_cliente
        and col_cred_monto
    ):

        deuda = (
            df_cred
            .groupby(col_cred_cliente)[col_cred_monto]
            .sum()
            .reset_index()
        )

        deuda.rename(
            columns={
                col_cred_cliente: 'customer_id',
                col_cred_monto: 'pago_deuda_mensual'
            },
            inplace=True
        )

    else:

        deuda = pd.DataFrame(
            columns=[
                'customer_id',
                'pago_deuda_mensual'
            ]
        )

    # 7. Consolidación de Tabla Gold
    base_keys = (
        df_tx[
            ['customer_id', 'periodo']
        ]
        .drop_duplicates()
    )

    df_gold = base_keys.merge(
        ingresos,
        on=['customer_id', 'periodo'],
        how='left'
    )

    df_gold = df_gold.merge(
        gastos,
        on=['customer_id', 'periodo'],
        how='left'
    )

    df_gold = df_gold.merge(
        gastos_fijos,
        on=['customer_id', 'periodo'],
        how='left'
    )

    df_gold = df_gold.merge(
        gastos_var,
        on=['customer_id', 'periodo'],
        how='left'
    )

    df_gold = df_gold.merge(
        deuda,
        on='customer_id',
        how='left'
    )

    # Rellenar ceros en montos no registrados
    fill_cols = [
        'ingresos_totales',
        'gastos_totales',
        'gastos_fijos',
        'gastos_variables',
        'pago_deuda_mensual'
    ]

    df_gold[fill_cols] = (
        df_gold[fill_cols]
        .fillna(0.0)
    )

    # 8. Cálculo de KPIs Derivados

    # Flujo neto
    df_gold['flujo_neto'] = (
        df_gold['ingresos_totales']
        - df_gold['gastos_totales']
    )

    # ---------------------------------------------------------
    # TASA DE AHORRO
    # Evitamos división entre cero reemplazando 0 por NaN.
    # Posteriormente convertimos los NaN nuevamente a 0.0.
    # ---------------------------------------------------------
    df_gold['tasa_ahorro'] = (
        df_gold['flujo_neto']
        .div(
            df_gold['ingresos_totales']
            .replace(0, np.nan)
        )
        .clip(lower=0)
        .fillna(0.0)
    )

    # ---------------------------------------------------------
    # RATIO DE GASTOS FIJOS
    # ---------------------------------------------------------
    df_gold['ratio_fijo'] = (
        df_gold['gastos_fijos']
        .div(
            df_gold['gastos_totales']
            .replace(0, np.nan)
        )
        .fillna(0.0)
    )

    # ---------------------------------------------------------
    # RATIO DE ENDEUDAMIENTO
    # CORRECCIÓN PRINCIPAL DEL ERROR
    # ---------------------------------------------------------
    df_gold['ratio_endeudamiento'] = (
        df_gold['pago_deuda_mensual']
        .div(
            df_gold['ingresos_totales']
            .replace(0, np.nan)
        )
        .fillna(0.0)
    )

    # 9. Redondeo final
    cols_round = [
        'ingresos_totales',
        'gastos_totales',
        'gastos_fijos',
        'gastos_variables',
        'flujo_neto',
        'pago_deuda_mensual'
    ]

    df_gold[cols_round] = (
        df_gold[cols_round]
        .round(2)
    )

    cols_ratios = [
        'tasa_ahorro',
        'ratio_fijo',
        'ratio_endeudamiento'
    ]

    df_gold[cols_ratios] = (
        df_gold[cols_ratios]
        .round(4)
    )

    # 10. Guardar Parquet final
    output_path = os.path.join(
        GOLD_DIR,
        "gold_cliente_mes.parquet"
    )

    df_gold.to_parquet(
        output_path,
        index=False
    )

    print(
        f"✅ Tabla Gold generada exitosamente en: "
        f"{output_path}"
    )

    print(
        f"📊 Registros procesados: {len(df_gold)}"
    )


if __name__ == "__main__":
    build_gold_layer()