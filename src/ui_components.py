import os
import base64
import streamlit as st
from src.ai_assistant import process_user_query

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..")) if os.path.basename(CURRENT_DIR) == "src" else CURRENT_DIR
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")

def get_base64_image(prefix: str) -> str:
    """Busca cualquier archivo en assets/ que comience con 'prefix' (ej. logo o logo2)."""
    if not os.path.exists(ASSETS_DIR):
        return ""

    for file in os.listdir(ASSETS_DIR):
        name_no_ext, ext = os.path.splitext(file)
        if name_no_ext.lower() == prefix.lower():
            filepath = os.path.join(ASSETS_DIR, file)
            ext_clean = ext.lower().replace(".", "")
            mime = "image/svg+xml" if ext_clean == "svg" else f"image/{'jpeg' if ext_clean in ['jpg', 'jpeg'] else ext_clean}"
            try:
                with open(filepath, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                    return f"data:{mime};base64,{encoded}"
            except Exception:
                return ""
    return ""

def render_login_logos():
    """Renderiza únicamente los logotipos superiores fijados en las esquinas del login."""
    logo_left = get_base64_image("logo2")
    logo_right = get_base64_image("logo")

    html_logos = '<div class="brand-top-header">'
    if logo_left:
        html_logos += f'<div class="brand-top-left"><img src="{logo_left}" class="brand-logo-left"></div>'
    if logo_right:
        html_logos += f'<div class="brand-top-right"><img src="{logo_right}" class="brand-logo-right"></div>'
    html_logos += '</div>'

    if logo_left or logo_right:
        st.markdown(html_logos, unsafe_allow_html=True)

def render_login_card_header():
    """Carga los textos del login desde templates/login.html."""
    html_path = os.path.join(TEMPLATES_DIR, "login.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)

def render_dashboard_header():
    """Renderiza el encabezado principal del dashboard desde templates/dashboard_header.html."""
    html_path = os.path.join(TEMPLATES_DIR, "dashboard_header.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)

def render_sidebar_logo():
    """Renderiza el logotipo de la barra lateral centrado."""
    html = """
        <div class="sidebar-brand-container sidebar-brand-centered">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 40" width="75">
                <text x="0" y="30" font-family="Trebuchet MS, sans-serif" font-size="34" font-weight="900" fill="#FFFFFF" letter-spacing="-1.5">BBVA</text>
            </svg>
            <div class="sidebar-brand-divider"></div>
            <span class="sidebar-brand-text">Tecmilenio</span>
        </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_kpi_card(title: str, value: str, subtext: str, is_cyan: bool = False):
    """Renderiza una tarjeta individual de KPI."""
    card_class = "kpi-card kpi-card-cyan" if is_cyan else "kpi-card"
    html = f"""
        <div class="{card_class}">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-subtext">{subtext}</div>
        </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_reflection_box(val_ratio_deuda: float, val_flujo: float):
    """Renderiza la sección de Reflexión Financiera y Alertas."""
    deuda_msg = (
        "⚠️ <i>Te recomendamos postergar compras no esenciales hasta reducir este porcentaje por debajo del 30%.</i>"
        if val_ratio_deuda > 30
        else "✅ <i>Tu nivel de endeudamiento está bajo control.</i>"
    )
    html = f"""
        <div class="reflection-box">
            <h4 class="reflection-title">🧠 Reflexión Financiera y Alertas Tempranas</h4>
            <p class="reflection-desc">
                Vivimos en una sociedad con altos incentivos al consumo constante. Analizar tu historial te permite hacer una pausa reflexiva antes de un gasto impulsivo:
            </p>
            <ul class="reflection-list">
                <li><b>Nivel de Deuda:</b> Tus créditos absorben el <b>{val_ratio_deuda:.1f}%</b> de lo que ganas. {deuda_msg}</li>
                <li><b>Margen de Maniobra:</b> Cuentas con <b>${val_flujo:,.2f} MXN</b> libres este mes. Si surge un imprevisto, este es tu colchón de liquidez real.</li>
            </ul>
        </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_floating_ai_assistant(sel_client: str, sel_periodo: str = None):
    """Renderiza el widget flotante con la información exacta del periodo activo."""
    with st.popover("💬 Asistente IA BBVA", use_container_width=False):
        st.markdown("<h4 style='color: #2DCCCD; margin-bottom: 2px;'>💬 Asistente Financiero BBVA</h4>", unsafe_allow_html=True)
        st.caption("Consulta tus KPIs, metas o simula reducciones de gasto en tiempo real.")
        
        if "chat_user" not in st.session_state or st.session_state.chat_user != sel_client:
            st.session_state.chat_user = sel_client
            st.session_state.messages = [
                {"role": "assistant", "content": f"¡Hola `{sel_client}`! Soy tu asistente del Gemelo Digital Financiero. ¿En qué puedo ayudarte hoy?"}
            ]

        chat_container = st.container(height=360)
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Escribe tu consulta aquí..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("🤖 Pensando respuesta..."):
                        # Pasar sel_periodo para amarrar la consulta al mes activo
                        response_obj = process_user_query(
                            prompt, 
                            authenticated_customer_id=sel_client,
                            periodo=sel_periodo
                        )
                        ans = response_obj["response"]
                    st.markdown(ans)

            st.session_state.messages.append({"role": "assistant", "content": ans})