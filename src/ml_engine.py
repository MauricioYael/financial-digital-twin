import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

def prepare_features_and_target(df_gold: pd.DataFrame):
    """
    Construye la matriz de características (Features) y la variable objetivo (Target).
    Garantiza la separación temporal sin fugas del futuro (Look-ahead bias).
    """
    df = df_gold.sort_values(by=["customer_id", "periodo"]).copy()
    
    # Asegurar orden chronológico por cliente
    df['next_cashflow'] = df.groupby('customer_id')['flujo_neto'].shift(-1)
    
    # Feature Engineering histórico (Últimos 3 meses)
    df['avg_income_3m'] = df.groupby('customer_id')['ingresos_totales'].transform(lambda x: x.rolling(3, min_periods=1).mean())
    df['avg_expenses_3m'] = df.groupby('customer_id')['gastos_totales'].transform(lambda x: x.rolling(3, min_periods=1).mean())
    df['expense_volatility_3m'] = df.groupby('customer_id')['gastos_totales'].transform(lambda x: x.rolling(3, min_periods=1).std().fillna(0))
    
    df['savings_rate_3m'] = np.where(df['avg_income_3m'] > 0, (df['avg_income_3m'] - df['avg_expenses_3m']) / df['avg_income_3m'], 0)
    
    col_deuda = 'pagos_deuda' if 'pagos_deuda' in df.columns else ('pago_deuda_mensual' if 'pago_deuda_mensual' in df.columns else None)
    if col_deuda:
        df['debt_to_income_ratio'] = np.where(df['ingresos_totales'] > 0, df[col_deuda] / df['ingresos_totales'], 0)
    else:
        df['debt_to_income_ratio'] = 0.0

    # Eliminar filas sin target (el último mes conocido no tiene 'siguiente mes')
    df_dataset = df.dropna(subset=['next_cashflow']).copy()
    
    feature_cols = ['avg_income_3m', 'avg_expenses_3m', 'expense_volatility_3m', 'savings_rate_3m', 'debt_to_income_ratio']
    X = df_dataset[feature_cols]
    y = df_dataset['next_cashflow']
    
    return df_dataset, X, y, feature_cols


def train_and_evaluate_models(df_gold: pd.DataFrame, error_margin_mxn: float = 1000.0):
    """
    Entrena y compara: Baseline, Regresión Lineal, Random Forest y Red Neuronal de 4 Capas.
    Calcula MAE, RMSE, Bias y Probabilidad de Acierto.
    """
    df_dataset, X, y, feature_cols = prepare_features_and_target(df_gold)
    
    if len(df_dataset) < 5:
        return None, "Datos insuficientes para entrenamiento."

    # Split Temporal (Garantizando no mezclar pasado y futuro)
    periodos_unicos = sorted(df_dataset['periodo'].unique())
    n_periodos = len(periodos_unicos)
    
    if n_periodos >= 3:
        train_cutoff = periodos_unicos[int(n_periodos * 0.7)]
        train_mask = df_dataset['periodo'] <= train_cutoff
        test_mask = df_dataset['periodo'] > train_cutoff
    else:
        # Fallback si hay pocos periodos
        split_idx = int(len(df_dataset) * 0.7)
        train_mask = df_dataset.index < df_dataset.index[split_idx]
        test_mask = ~train_mask

    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    results = {}

    # 1. Baseline: Promedio móvil de flujo neto de los últimos 3 meses
    baseline_pred = df_dataset.loc[test_mask, 'avg_income_3m'] - df_dataset.loc[test_mask, 'avg_expenses_3m']
    results['Línea Base (Promedio 3M)'] = calculate_metrics(y_test, baseline_pred, error_margin_mxn)

    # 2. Regresión Lineal
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    results['Regresión Lineal'] = calculate_metrics(y_test, lr.predict(X_test), error_margin_mxn)

    # 3. Random Forest Regressor
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    results['Random Forest'] = calculate_metrics(y_test, rf.predict(X_test), error_margin_mxn)

    # 4. Red Neuronal Multicapa (MLP Regressor - 4 Capas: Entrada -> 64 -> 32 -> 16 -> Salida)
    mlp = MLPRegressor(
        hidden_layer_sizes=(64, 32, 16),
        activation='relu',
        max_iter=1000,
        random_state=42,
        early_stopping=True
    )
    mlp.fit(X_train, y_train)
    results['Red Neuronal (4 Capas)'] = calculate_metrics(y_test, mlp.predict(X_test), error_margin_mxn)

    return pd.DataFrame(results).T, mlp


