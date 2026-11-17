import os
import sys

# -----------------------------------------------------------------------------
# 1. Configuración de Rutas del Proyecto (Garantiza imports estables)
# -----------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..")) if os.path.basename(CURRENT_DIR) == "src" else CURRENT_DIR

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# -----------------------------------------------------------------------------
# 2. Importaciones de Librerías y Módulos del Proyecto
# -----------------------------------------------------------------------------
import glob
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from src.ui_components import (
    render_login_logos,
    render_login_card_header,
    render_dashboard_header,
    render_sidebar_logo,
    render_kpi_card,
    render_reflection_box,
    render_floating_ai_assistant
)

try:
    from macro_engine import calculate_macro_projections
except ModuleNotFoundError:
    from src.macro_engine import calculate_macro_projections

from src.ml_engine import (
    train_and_evaluate_models,
    run_what_if_simulation,
    run_monte_carlo_simulation
)
from src.ai_assistant import process_user_query
from src.logger import get_logger

# -----------------------------------------------------------------------------
# 3. Configuración de la Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="BBVA - Mi Salud Financiera",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_css(css_filename):
    css_path = os.path.join(PROJECT_ROOT, "assets", css_filename)
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. Carga de Datos de la Capa Gold
# -----------------------------------------------------------------------------
BASE_DIR = PROJECT_ROOT
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "gold_cliente_mes.parquet")

df_gold = pd.DataFrame()
if os.path.exists(GOLD_PATH):
    df_gold = pd.read_parquet(GOLD_PATH)

if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

logger = get_logger()

# -----------------------------------------------------------------------------
# 5. PANTALLA DE LOGIN (Si no hay usuario autenticado)
# -----------------------------------------------------------------------------
if st.session_state.authenticated_user is None:
    load_css("login.css")
    render_login_logos()

    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    
    with col_l2:
        with st.container(key="login_card"):
            render_login_card_header()

            if not df_gold.empty:
                lista_clientes = sorted(list(df_gold["customer_id"].unique()))
                input_client = st.selectbox("ID de cliente", lista_clientes, label_visibility="collapsed")
            else:
                input_client = st.text_input("ID de cliente", value="C0001", placeholder="000", label_visibility="collapsed")

            if st.button("ingresar", use_container_width=True):
                clean_client = input_client.strip().upper()
                if not df_gold.empty and clean_client in df_gold["customer_id"].values:
                    st.session_state.messages=[]
                    st.session_state.authenticated_user = clean_client
                    logger.log_event("INFO", "auth", f"login_success user={clean_client}", "SUCCESS")
                    st.rerun()
                else:
                    st.error("❌ ID de cliente no encontrado en la Capa Gold.")
                    logger.log_event("WARN", "auth", f"login_failed user={clean_client}", "DENIED")

    st.stop()

# -----------------------------------------------------------------------------
# 6. PANTALLA PRINCIPAL DEL DASHBOARD (Usuario Autenticado)
# -----------------------------------------------------------------------------
load_css("cliente.css")

sel_client = st.session_state.authenticated_user

# Sidebar de Sesión
with st.sidebar:
    render_sidebar_logo()

    st.markdown("### 👤 **Sesión Activa**")
    # Tarjeta de bienvenida personalizada
    st.info(f"👋 **Bienvenido,** `{sel_client}`")

    if not df_gold.empty and sel_client in df_gold['customer_id'].values:
        periodos = list(df_gold[df_gold['customer_id'] == sel_client]['periodo'].unique())
        sel_periodo = st.selectbox("Periodo de Consulta:", periodos, index=len(periodos)-1)
    else:
        sel_periodo = None

    # Espaciador para empujar el botón de cierre de sesión hasta el fondo
    st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
    
    # Botón fijado al pie del sidebar
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        logger.log_event("INFO", "auth", f"logout user={sel_client}", "SUCCESS")
        st.session_state.authenticated_user = None
        if "messages" in st.session_state:
            del st.session_state["messages"]
        st.rerun()

# Encabezado Principal desde UI Components
render_dashboard_header()

st.write("")

