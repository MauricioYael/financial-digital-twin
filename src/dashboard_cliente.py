import os
import glob
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from macro_engine import calculate_macro_projections

def find_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None

st.set_page_config(
    page_title="BBVA - Mi Salud Financiera",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos visuales BBVA x Tecmilenio
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

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020814 0%, #041026 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }

    .kpi-card {
        background: linear-gradient(135deg, rgba(7, 26, 56, 0.85) 0%, rgba(3, 13, 34, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 18px 20px;
        position: relative;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }

    .kpi-card-cyan {
        border: 1px solid rgba(45, 204, 205, 0.5);
        box-shadow: 0 0 20px rgba(45, 204, 205, 0.15);
    }

    .kpi-title {
        font-size: 13px;
        color: #8a9bb0;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .kpi-value {
        font-size: 28px;
        font-weight: 800;
        color: #ffffff;
        margin: 8px 0 4px 0;
        letter-spacing: -0.5px;
    }

    .kpi-subtext {
        font-size: 11px;
        color: #2DCCCD;
        font-weight: 600;
    }

    .chart-panel {
        background: linear-gradient(180deg, rgba(7, 26, 56, 0.7) 0%, rgba(3, 13, 34, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }

    .panel-header {
        font-size: 15px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .summary-box {
        background: rgba(45, 204, 205, 0.08);
        border: 1px solid rgba(45, 204, 205, 0.25);
        border-radius: 10px;
        padding: 14px;
        margin-top: 10px;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Rutas de archivos
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GOLD_DIR = os.path.join(BASE_DIR, "data", "gold")
GOLD_PATH = os.path.join(GOLD_DIR, "gold_cliente_mes.parquet")

df_gold = pd.DataFrame()
if os.path.exists(GOLD_PATH):
    df_gold = pd.read_parquet(GOLD_PATH)

# Sidebar Co-Branding y Filtros
with st.sidebar:
    header_html = (
        '<div style="display: flex; align-items: center; gap: 10px; padding: 5px 0 20px 0;">'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 40" width="75"><text x="0" y="30" font-family=\'Trebuchet MS\', sans-serif font-size="34" font-weight="900" fill="#FFFFFF" letter-spacing="-1.5">BBVA</text></svg>'
        '<div style="height: 20px; width: 1px; background-color: rgba(255, 255, 255, 0.3);"></div>'
        '<div style="display: flex; align-items: center; gap: 6px;">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#2DCCCD" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 17L12 22L22 17" stroke="#2DCCCD" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 12L12 17L22 12" stroke="#2DCCCD" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        '<span style="color: #FFFFFF; font-weight: 800; font-size: 13px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; letter-spacing: -0.3px;">Tecmilenio</span>'
        '</div>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)
    st.markdown("### 👤 **Mi Perfil**")

    if not df_gold.empty:
        clientes = list(df_gold['customer_id'].unique())
        sel_client = st.selectbox("Identificador de Cliente:", clientes, index=0)
        
        periodos = list(df_gold[df_gold['customer_id'] == sel_client]['periodo'].unique())
        sel_periodo = st.selectbox("Periodo de Consulta:", periodos, index=0)
    else:
        sel_client, sel_periodo = None, None

    st.markdown("""
        <div style="position: fixed; bottom: 30px; left: 20px; width: 180px;">
            <p style="color: #ffffff; font-size: 12px; font-weight: 600; line-height: 1.3; margin-bottom: 6px;">
                Banca Digital BBVA
            </p>
            <div style="width: 30px; height: 3px; background-color: #2DCCCD; border-radius: 2px;"></div>
        </div>
    """, unsafe_allow_html=True)

# Encabezado Principal
st.markdown("""
    <p style="color: #8a9bb0; font-size: 14px; margin: 0;">Bienvenido a tu Gemelo Digital</p>
    <h1 style="color: #ffffff; font-size: 28px; font-weight: 800; margin: 0; letter-spacing: -0.5px;">
        Mi Salud Financiera <span style="color: #2DCCCD;">BBVA</span>
    </h1>
    <p style="color: #8a9bb0; font-size: 13px; margin-top: 4px;">
        Análisis claro y transparente de tus ingresos, gastos operacionales, compromisos de deuda y proyecciones de ahorro.
    </p>
""", unsafe_allow_html=True)

st.write("")

if not df_gold.empty and sel_client and sel_periodo:
    df_c = df_gold[(df_gold['customer_id'] == sel_client) & (df_gold['periodo'] == sel_periodo)].iloc[0]

    # Detección flexible de nombre de columna de deuda
    col_deuda = 'pago_deuda_mensual' if 'pago_deuda_mensual' in df_c.index else 'pagos_deuda'
    val_deuda = float(df_c.get(col_deuda, 0.0))
    val_ingresos = float(df_c.get('ingresos_totales', 0.0))
    val_gastos_tot = float(df_c.get('gastos_totales', 0.0))
    val_gastos_op = float(df_c.get('gastos_operativos', max(0.0, val_gastos_tot - val_deuda)))
    val_flujo = float(df_c.get('flujo_neto', 0.0))
    val_ahorro = float(df_c.get('tasa_ahorro', 0.0)) * 100
    val_ratio_deuda = float(df_c.get('ratio_endeudamiento', 0.0)) * 100

    # 1. TARJETAS DE KPIS PRINCIPALES
    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">💵 Ingresos Totales</div>
            <div class="kpi-value">${val_ingresos:,.2f}</div>
            <div class="kpi-subtext">Entradas del mes</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">🛒 Gastos Operativos</div>
            <div class="kpi-value">${val_gastos_op:,.2f}</div>
            <div class="kpi-subtext">Consumos directos</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">💳 Pago de Préstamos</div>
            <div class="kpi-value">${val_deuda:,.2f}</div>
            <div class="kpi-subtext">Compromisos de crédito</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
        <div class="kpi-card kpi-card-cyan">
            <div class="kpi-title">🌱 Flujo Neto Real</div>
            <div class="kpi-value">${val_flujo:,.2f}</div>
            <div class="kpi-subtext">Disponible libre</div>
        </div>
        """, unsafe_allow_html=True)

    with k5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">📊 Tasa de Ahorro</div>
            <div class="kpi-value">{val_ahorro:.1f}%</div>
            <div class="kpi-subtext">Capacidad de reserva</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.write("")

    # 2. SECCIÓN VISUAL (Gráficos)
    col_chart1, col_chart2 = st.columns([1.3, 1.7])

    with col_chart1:
        st.markdown("""
        <div class="chart-panel">
            <div class="panel-header">
                <span>🍩 Distribución del Presupuesto</span>
            </div>
        """, unsafe_allow_html=True)

        labels = ['Gastos Operativos', 'Pago de Préstamos', 'Flujo Neto (Ahorro/Disponible)']
        values = [val_gastos_op, val_deuda, max(0.0, val_flujo)]

        fig_pie = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.6,
            marker=dict(colors=['#1464A5', '#D32F2F', '#2DCCCD']),
            textinfo='label+percent'
        )])
        fig_pie.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            font=dict(color='#8a9bb0', size=11)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown(f"""
        <div class="summary-box">
            <span style="color: #ffffff; font-size: 12px; font-weight: 700;">📌 Diagnóstico BBVA:</span><br>
            <span style="color: #cbd5e1; font-size: 12px;">
                Tus pagos de crédito representan el <b>{val_ratio_deuda:.1f}%</b> de tus ingresos. Mantienes un flujo libre disponible de <b>${val_flujo:,.2f}</b> en el periodo seleccionado.
            </span>
        </div>
        </div>
        """, unsafe_allow_html=True)

    with col_chart2:
        st.markdown("""
        <div class="chart-panel">
            <div class="panel-header">
                <span>📈 Historico de Tendencia del Cliente</span>
            </div>
        """, unsafe_allow_html=True)

        df_user_history = df_gold[df_gold['customer_id'] == sel_client].sort_values('periodo')

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=df_user_history['periodo'], y=df_user_history['ingresos_totales'],
            mode='lines+markers', name='Ingresos',
            line=dict(color='#2DCCCD', width=3)
        ))
        
        hist_deuda = df_user_history[col_deuda] if col_deuda in df_user_history.columns else 0
        hist_op = df_user_history.get('gastos_operativos', df_user_history['gastos_totales'] - hist_deuda)

        fig_trend.add_trace(go.Scatter(
            x=df_user_history['periodo'], y=hist_op,
            mode='lines+markers', name='Gastos Operativos',
            line=dict(color='#1464A5', width=2)
        ))
        fig_trend.add_trace(go.Scatter(
            x=df_user_history['periodo'], y=hist_deuda,
            mode='lines+markers', name='Pago Deuda',
            line=dict(color='#D32F2F', width=2, dash='dot')
        ))
        fig_trend.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8a9bb0', size=11),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # 3. SIMULADOR MACROECONÓMICO "WHAT-IF"
    st.markdown("""
    <div class="chart-panel">
        <div class="panel-header">
            <span>🔮 Simulador de Liquidez Futura ("What-If Macro")</span>
            <span style="font-size: 11px; color: #2DCCCD;">Ajustado por Inflación & Tipo de Cambio</span>
        </div>
    """, unsafe_allow_html=True)

    sim_col1, sim_col2 = st.columns(2)
    with sim_col1:
        inf_annual = st.slider("Escenario de Inflación Anual Estimada (%)", min_value=1.0, max_value=15.0, value=4.5, step=0.1) / 100.0
    with sim_col2:
        usd_rate = st.number_input("Tipo de Cambio Proyectado USD/MXN", min_value=10.0, max_value=30.0, value=18.50, step=0.25)

    df_single = pd.DataFrame([df_c])
    df_proj = calculate_macro_projections(df_single, inflation_annual=inf_annual, usd_mxn=usd_rate)

    if not df_proj.empty:
        r_p = df_proj.iloc[0]
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Proyección 3 Meses (MXN)", f"${r_p['proyeccion_3m_mxn']:,.2f}")
        p2.metric("Proyección 6 Meses (MXN)", f"${r_p['proyeccion_6m_mxn']:,.2f}")
        p3.metric("Proyección 6 Meses (USD)", f"${r_p['proyeccion_6m_usd']:,.2f} USD")
        p4.metric("Efecto Inflación (Pérdida 3M)", f"-${r_p['impacto_inflacion_3m']:,.2f}", delta_color="inverse")

    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.warning("⚠️ No se encontraron datos cargados en la Capa Gold. Ejecuta `python src/gold_builder.py` para sincronizar.")