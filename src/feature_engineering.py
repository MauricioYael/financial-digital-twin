import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GOLD_DIR = os.path.join(BASE_DIR, "data", "gold")
GOLD_PATH = os.path.join(GOLD_DIR, "gold_cliente_mes.parquet")
FEATURE_MATRIX_PATH = os.path.join(GOLD_DIR, "ml_feature_matrix.parquet")


def build_feature_matrix():
    print("🚀 Iniciando generación de la Matriz de Features para ML...")

    if not os.path.exists(GOLD_PATH):
        print(f"❌ Error: No se encontró la Capa Gold en {GOLD_PATH}")
        return None

    df_gold = pd.read_parquet(GOLD_PATH)

    if df_gold.empty:
        print("⚠️ La tabla Gold está vacía.")
        return None

    # Ordenar por cliente y periodo para cálculos secuenciales (Lags y Rolling)
    df = df_gold.sort_values(by=['customer_id', 'periodo']).copy()

    # 1. Deltas y Crecimiento Mes a Mes (MoM)
    df['flujo_neto_prev'] = df.groupby('customer_id')['flujo_neto'].shift(1)
    df['delta_flujo_neto_mom'] = (df['flujo_neto'] - df['flujo_neto_prev']).fillna(0.0)

    df['ingresos_prev'] = df.groupby('customer_id')['ingresos_totales'].shift(1)
    df['pct_cambio_ingresos_mom'] = (
        (df['ingresos_totales'] - df['ingresos_prev'])
        .div(df['ingresos_prev'].replace(0, np.nan))
        .fillna(0.0)
        .round(4)
    )

    df['gastos_op_prev'] = df.groupby('customer_id')['gastos_operativos'].shift(1)
    df['pct_cambio_gastos_op_mom'] = (
        (df['gastos_operativos'] - df['gastos_op_prev'])
        .div(df['gastos_op_prev'].replace(0, np.nan))
        .fillna(0.0)
        .round(4)
    )

    # 2. Promedios Móviles a 3 Meses (Rolling 3M)
    df['promedio_movil_ingresos_3m'] = (
        df.groupby('customer_id')['ingresos_totales']
        .transform(lambda x: x.rolling(window=3, min_periods=1).mean())
        .round(2)
    )

    df['promedio_movil_gastos_3m'] = (
        df.groupby('customer_id')['gastos_totales']
        .transform(lambda x: x.rolling(window=3, min_periods=1).mean())
        .round(2)
    )

    # 3. Ratio de Cobertura de Deuda (Capacidad de pago operativa)
    df['ratio_cobertura_deuda'] = (
        df['ingresos_totales']
        .sub(df['gastos_operativos'])
        .div(df['pagos_deuda'].replace(0, np.nan))
        .fillna(99.0)  # 99 indica sin deuda comprometida
        .clip(upper=99.0)
        .round(2)
    )

    # 4. Score Sintético de Salud Financiera (0 a 100)
    # Ponderación: 40% Tasa Ahorro, 40% Control de Endeudamiento, 20% Flujo Positivo
    score_ahorro = df['tasa_ahorro'].clip(0, 0.5) / 0.5 * 40
    score_deuda = (1 - df['ratio_endeudamiento'].clip(0, 0.5) / 0.5) * 40
    score_flujo = np.where(df['flujo_neto'] > 0, 20, 0)

    df['score_salud_financiera'] = (score_ahorro + score_deuda + score_flujo).round(1)

    # Limpieza de columnas temporales
    cols_drop = ['flujo_neto_prev', 'ingresos_prev', 'gastos_op_prev']
    df = df.drop(columns=[c for c in cols_drop if c in df.columns])

    # Guardar Feature Matrix en formato Parquet
    df.to_parquet(FEATURE_MATRIX_PATH, index=False)
    print(f"✅ Matriz de Features generada exitosamente en: {FEATURE_MATRIX_PATH}")
    print(f"📊 Granularidad: {len(df)} registros | {len(df.columns)} características (features)")

    return df


if __name__ == "__main__":
    build_feature_matrix()