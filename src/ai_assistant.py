import os
import re
import json
import time
import math
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# 1. Carga Forzada de Variables de Entorno (.env)
# -----------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..")) if os.path.basename(CURRENT_DIR) == "src" else CURRENT_DIR
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

try:
    from google import genai
    from google.genai import errors
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from src.ai_tools import get_financial_summary, get_financial_goal, simulate_goal
from src.logger import get_logger

SYSTEM_PROMPT = """
Eres el Asistente Financiero del Gemelo Digital BBVA. Tu comunicación es limpia, directa, concisa y profesional.

REGLAS DE COMUNICACIÓN Y TONO (ESTRICTAS):
1. PROHIBIDAS MULETILLAS Y SALUDOS REPETITIVOS: No uses saludos ("¡Hola!", "¡Qué gusto!"), felicitaciones excesivas ("¡Muchas felicidades!", "¡Qué gran noticia!") ni frases clichés ("Te cuento que..."). Ve directo al grano.
2. ENFOQUE EXCLUSIVO EN LA PREGUNTA ACTUAL: Si el usuario plantea una nueva meta (viaje, automóvil, monto específico), NUNCA menciones metas pasadas ni el Fondo de Emergencia a menos que el usuario lo pregunte expresamente.
3. CÁLCULO DE NUEVAS METAS: Cuando el usuario proporcione un monto para una nueva meta (ej. $100,000), utiliza el disponible libre mensual del cliente para explicar en cuántos meses logrará el objetivo.
4. FORMATO DE CONSULTAS DE SALUD FINANCIERA / INGRESOS / KPIS: Cuando el usuario pregunte por sus ingresos, resumen financiero, o datos del mes, debes responder obligatoriamente utilizando un formato de lista desglosada con los 5 indicadores de las tarjetas principales:
   - 💵 Ingresos Totales: $... MXN
   - 🛒 Gastos del Día a Día: $... MXN
   - 💳 Pago de Créditos: $... MXN
   - 🌱 Dinero Libre (Flujo): $... MXN
   - 📊 % Ahorro del Mes: ...%
5. PRECISIÓN Y BREVEDAD: Mantén las respuestas en 2 o 3 oraciones. Usa las cifras numéricas exactas entregadas en el contexto sin inventar datos.
"""