def calculate_metrics(y_true, y_pred, error_margin: float):
    """Calcula MAE, RMSE, Bias y % de acierto dentro del margen de error."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    bias = np.mean(y_pred - y_true)  # Positivo = Sobreestimación, Negativo = Subestimación
    
    # Probabilidad de acierto (% de casos dentro del margen ±error_margin MXN)
    abs_errors = np.abs(y_pred - y_true)
    accuracy_rate = (abs_errors <= error_margin).mean() * 100.0

    return {
        "MAE (MXN)": round(mae, 2),
        "RMSE (MXN)": round(rmse, 2),
        "Bias (MXN)": round(bias, 2),
        f"Prob. Acierto (±${error_margin:,.0f})": f"{accuracy_rate:.1f}%"
    }


def run_what_if_simulation(ingreso_actual: float, gasto_actual: float, pct_gasto_var: float = 20.0, pct_ingreso_var: float = -15.0):
    """
    Simulación determinista What-If.
    """
    flujo_base = ingreso_actual - gasto_actual
    
    nuevo_gasto = gasto_actual * (1 + pct_gasto_var / 100.0)
    nuevo_ingreso = ingreso_actual * (1 + pct_ingreso_var / 100.0)
    flujo_simulado = nuevo_ingreso - nuevo_gasto
    
    diferencia = flujo_simulado - flujo_base
    
    return {
        "flujo_base": flujo_base,
        "nuevo_ingreso": nuevo_ingreso,
        "nuevo_gasto": nuevo_gasto,
        "flujo_simulado": flujo_simulado,
        "diferencia": diferencia
    }


def run_monte_carlo_simulation(
    ingreso_medio: float,
    gasto_medio: float,
    gasto_std: float,
    saldo_inicial: float = 30000.0,
    n_trayectorias: int = 1000,
    meses: int = 6,
    seed: int = 42
):
    """
    Simulación Monte Carlo (1,000 trayectorias a 6 meses con semilla fija).
    Calcula percentiles P10, Mediana (P50), P90 y riesgo de saldo negativo.
    """
    np.random.seed(seed)
    
    # Arreglo para almacenar la evolución del saldo [n_trayectorias, meses + 1]
    saldos = np.zeros((n_trayectorias, meses + 1))
    saldos[:, 0] = saldo_inicial

    for t in range(1, meses + 1):
        # Generar variaciones normales alrededor del ingreso y gasto
        ingresos_sim = np.random.normal(ingreso_medio, ingreso_medio * 0.05, n_trayectorias)
        gastos_sim = np.random.normal(gasto_medio, max(gasto_std, gasto_medio * 0.10), n_trayectorias)
        
        flujo_sim = ingresos_sim - gastos_sim
        saldos[:, t] = saldos[:, t - 1] + flujo_sim

    # Análisis estadístico al final de los 6 meses
    saldos_finales = saldos[:, -1]
    
    p10 = np.percentile(saldos_finales, 10)
    p50 = np.percentile(saldos_finales, 50)
    p90 = np.percentile(saldos_finales, 90)

    # Probabilidad de saldo negativo en al menos un mes durante la trayectoria
    min_saldos = np.min(saldos, axis=1)
    prob_saldo_negativo = (min_saldos < 0).mean() * 100.0

    return {
        "matriz_saldos": saldos,
        "p10": p10,
        "p50_mediana": p50,
        "p90": p90,
        "prob_saldo_negativo": prob_saldo_negativo
    }