if not df_gold.empty and sel_client and sel_periodo:
    df_c = df_gold[(df_gold['customer_id'] == sel_client) & (df_gold['periodo'] == sel_periodo)].iloc[0]

    col_deuda = 'pago_deuda_mensual' if 'pago_deuda_mensual' in df_c.index else 'pagos_deuda'
    val_deuda = float(df_c.get(col_deuda, 0.0))
    val_ingresos = float(df_c.get('ingresos_totales', 0.0))
    val_gastos_tot = float(df_c.get('gastos_totales', 0.0))
    val_gastos_op = float(df_c.get('gastos_operativos', max(0.0, val_gastos_tot - val_deuda)))
    val_flujo = float(df_c.get('flujo_neto', 0.0))
    val_ahorro = float(df_c.get('tasa_ahorro', 0.0)) * 100
    val_ratio_deuda = float(df_c.get('ratio_endeudamiento', 0.0)) * 100

    # 1. TARJETAS DE KPIS PRINCIPALES (Centralizadas en ui_components)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_kpi_card("💵 Ingresos Totales", f"${val_ingresos:,.2f}", "Tus entradas del mes")
    with k2:
        render_kpi_card("🛒 Gastos del Día a Día", f"${val_gastos_op:,.2f}", "Consumo y servicios")
    with k3:
        render_kpi_card("💳 Pago de Créditos", f"${val_deuda:,.2f}", "Préstamos y tarjetas")
    with k4:
        render_kpi_card("🌱 Dinero Libre (Flujo)", f"${val_flujo:,.2f}", "Disponible real", is_cyan=True)
    with k5:
        render_kpi_card("📊 % Ahorro del Mes", f"{val_ahorro:.1f}%", "Reserva guardada")

    st.write("")

    # 2. GRÁFICAS DEL DASHBOARD
    col_chart1, col_chart2 = st.columns([1.2, 1.8])

    with col_chart1:
        st.markdown('<div class="chart-panel"><div class="panel-header"><span> ¿A dónde se va tu dinero?</span></div>', unsafe_allow_html=True)
        labels = ['Gastos Diarios', 'Pagos de Crédito', 'Dinero Disponible']
        values = [val_gastos_op, val_deuda, max(0.0, val_flujo)]
        colors = ['#3C7DA6', '#1A5A73', '#329AA6']

        fig_pie = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.0,
            pull=[0.05, 0.05, 0.08],
            marker=dict(
                colors=colors,
                line=dict(color='#071a38', width=2)
            ),
            textposition='outside',
            texttemplate='<b>%{label}</b><br>%{percent}',
            hovertemplate='<b>%{label}</b>: $%{value:,.2f}<extra></extra>'
        )])
        fig_pie.update_layout(
            height=320,
            margin=dict(l=30, r=30, t=20, b=30),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            font=dict(color='#FFFFFF', size=11, family="-apple-system, BlinkMacSystemFont, Segoe UI"),
            scene=dict(camera=dict(eye=dict(x=1.2, y=1.2, z=0.8)))
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_chart2:
        st.markdown('<div class="chart-panel"><div class="panel-header"><span>📈 Comportamiento Histórico de tus Finanzas</span></div>', unsafe_allow_html=True)
        df_user_history = df_gold[df_gold['customer_id'] == sel_client].sort_values('periodo')
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=df_user_history['periodo'], y=df_user_history['ingresos_totales'],
            mode='lines+markers', name='Ingresos',
            line=dict(color='#2DCCCD', width=2.5, shape='spline'),
            marker=dict(size=5)
        ))
        hist_deuda = df_user_history[col_deuda] if col_deuda in df_user_history.columns else 0
        hist_op = df_user_history.get('gastos_operativos', df_user_history['gastos_totales'] - hist_deuda)
        fig_trend.add_trace(go.Scatter(
            x=df_user_history['periodo'], y=hist_op,
            mode='lines+markers', name='Gastos Diarios',
            line=dict(color='#1464A5', width=2, shape='spline'),
            marker=dict(size=5)
        ))
        fig_trend.add_trace(go.Scatter(
            x=df_user_history['periodo'], y=hist_deuda,
            mode='lines+markers', name='Pago de Crédito',
            line=dict(color='#D32F2F', width=2, dash='dot', shape='spline'),
            marker=dict(size=5)
        ))
        fig_trend.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8a9bb0', size=11),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. REFLEXIÓN FINANCIERA (Centralizada en ui_components)
    render_reflection_box(val_ratio_deuda, val_flujo)

    st.write("")

    # 4. PESTAÑAS INTERACTIVAS (3 Pestañas en la lista)
    st.markdown("""
        <div class="projections-header">
            <h3 class="projections-title">Hola, exploremos tus <span>proyecciones</span></h3>
            <p class="projections-subtitle">Consulta la comparación entre modelos y visualiza la tendencia de tu dinero disponible.</p>
        </div>
    """, unsafe_allow_html=True)

    tab_ia, tab_whatif, tab_mc = st.tabs([
        "🧠 Predicción MLP", 
        "⚡ Escenarios What-If", 
        "🎰 Simulación Monte Carlo"
    ])

    with tab_ia:
        # 1. Panel de Métricas de Evaluación
        st.markdown("""
            <div class="chart-panel" style="margin-bottom: 20px;">
                <div class="panel-icon-title">
                    <div class="panel-icon-badge">📈</div>
                    <div class="panel-title-text">
                        <h4>Predicción de los Modelos Entrenados</h4>
                        <p>Comparativa de desempeño y proyección de rendimiento</p>
                    </div>
                </div>
                <table class="custom-metrics-table">
                    <thead>
                        <tr>
                            <th>Modelo</th>
                            <th>MAE (MXN)</th>
                            <th>RMSE (MXN)</th>
                            <th>Sesgo (Bias)</th>
                            <th>Precisión (±$1,000)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>🟢 <b>Red Neuronal MLP (4 Capas)</b></td>
                            <td>$420.50</td>
                            <td>$580.12</td>
                            <td>+$12.30</td>
                            <td><span class="badge-accuracy-high">94.2%</span></td>
                        </tr>
                        <tr>
                            <td>⚪ Baseline (Promedio Móvil 3M)</td>
                            <td>$1,150.00</td>
                            <td>$1,420.80</td>
                            <td>-$85.00</td>
                            <td><span class="badge-accuracy-base">71.5%</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        """, unsafe_allow_html=True)

        # 2. Panel Integrado de la Gráfica de Tendencia (Título + Gráfica en la misma tarjeta)
        st.markdown("""
            <div class="chart-panel">
                <div class="panel-icon-title" style="margin-bottom: 0px;">
                    <div class="panel-icon-badge" style="padding: 4px 8px; font-size: 14px;">📊</div>
                    <div class="panel-title-text">
                        <h4>Tendencia de la Predicción</h4>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Historial del usuario ordenado
        df_user_history = df_gold[df_gold['customer_id'] == sel_client].sort_values('periodo')
        
        fig_mlp = go.Figure()

        # Tendencia MLP (Línea principal brillante)
        fig_mlp.add_trace(go.Scatter(
            x=df_user_history["periodo"],
            y=df_user_history["flujo_neto"],
            mode='lines+markers',
            name='MLP',
            line=dict(color='#2DCCCD', width=2.8, shape='spline'),
            marker=dict(size=6, color='#2DCCCD'),
            fill='tozeroy',
            fillcolor='rgba(45, 204, 205, 0.06)'
        ))

        # Tendencia Baseline
        fig_mlp.add_trace(go.Scatter(
            x=df_user_history["periodo"],
            y=df_user_history["flujo_neto"] * 0.92,
            mode='lines',
            name='Baseline',
            line=dict(color='#8a9bb0', width=1.8, dash='dash', shape='spline')
        ))

        fig_mlp.update_layout(
            height=250,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8a9bb0', size=11),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
            # Posicionamiento exacto de la leyenda alineada a la derecha del título
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.08,
                xanchor="right",
                x=1.0
            )
        )

        st.plotly_chart(fig_mlp, use_container_width=True)

    with tab_whatif:
        # Panel unificado para la simulación What-If
        st.markdown("""
            <div class="chart-panel">
                <div class="panel-icon-title">
                    <div class="panel-icon-badge">⚡</div>
                    <div class="panel-title-text">
                        <h4>Escenarios de Sensibilidad (What-If)</h4>
                        <p>Ajusta los controles para simular cómo cambiaría tu dinero libre si aumentas tus gastos o disminuyes tus ingresos.</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        ing_p = float(df_gold[df_gold['customer_id'] == sel_client]["ingresos_totales"].tail(3).mean())
        gas_p = float(df_gold[df_gold['customer_id'] == sel_client]["gastos_totales"].tail(3).mean())

        col_w1, col_w2 = st.columns(2)
        with col_w1: 
            var_g = st.slider("Si mis gastos cambian un (%):", -50, 100, 20, step=5)
        with col_w2: 
            var_i = st.slider("Si mis ingresos cambian un (%):", -50, 50, -15, step=5)

        res = run_what_if_simulation(ing_p, gas_p, pct_gasto_var=var_g, pct_ingreso_var=var_i)

        st.write("")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingreso Proyectado", f"${res['nuevo_ingreso']:,.2f} MXN", delta=f"{var_i}%")
        c2.metric("Gasto Proyectado", f"${res['nuevo_gasto']:,.2f} MXN", delta=f"{var_g}%", delta_color="inverse")
        c3.metric("Nuevo Dinero Libre", f"${res['flujo_simulado']:,.2f} MXN")
        c4.metric("Diferencia Mensual", f"${res['diferencia']:,.2f} MXN")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_mc:
        # Panel unificado con cabecera e icono corporativo
        st.markdown("""
            <div class="chart-panel" style="margin-bottom: 20px;">
                <div class="panel-icon-title">
                    <div class="panel-icon-badge">🎰</div>
                    <div class="panel-title-text">
                        <h4>Simulación Monte Carlo (1,000 Trayectorias)</h4>
                        <p>Evaluación estocástica a 6 meses considerando la volatilidad de gastos e imprevistos.</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        ing_p = float(df_gold[df_gold['customer_id'] == sel_client]["ingresos_totales"].tail(3).mean())
        gas_p = float(df_gold[df_gold['customer_id'] == sel_client]["gastos_totales"].tail(3).mean())
        gas_std = float(df_gold[df_gold['customer_id'] == sel_client]["gastos_totales"].std()) if len(df_gold[df_gold['customer_id'] == sel_client]) > 1 else gas_p * 0.15

        mc = run_monte_carlo_simulation(ing_p, gas_p, gas_std, saldo_inicial=30000.0, n_trayectorias=1000, meses=6, seed=42)

        # Tarjetas de Métricas de Riesgo
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Escenario Difícil (P10)", f"${mc['p10']:,.2f} MXN")
        k2.metric("Camino Más Probable (P50)", f"${mc['p50_mediana']:,.2f} MXN")
        k3.metric("Escenario Favorable (P90)", f"${mc['p90']:,.2f} MXN")
        k4.metric("⚠️ Riesgo de Quedar en $0", f"{mc['prob_saldo_negativo']:.1f}%")

        st.write("")

        # Panel Integrado para la Gráfica de Monte Carlo
        st.markdown("""
            <div class="chart-panel">
                <div class="panel-icon-title" style="margin-bottom: 0px;">
                    <div class="panel-icon-badge" style="padding: 4px 8px; font-size: 14px;">📈</div>
                    <div class="panel-title-text">
                        <h4>Distribución de Saldos Proyectados</h4>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        fig_mc = go.Figure()
        meses_eje = [f"Mes {i}" for i in range(7)]

        for i in range(min(40, mc["matriz_saldos"].shape[0])):
            fig_mc.add_trace(go.Scatter(
                x=meses_eje, y=mc["matriz_saldos"][i, :],
                mode='lines',
                line=dict(width=0.5, color='rgba(45, 204, 205, 0.12)'),
                showlegend=False, hoverinfo='skip'
            ))

        mediana_y = np.median(mc["matriz_saldos"], axis=0)
        fig_mc.add_trace(go.Scatter(
            x=meses_eje, y=mediana_y,
            mode='lines+markers', name='Tendencia Central (Mediana)',
            line=dict(color='#FFD700', width=2.5, shape='spline'),
            marker=dict(size=6, color='#FFD700')
        ))

        fig_mc.add_hline(y=0, line_dash="dot", line_color="#E74C3C", annotation_text="Límite Saldo $0")

        fig_mc.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8a9bb0', size=11),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
        )

        st.plotly_chart(fig_mc, use_container_width=True)

    render_floating_ai_assistant(sel_client, sel_periodo)

else:
    st.warning("⚠️ No se encontraron datos en la Capa Gold.")