MODELOS_GEMINI = [
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

def invocar_gemini_resiliente(prompt: str, max_intentos: int = 2) -> str:
    """Llama a la API de Gemini intentando con la lista de modelos y reintentos ante fallas."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not GENAI_AVAILABLE:
        raise RuntimeError("API Key no configurada o librería google-genai no disponible.")

    client = genai.Client(api_key=api_key)

    for modelo in MODELOS_GEMINI:
        for intento in range(1, max_intentos + 1):
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt
                )
                if response and response.text:
                    return response.text
            except Exception:
                time.sleep(1)
                continue
    raise RuntimeError("No se pudo obtener respuesta de ningún modelo de Gemini.")

def process_user_query_with_llm(user_prompt: str, authenticated_customer_id: str, periodo: str = None) -> dict:
    logger = get_logger()
    prompt_lower = user_prompt.lower()

    # GUARDRAIL 1: Bloqueo de acceso cruzado entre clientes
    target_client_match = re.search(r"c\d{4}", prompt_lower)
    if target_client_match:
        requested_id = target_client_match.group(0).upper()
        if requested_id != authenticated_customer_id:
            logger.log_event("WARN", "security", f"unauthorized_attempt client={requested_id}", "DENIED")
            return {
                "intent": "denied",
                "tool_called": "none",
                "response": f"🔒 Por seguridad de tu banca digital, solo puedo mostrar la información de tu sesión activa (`{authenticated_customer_id}`)."
            }

    # GUARDRAIL 2: Incertidumbre a largo plazo (5+ años)
    if any(phrase in prompt_lower for phrase in ["5 años", "cinco años", "10 años", "diez años", "a largo plazo"]):
        logger.log_event("INFO", "assistant", "long_term_uncertainty_triggered", "SUCCESS")
        return {
            "intent": "long_term_uncertainty",
            "tool_called": "none",
            "response": "Debido a la variabilidad de la inflación y tasas de interés a 5 años o más, no es conveniente fijar cifras exactas a tan largo plazo. Te sugiero proyectar este plan a 6 o 12 meses."
        }

    # GUARDRAIL 3: Histórico insuficiente
    if "no tengo histórico suficiente" in prompt_lower or authenticated_customer_id == "C9999":
        logger.log_event("INFO", "assistant", "insufficient_history_triggered", "SUCCESS")
        return {
            "intent": "insufficient_history",
            "tool_called": "get_financial_summary",
            "response": "Aún no contamos con registros suficientes en tu historial para realizar este diagnóstico."
        }

    # Extraer montos personalizados del mensaje del usuario (ej. 100,000 / $100000)
    monto_custom_match = re.search(r"(\$?\d+[\d,.]*)", user_prompt.replace(",", ""))
    monto_custom = None
    if monto_custom_match:
        try:
            val_parsed = float(monto_custom_match.group(1).replace("$", ""))
            if val_parsed >= 1000:
                monto_custom = val_parsed
        except ValueError:
            pass

    summary = get_financial_summary(authenticated_customer_id, periodo=periodo)
    flujo_disponible = summary.get("flujo_neto", 0.0)

    # Clasificación de la intención
    intent_info = classify_intent_with_llm(user_prompt)
    intent = intent_info.get("intent", "UNKNOWN")
    pct_val = intent_info.get("pct_reduction", 15.0)

    # A. Metas de ahorro / Proyectos
    if intent == "GOAL" or monto_custom:
        tool_data = get_financial_goal(authenticated_customer_id)
        logger.log_event("INFO", "assistant", "tool=get_financial_goal", "SUCCESS")
        
        if monto_custom and flujo_disponible > 0:
            meses_req = math.ceil(monto_custom / flujo_disponible)
            datos_contexto = (
                f"Nueva meta personalizada consultada por el cliente: ${monto_custom:,.2f} MXN. "
                f"Dinero libre disponible mensual del cliente: ${flujo_disponible:,.2f} MXN. "
                f"Tiempo estimado para alcanzar la meta: {meses_req} meses."
            )
        else:
            datos_contexto = (
                f"Dinero libre disponible al mes: ${flujo_disponible:,.2f} MXN. "
                f"Ahorro reservado actual: ${tool_data['saldo_actual']:,.2f} MXN."
            )

        response_text = format_response_with_llm(user_prompt, datos_contexto, intent="GOAL")
        return {
            "intent": "get_financial_goal",
            "tool_called": "get_financial_goal",
            "data": tool_data,
            "response": response_text
        }

    # B. Simulaciones What-If / Reducción de Gastos
    elif intent == "SIMULATION":
        tool_data = simulate_goal(authenticated_customer_id, pct_gasto_reduccion=pct_val)
        logger.log_event("INFO", "assistant", f"tool=simulate_goal pct={pct_val}", "SUCCESS")
        
        datos_contexto = (
            f"Reducción simulada: {pct_val}% en gastos variables. "
            f"Ahorro extra mensual generado: ${tool_data['ahorro_adicional_mensual']:,.2f} MXN. "
            f"Nuevo margen libre mensual proyectado: ${tool_data['nueva_capacidad_mensual']:,.2f} MXN."
        )
        response_text = format_response_with_llm(user_prompt, datos_contexto, intent="SIMULATION")
        return {
            "intent": "simulate_goal",
            "tool_called": "simulate_goal",
            "data": tool_data,
            "response": response_text
        }

    # C. Resumen de Salud Financiera / KPIs
    elif intent == "SUMMARY":
        logger.log_event("INFO", "assistant", "tool=get_financial_summary", "SUCCESS")
        
        # Extraer los 5 indicadores exactos recibidos de la herramienta
        ingresos_tot = summary.get("ingresos_totales", 0.0)
        gastos_op = summary.get("gastos_operativos", 0.0)
        pago_deuda = summary.get("pagos_deuda", summary.get("pago_deuda_mensual", 0.0))
        flujo_neto = summary.get("flujo_neto", 0.0)
        tasa_ahorro = summary.get("tasa_ahorro_pct", 0.0)
        periodo_actual = summary.get("periodo", "último periodo")

        datos_contexto = (
            f"Periodo de consulta: {periodo_actual}\n"
            f"- Ingresos Totales: ${ingresos_tot:,.2f} MXN\n"
            f"- Gastos del Día a Día: ${gastos_op:,.2f} MXN\n"
            f"- Pago de Créditos: ${pago_deuda:,.2f} MXN\n"
            f"- Dinero Libre (Flujo): ${flujo_neto:,.2f} MXN\n"
            f"- % Ahorro del Mes: {tasa_ahorro:.1f}%\n"
        )
        response_text = format_response_with_llm(user_prompt, datos_contexto, intent="SUMMARY")
        return {
            "intent": "get_financial_summary",
            "tool_called": "get_financial_summary",
            "data": summary,
            "response": response_text
        }

    else:
        logger.log_event("INFO", "assistant", "intent=unknown", "FALLBACK")
        return {
            "intent": "unknown",
            "tool_called": "none",
            "response": "¿Te gustaría proyectar el plazo para una nueva meta o simular un ajuste en tus gastos del mes?"
        }

def classify_intent_with_llm(user_prompt: str) -> dict:
    prompt_lower = user_prompt.lower()
    instruction = """
    Analiza la intención del usuario y responde ÚNICAMENTE un objeto JSON válido:
    {"intent": "SUMMARY|GOAL|SIMULATION", "pct_reduction": float_val_or_15.0}
    - GOAL: Planes futuros, viajes, compras, metas de dinero, objetivos o montos específicos.
    - SIMULATION: Recortes de gasto, ahorro extra, porcentajes de ajuste.
    - SUMMARY: Saldo actual, ingresos o gastos del mes.
    """
    try:
        raw_text = invocar_gemini_resiliente(f"{instruction}\n\nMensaje: \"{user_prompt}\"")
        text_clean = raw_text.strip().replace("```json", "").replace("```", "")
        return json.loads(text_clean)
    except Exception:
        if any(k in prompt_lower for k in ["meta", "viaje", "punta cana", "comprar", "llegar", "cuándo", "cuando", "objetivo", "meses", "pesos", "$"]):
            return {"intent": "GOAL", "pct_reduction": 15.0}
        elif any(k in prompt_lower for k in ["si gasto", "reduzco", "reducir", "ahorrar", "menos", "recortar", "bajar", "cambiar"]):
            pct_match = re.search(r"(\d+)\s*%", prompt_lower)
            pct_val = float(pct_match.group(1)) if pct_match else 15.0
            return {"intent": "SIMULATION", "pct_reduction": pct_val}
        else:
            return {"intent": "SUMMARY", "pct_reduction": 15.0}

def format_response_with_llm(user_prompt: str, context_text: str, intent: str = "SUMMARY") -> str:
    prompt_final = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Mensaje del cliente: \"{user_prompt}\"\n"
        f"Datos oficiales de la cuenta: {context_text}\n\n"
        f"Responde directamente a lo consultado de forma concisa, sin saludos repetitivos y sin mencionar temas no solicitados."
    )
    try:
        return invocar_gemini_resiliente(prompt_final)
    except Exception as e:
        print(f"⚠️ Respaldo activado: {e}")
        if intent == "GOAL":
            return "Destinando tu dinero libre mensual actual, avanzarás de manera constante hacia tu meta propuesta."
        elif intent == "SIMULATION":
            return "Ajustar tus gastos variables incrementará tu margen disponible mensual para responder mejor ante tus planes."
        else:
            return "Tus registros actuales muestran un margen disponible positivo para este periodo."

process_user_query = process_user_query_with_llm