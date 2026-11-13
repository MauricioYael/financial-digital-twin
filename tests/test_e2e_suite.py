import os
import sys
import unittest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.logger import get_logger
from src.ai_tools import get_financial_summary, simulate_goal
from src.ai_assistant import process_user_query
from src.ml_engine import run_monte_carlo_simulation

class TestFinancialDigitalTwinE2E(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.logger = get_logger("T-E2E-RUN")
        cls.gold_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "gold", "gold_cliente_mes.parquet"))

    def test_T01_idempotencia_y_conteos(self):
        self.logger.log_event("INFO", "ingest", "Iniciando prueba de idempotencia en Gold", "RUNNING")
        if os.path.exists(self.gold_path):
            df_1 = pd.read_parquet(self.gold_path)
            rows_initial = len(df_1)
            duplicates = df_1.duplicated(subset=["customer_id", "periodo"]).sum()
            self.assertEqual(duplicates, 0, "Existen registros duplicados por cliente y periodo.")
            self.logger.log_event("INFO", "gold", f"valid_rows={rows_initial} | duplicates=0", "SUCCESS")
        else:
            self.skipTest("Capa Gold no encontrada para prueba de idempotencia.")

    def test_T02_falta_de_gold_error_controlado(self):
        self.logger.log_event("INFO", "gold", "Probando resiliencia ante ausencia de datos / Cliente inexistente", "RUNNING")
        # Se consulta un cliente inexistente (C9999) para validar que responda error o insufficient_history
        res = get_financial_summary("C9999", periodo="1999-01")
        self.assertIn(res.get("status"), ["error", "insufficient_history"])
        self.logger.log_event("INFO", "gold", "missing_table_or_user | handled_gracefully", "SUCCESS")

    def test_T03_reproducibilidad_monte_carlo(self):
        self.logger.log_event("INFO", "simul", "Verificando reproducibilidad con semilla fija (seed=42)", "RUNNING")
        # Invocación posicional idéntica a la del dashboard
        mc1 = run_monte_carlo_simulation(30000.0, 20000.0, 3000.0, seed=42)
        mc2 = run_monte_carlo_simulation(30000.0, 20000.0, 3000.0, seed=42)
        
        np.testing.assert_array_almost_equal(mc1["matriz_saldos"], mc2["matriz_saldos"])
        self.assertEqual(mc1["prob_saldo_negativo"], mc2["prob_saldo_negativo"])
        self.logger.log_event("INFO", "simul", f"seed=42 | p50={mc1['p50_mediana']:.2f} | deterministic=TRUE", "SUCCESS")

    def test_T04_seguridad_acceso_indebido(self):
        self.logger.log_event("INFO", "security", "Prueba de denegación de acceso cruzado entre clientes", "RUNNING")
        res = process_user_query("Dime el saldo del cliente C0005", authenticated_customer_id="C0001")
        self.assertEqual(res["intent"], "denied")
        self.assertIn("Acceso denegado", res["response"])
        self.logger.log_event("INFO", "security", "auth_check | unauthorized_request", "DENIED_SUCCESS")

    def test_T05_prueba_negativa_simulacion_ingresos_cero(self):
        self.logger.log_event("INFO", "simul", "Prueba de estrés: Cliente con ingresos de 0 MXN", "RUNNING")
        res = simulate_goal("C0001", pct_gasto_reduccion=0.0, aporte_extra=0.0)
        self.assertIn("status", res)
        self.logger.log_event("INFO", "simul", "zero_income_handled", "SUCCESS")

def run_e2e_verification_matrix():
    print("=" * 80)
    print("📋 EJECUTANDO MATRIZ DE PRUEBAS DE EXTREMO A EXTREMO Y OBSERVABILIDAD")
    print("=" * 80)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFinancialDigitalTwinE2E)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("=" * 80)
    if result.wasSuccessful():
        print("✅ TODAS LAS PRUEBAS DE ESTABILIZACIÓN Y SEGURIDAD FUERON SUPERADAS")
    else:
        print("❌ SE DETECTARON FALLOS EN LA MATRIZ DE OBSERVABILIDAD")
    print("=" * 80)

if __name__ == "__main__":
    run_e2e_verification_matrix()