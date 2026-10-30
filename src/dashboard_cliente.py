import os
import sys
import glob
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Configuración de rutas
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from macro_engine import calculate_macro_projections
from src.ml_engine import (
    train_and_evaluate_models,
    run_what_if_simulation,
    run_monte_carlo_simulation
)

st.set_page_config(
    page_title="BBVA - Mi Salud Financiera",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carga modular de CSS
def load_css(css_path):
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

CSS_FILE = os.path.join(PROJECT_ROOT, "assets", "styles.css")
load_css(CSS_FILE)

# Estilos visuales de respaldo (Dark Elegance)
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at 80% 20%, #072146 0%, #020a17 60%, #01050d 100%);
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 95%;
    }
    .kpi-card {
        background: linear-gradient(135deg, rgba(7, 26, 56, 0.85) 0%, rgba(3, 13, 34, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }
    .kpi-card-cyan {
        border: 1px solid rgba(45, 204, 205, 0.4);
        box-shadow: 0 0 20px rgba(45, 204, 205, 0.12);
    }
    .kpi-title {
        font-size: 12px;
        color: #8a9bb0;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 24px;
        font-weight: 800;
        color: #ffffff;
        margin: 4px 0;
    }
    .kpi-subtext {
        font-size: 11px;
        color: #2DCCCD;
        font-weight: 600;
    }
    .chart-panel {
        background: linear-gradient(180deg, rgba(7, 26, 56, 0.6) 0%, rgba(3, 13, 34, 0.75) 100%);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
    }
    .panel-header {
        font-size: 15px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .reflection-box {
        background: linear-gradient(135deg, rgba(20, 100, 165, 0.15) 0%, rgba(45, 204, 205, 0.08) 100%);
        border: 1px solid rgba(45, 204, 205, 0.3);
        border-radius: 12px;
        padding: 16px 20px;
        margin-top: 15px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Carga de la Capa Gold
BASE_DIR = PROJECT_ROOT
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "gold_cliente_mes.parquet")

df_gold = pd.DataFrame()
if os.path.exists(GOLD_PATH):
    df_gold = pd.read_parquet(GOLD_PATH)

# Sidebar Co-Branding
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; padding: 5px 0 20px 0;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 40" width="75"><text x="0" y="30" font-family='Trebuchet MS', sans-serif font-size="34" font-weight="900" fill="#FFFFFF" letter-spacing="-1.5">BBVA</text></svg>
            <div style="height: 20px; width: 1px; background-color: rgba(255, 255, 255, 0.3);"></div>
            <span style="color: #FFFFFF; font-weight: 800; font-size: 13px;">Tecmilenio</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 👤 **Mi Perfil**")
    if not df_gold.empty:
        clientes = list(df_gold['customer_id'].unique())
        sel_client = st.selectbox("Seleccionar Cliente:", clientes, index=0)
        
        periodos = list(df_gold[df_gold['customer_id'] == sel_client]['periodo'].unique())
        sel_periodo = st.selectbox("Periodo de Consulta:", periodos, index=0)
    else:
        sel_client, sel_periodo = None, None

# Encabezado Principal
st.markdown("""
    <p style="color: #8a9bb0; font-size: 14px; margin: 0;">Bienvenido a tu Gemelo Digital Financiero</p>
    <h1 style="color: #ffffff; font-size: 28px; font-weight: 800; margin: 0; letter-spacing: -0.5px;">
        Mi Salud Financiera <span style="color: #2DCCCD;">BBVA</span>
    </h1>
    <p style="color: #8a9bb0; font-size: 13px; margin-top: 4px;">
        Visualiza la historia de tu dinero de forma sencilla, anticipa escenarios y toma decisiones conscientes sobre tu consumo.
    </p>
""", unsafe_allow_html=True)

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

    # 1. TARJETAS DE KPIS PRINCIPALES (Sencillas y claras)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">💵 Ingresos Totales</div><div class="kpi-value">${val_ingresos:,.2f}</div><div class="kpi-subtext">Tus entradas del mes</div></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">🛒 Gastos del Día a Día</div><div class="kpi-value">${val_gastos_op:,.2f}</div><div class="kpi-subtext">Consumo y servicios</div></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">💳 Pago de Créditos</div><div class="kpi-value">${val_deuda:,.2f}</div><div class="kpi-subtext">Préstamos y tarjetas</div></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="kpi-card kpi-card-cyan"><div class="kpi-title">🌱 Dinero Libre (Flujo)</div><div class="kpi-value">${val_flujo:,.2f}</div><div class="kpi-subtext">Disponible real</div></div>', unsafe_allow_html=True)
    with k5:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">📊 % Ahorro del Mes</div><div class="kpi-value">{val_ahorro:.1f}%</div><div class="kpi-subtext">Reserva guardada</div></div>', unsafe_allow_html=True)

    st.write("")

    # 2. SECCIÓN VISUAL HISTÓRICA Y REFLEXIÓN
    col_chart1, col_chart2 = st.columns([1.2, 1.8])

    with col_chart1:
        st.markdown('<div class="chart-panel"><div class="panel-header"><span>🍩 ¿A dónde se va tu dinero?</span></div>', unsafe_allow_html=True)

        labels = ['Gastos Diarios', 'Pagos de Crédito', 'Dinero Disponible']
        values = [val_gastos_op, val_deuda, max(0.0, val_flujo)]

        fig_pie = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.68,
            marker=dict(colors=['#1464A5', '#D32F2F', '#2DCCCD']),
            textinfo='percent',
            hoverinfo='label+value'
        )])
        fig_pie.update_layout(
            height=240,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            font=dict(color='#8a9bb0', size=11)
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_chart2:
        st.markdown('<div class="chart-panel"><div class="panel-header"><span>📈 Comportamiento Histórico de tus Finanzas</span></div>', unsafe_allow_html=True)

        df_user_history = df_gold[df_gold['customer_id'] == sel_client].sort_values('periodo')

        fig_trend = go.Figure()
        # Trazo principal fino con relleno suave
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

    # 3. MÓDULO DE REFLEXIÓN Y ALERTAS DE CONSUMO
    st.markdown(f"""
        <div class="reflection-box">
            <h4 style="color: #2DCCCD; margin: 0 0 8px 0; font-size: 16px;">🧠 Reflexión Financiera y Alertas Tempranas</h4>
            <p style="color: #e2e8f0; font-size: 13px; line-height: 1.5; margin: 0;">
                Vivimos en una sociedad con altos incentivos al consumo constante. Analizar tu historial te permite hacer una pausa reflexiva antes de un gasto impulsivo:
            </p>
            <ul style="color: #cbd5e1; font-size: 12px; margin-top: 8px; margin-bottom: 0;">
                <li><b>Nivel de Deuda:</b> Tus créditos absorben el <b>{val_ratio_deuda:.1f}%</b> de lo que ganas. {"⚠️ <i>Te recomendamos postergar compras no esenciales hasta reducir este porcentaje por debajo del 30%.</i>" if val_ratio_deuda > 30 else "✅ <i>Tu nivel de endeudamiento está bajo control.</i>"}</li>
                <li><b>Margen de Maniobra:</b> Cuentas con <b>${val_flujo:,.2f} MXN</b> libres este mes. Si surge un imprevisto, este es tu colchón de liquidez real.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

    st.write("")

    # 4. PESTAÑAS INTERACTIVAS DE PREDICCIÓN Y SIMULACIÓN
    st.markdown("### 🔮 Proyecciones Inteligentes y Simuladores")
    tab_ia, tab_whatif, tab_mc = st.tabs([
        "🤖 Pronóstico Inteligente (Red Neuronal)", 
        "⚡ Escenarios ¿Qué pasaría si...?", 
        "🎰 Simulación de Futuros Posibles (Monte Carlo)"
    ])

    # A. INTELIGENCIA ARTIFICIAL
    with tab_ia:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        metricas_df, model_mlp = train_and_evaluate_models(df_gold, error_margin_mxn=1000.0)
        
        if isinstance(metricas_df, pd.DataFrame):
            st.markdown("##### 📊 Precisión de los Modelos Entrenados")
            st.dataframe(metricas_df, use_container_width=True)

            fig_mlp = go.Figure()
            fig_mlp.add_trace(go.Scatter(
                x=df_user_history["periodo"],
                y=df_user_history["flujo_neto"],
                mode='lines+markers',
                name='Dinero Libre Real',
                line=dict(color='#2DCCCD', width=2.5, shape='spline'),
                fill='tozeroy',
                fillcolor='rgba(45, 204, 205, 0.08)'
            ))
            fig_mlp.update_layout(
                height=260,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#8a9bb0', size=11),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
            )
            st.plotly_chart(fig_mlp, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # B. WHAT-IF
    with tab_whatif:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.caption("Ajusta los controles para simular cómo cambiaría tu dinero libre si aumentas tus gastos o disminuyes tus ingresos.")
        
        ing_p = float(df_gold[df_gold['customer_id'] == sel_client]["ingresos_totales"].tail(3).mean())
        gas_p = float(df_gold[df_gold['customer_id'] == sel_client]["gastos_totales"].tail(3).mean())

        col_w1, col_w2 = st.columns(2)
        with col_w1: var_g = st.slider("Si mis gastos cambian un (%):", -50, 100, 20, step=5)
        with col_w2: var_i = st.slider("Si mis ingresos cambian un (%):", -50, 50, -15, step=5)

        res = run_what_if_simulation(ing_p, gas_p, pct_gasto_var=var_g, pct_ingreso_var=var_i)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingreso Proyectado", f"${res['nuevo_ingreso']:,.2f} MXN", delta=f"{var_i}%")
        c2.metric("Gasto Proyectado", f"${res['nuevo_gasto']:,.2f} MXN", delta=f"{var_g}%", delta_color="inverse")
        c3.metric("Nuevo Dinero Libre", f"${res['flujo_simulado']:,.2f} MXN")
        c4.metric("Diferencia Mensual", f"${res['diferencia']:,.2f} MXN")
        st.markdown('</div>', unsafe_allow_html=True)

    # C. MONTE CARLO (Gráfica no grotesca, ultra clara)
    with tab_mc:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.caption("Evaluación de 1,000 caminos posibles para los próximos 6 meses considerando imprevistos.")
        
        ing_p = float(df_gold[df_gold['customer_id'] == sel_client]["ingresos_totales"].tail(3).mean())
        gas_p = float(df_gold[df_gold['customer_id'] == sel_client]["gastos_totales"].tail(3).mean())
        gas_std = float(df_gold[df_gold['customer_id'] == sel_client]["gastos_totales"].std()) if len(df_gold[df_gold['customer_id'] == sel_client]) > 1 else gas_p * 0.15

        mc = run_monte_carlo_simulation(ing_p, gas_p, gas_std, saldo_inicial=30000.0, n_trayectorias=1000, meses=6, seed=42)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Escenario Difícil (P10)", f"${mc['p10']:,.2f} MXN")
        k2.metric("Camino Más Probable (P50)", f"${mc['p50_mediana']:,.2f} MXN")
        k3.metric("Escenario Favorable (P90)", f"${mc['p90']:,.2f} MXN")
        k4.metric("⚠️ Riesgo de Quedar en $0", f"{mc['prob_saldo_negativo']:.1f}%")

        # Trazado de muestra limpia
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
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
        )
        st.plotly_chart(fig_mc, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.warning("⚠️ No se encontraron datos en la Capa Gold. Ejecuta `python src/gold_builder.py` para sincronizar.")