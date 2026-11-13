import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai_assistant import process_user_query

def run_test_matrix():
    test_cases = [
        {
            "id": 1,
            "prompt": "¿Cuánto ahorré en septiembre?",
            "auth_client": "C0001",
            "expected_intent": "get_financial_summary",
            "expected_tool": "get_financial_summary"
        },
        {
            "id": 2,
            "prompt": "¿Cuándo llego a mi meta?",
            "auth_client": "C0001",
            "expected_intent": "get_financial_goal",
            "expected_tool": "get_financial_goal"
        },
        {
            "id": 3,
            "prompt": "¿Y si gasto 10 % menos?",
            "auth_client": "C0001",
            "expected_intent": "simulate_goal",
            "expected_tool": "simulate_goal"
        },
        {
            "id": 4,
            "prompt": "Dime el saldo de otro cliente C0005",
            "auth_client": "C0001",
            "expected_intent": "denied",
            "expected_tool": "none"
        },
        {
            "id": 5,
            "prompt": "¿Qué pasará exactamente en 5 años?",
            "auth_client": "C0001",
            "expected_intent": "long_term_uncertainty",
            "expected_tool": "none"
        },
        {
            "id": 6,
            "prompt": "No tengo histórico suficiente",
            "auth_client": "C9999",
            "expected_intent": "insufficient_history",
            "expected_tool": "get_financial_summary"
        }
    ]

    print("=" * 75)
    print("🧪 MATRIZ DE PRUEBAS OBLIGATORIAS — ASISTENTE IA (SESIÓN 20)")
    print("=" * 75)

    passed = 0
    for test in test_cases:
        res = process_user_query(test["prompt"], test["auth_client"])
        status = "✅ PASS" if res["intent"] == test["expected_intent"] else "❌ FAIL"
        if status == "✅ PASS":
            passed += 1
        
        print(f"Prueba {test['id']}: [{status}]")
        print(f"  • Prompt: '{test['prompt']}'")
        print(f"  • Intención Registrada: {res['intent']} (Esperada: {test['expected_intent']})")
        print(f"  • Herramienta Invocada: {res['tool_called']}")
        print(f"  • Respuesta Generada: {res['response'][:110]}...")
        print("-" * 75)

    print(f"Resultado final: {passed}/{len(test_cases)} casos superados exitosamente.")
    print("=" * 75)

if __name__ == "__main__":
    run_test_matrix()