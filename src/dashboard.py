import os
import glob
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

def find_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None

st.set_page_config(
    page_title="BBVA Financial Digital Twin",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        max-width: 98%;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020814 0%, #041026 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
    
    div[data-testid="stRadio"] > label {
        display: none;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 6px;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        background: transparent;
        border-radius: 8px;
        padding: 10px 14px;
        color: #94a3b8;
        font-weight: 500;
        font-size: 14px;
        transition: all 0.2s ease;
        border: 1px solid transparent;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.03);
        color: #ffffff;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"] {
        background: linear-gradient(90deg, #004481 0%, #1464A5 100%);
        color: #ffffff !important;
        font-weight: 700;
        box-shadow: 0 4px 14px rgba(0, 68, 129, 0.4);
    }

    .kpi-card {
        background: linear-gradient(135deg, rgba(7, 26, 56, 0.8) 0%, rgba(3, 13, 34, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 18px 20px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }
    .kpi-card-cyan {
        border: 1px solid rgba(45, 204, 205, 0.4);
        box-shadow: 0 0 20px rgba(45, 204, 205, 0.15);
    }
    .kpi-card-red {
        border: 1px solid rgba(211, 47, 47, 0.3);
    }

    .kpi-title {
        font-size: 12px;
        color: #94a3b8;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .kpi-value {
        font-size: 32px;
        font-weight: 800;
        color: #ffffff;
        margin: 8px 0;
        letter-spacing: -0.5px;
    }
    .kpi-badge {
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 20px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-cyan { background: rgba(45, 204, 205, 0.15); color: #2DCCCD; }
    .badge-red  { background: rgba(211, 47, 47, 0.15); color: #ff6b6b; }
    .badge-blue { background: rgba(20, 100, 165, 0.15); color: #52a5e8; }

    .chart-panel {
        background: linear-gradient(180deg, rgba(7, 26, 56, 0.7) 0%, rgba(3, 13, 34, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        height: 100%;
    }
    .panel-header {
        font-size: 14px;
        font-weight: 700;
        color: #ffffff;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }

    .status-banner {
        background: linear-gradient(90deg, rgba(7, 33, 70, 0.8) 0%, rgba(4, 20, 44, 0.9) 100%);
        border: 1px solid rgba(45, 204, 205, 0.2);
        border-radius: 12px;
        padding: 14px 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 15px;
    }
    .status-item {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 13px;
        color: #cbd5e1;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #2DCCCD;
        box-shadow: 0 0 8px #2DCCCD;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze")
SILVER_DIR = os.path.join(BASE_DIR, "data", "silver")
GOLD_DIR = os.path.join(BASE_DIR, "data", "gold")
QUARANTINE_DIR = os.path.join(BASE_DIR, "data", "quarantine")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

REPORT_PATH = os.path.join(REPORTS_DIR, "validation_report.csv")
GOLD_PATH = os.path.join(GOLD_DIR, "gold_cliente_mes.parquet")
SILVER_TX_PATH = os.path.join(SILVER_DIR, "fct_transacciones.parquet")

bronze_files = glob.glob(os.path.join(BRONZE_DIR, "*.parquet"))
silver_files = glob.glob(os.path.join(SILVER_DIR, "*.parquet"))
quarantine_files = glob.glob(os.path.join(QUARANTINE_DIR, "*.parquet"))

if os.path.exists(REPORT_PATH):
    df_report = pd.read_csv(REPORT_PATH)
else:
    df_report = pd.DataFrame([
        {"dataset": "dim_clientes", "bronze": 150, "silver": 148, "rechazados": 2, "promueve": "si"},
        {"dataset": "fct_transacciones", "bronze": 540, "silver": 532, "rechazados": 8, "promueve": "si"},
        {"dataset": "dim_compromisos_fijos", "bronze": 10, "silver": 9, "rechazados": 1, "promueve": "no"}
    ])

df_quarantine = pd.DataFrame()
if quarantine_files:
    dfs = [pd.read_parquet(f) for f in quarantine_files]
    df_quarantine = pd.concat(dfs, ignore_index=True)

df_gold = pd.DataFrame()
if os.path.exists(GOLD_PATH):
    df_gold = pd.read_parquet(GOLD_PATH)

df_silver_tx = pd.DataFrame()
if os.path.exists(SILVER_TX_PATH):
    df_silver_tx = pd.read_parquet(SILVER_TX_PATH)
    if not df_silver_tx.empty:
        col_fecha = find_column(df_silver_tx, ['fecha_operacion', 'fecha', 'fecha_transaccion', 'date'])
        col_cliente = find_column(df_silver_tx, ['customer_id', 'cliente_id', 'id_cliente'])
        col_tipo = find_column(df_silver_tx, ['tipo_movimiento', 'tipo', 'type'])
        col_monto = find_column(df_silver_tx, ['monto', 'monto_total', 'amount'])

        rename_dict = {}
        if col_fecha: rename_dict[col_fecha] = 'fecha_operacion'
        if col_cliente: rename_dict[col_cliente] = 'customer_id'
        if col_tipo: rename_dict[col_tipo] = 'tipo_movimiento'
        if col_monto: rename_dict[col_monto] = 'monto'

        df_silver_tx = df_silver_tx.rename(columns=rename_dict)
        if 'fecha_operacion' in df_silver_tx.columns:
            df_silver_tx['fecha_operacion'] = pd.to_datetime(df_silver_tx['fecha_operacion'])
            df_silver_tx['periodo'] = df_silver_tx['fecha_operacion'].dt.strftime('%Y-%m')

total_bronze = int(df_report["bronze"].sum())
total_silver = int(df_report["silver"].sum())
total_gold = len(df_gold) if not df_gold.empty else 0
total_rechazados = int(df_report["rechazados"].sum())
tasa_calidad = round((total_silver / total_bronze * 100), 1) if total_bronze > 0 else 0.0
pct_rechazados = round((total_rechazados / total_bronze * 100), 1) if total_bronze > 0 else 0.0
num_archivos = len(bronze_files) if bronze_files else 6

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
    
    selected_nav = st.radio(
        "Navegación",
        [
            "🏠 Dashboard", 
            "📊 Calidad de Datos", 
            "🏆 Capa Gold (KPIs)", 
            "🔎 Conciliación Silver vs Gold", 
            "🛡️ Cuarentena"
        ],
        index=0
    )
    
    st.markdown("""
        <div style="position: fixed; bottom: 30px; left: 20px; width: 180px;">
            <p style="color: #ffffff; font-size: 13px; font-weight: 700; line-height: 1.3; margin-bottom: 6px;">
                Construyendo juntos un futuro más inteligente
            </p>
            <div style="width: 30px; height: 3px; background-color: #2DCCCD; border-radius: 2px;"></div>
        </div>
    """, unsafe_allow_html=True)

head_col1, head_col2 = st.columns([3, 1.5])

with head_col1:
    st.markdown("""
        <p style="color: #8a9bb0; font-size: 14px; margin: 0;">Hola,</p>
        <h1 style="color: #ffffff; font-size: 28px; font-weight: 800; margin: 0; letter-spacing: -0.5px;">
            BBVA <span style="color: #2DCCCD;">Financial Digital Twin</span>
        </h1>
        <p style="color: #8a9bb0; font-size: 13px; margin-top: 4px;">
            Datos que impulsan decisiones más inteligentes.
        </p>
    """, unsafe_allow_html=True)

with head_col2:
    f1, f2 = st.columns(2)
    with f1:
        st.selectbox("Rango", ["Últimos 7 días", "Hoy", "Mes actual"], index=0, label_visibility="collapsed")
    with f2:
        st.selectbox("Capa", ["Todas las Capas", "Bronze", "Silver", "Gold"], index=0, label_visibility="collapsed")

st.write("")

if selected_nav == "🏠 Dashboard":
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

    with kpi1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">📄 Archivos Lote</div>
            <div class="kpi-value">{num_archivos}</div>
            <div class="kpi-badge badge-blue">↑ +0 vs. semana anterior</div>
            <svg style="position:absolute; bottom:0; right:0; opacity:0.2;" width="100" height="40" viewBox="0 0 100 40">
                <path d="M0 30 Q 30 10, 60 25 T 100 10 L 100 40 L 0 40 Z" fill="#1464A5"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)

    with kpi2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">🗄️ Ingesta Bronze</div>
            <div class="kpi-value">{total_bronze:,}</div>
            <div class="kpi-badge badge-blue">↑ +12% vs. semana anterior</div>
            <svg style="position:absolute; bottom:0; right:0; opacity:0.25;" width="100" height="40" viewBox="0 0 100 40">
                <path d="M0 25 Q 40 5, 70 20 T 100 5 L 100 40 L 0 40 Z" fill="#2DCCCD"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)

    with kpi3:
        st.markdown(f"""
        <div class="kpi-card kpi-card-cyan">
            <div class="kpi-title">✔️ Válidos Silver</div>
            <div class="kpi-value">{total_silver:,}</div>
            <div class="kpi-badge badge-cyan">✔ {tasa_calidad}% Calidad</div>
            <svg style="position:absolute; bottom:0; right:0; opacity:0.3;" width="100" height="40" viewBox="0 0 100 40">
                <path d="M0 20 Q 35 30, 65 10 T 100 15 L 100 40 L 0 40 Z" fill="#2DCCCD"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)

    with kpi4:
        st.markdown(f"""
        <div class="kpi-card kpi-card-red">
            <div class="kpi-title">❗ Cuarentena</div>
            <div class="kpi-value">{total_rechazados:,}</div>
            <div class="kpi-badge badge-red">↑ +{pct_rechazados}% vs. semana</div>
            <svg style="position:absolute; bottom:0; right:0; opacity:0.25;" width="100" height="40" viewBox="0 0 100 40">
                <path d="M0 35 Q 40 15, 70 25 T 100 10 L 100 40 L 0 40 Z" fill="#D32F2F"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)

    with kpi5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">⚡ Latencia Pipeline</div>
            <div class="kpi-value">~1.2 s</div>
            <div class="kpi-badge badge-cyan">⚡ Optimizado</div>
            <svg style="position:absolute; bottom:0; right:0; opacity:0.2;" width="100" height="40" viewBox="0 0 100 40">
                <path d="M0 15 Q 30 35, 70 10 T 100 25 L 100 40 L 0 40 Z" fill="#2DCCCD"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    c1, c2, c3 = st.columns([1.5, 1.2, 1.3])

    with c1:
        st.markdown("""
            <div class="chart-panel">
                <div class="panel-header">
                    <span>📊 Evolución de Calidad de Datos</span>
                    <span class="kpi-badge badge-cyan">● 98.4%</span>
                </div>
        """, unsafe_allow_html=True)
        
        dates = pd.date_range(end=datetime.today(), periods=7).strftime("Oct %d")
        df_trend = pd.DataFrame({
            "Fecha": dates,
            "% Válidos": [96.0, 96.5, 97.2, 97.5, 98.0, 98.4, tasa_calidad],
            "% Rechazados": [4.0, 3.5, 2.8, 2.5, 2.0, 1.6, pct_rechazados]
        })
        
        fig_evol = go.Figure()
        fig_evol.add_trace(go.Scatter(
            x=df_trend["Fecha"], y=df_trend["% Válidos"],
            mode='lines+markers', name='% Válidos',
            line=dict(color='#2DCCCD', width=3, shape='spline'),
            marker=dict(size=6, color='#2DCCCD')
        ))
        fig_evol.add_trace(go.Scatter(
            x=df_trend["Fecha"], y=df_trend["% Rechazados"],
            mode='lines', name='% Rechazos',
            line=dict(color='#8a9bb0', width=2, dash='dash')
        ))
        fig_evol.update_layout(
            height=210,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8a9bb0', size=11),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', range=[80, 102]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_evol, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("""
            <div class="chart-panel">
                <div class="panel-header">
                    <span>💠 Distribución Válidos vs Cuarentena</span>
                </div>
        """, unsafe_allow_html=True)
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=["Válidos (Silver)", "Cuarentena"],
            values=[total_silver, total_rechazados if total_rechazados > 0 else 1],
            hole=0.75,
            marker=dict(colors=['#2DCCCD', '#D32F2F']),
            textinfo='none'
        )])
        fig_pie.update_layout(
            height=210,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=0.98),
            font=dict(color='#8a9bb0', size=11),
            annotations=[dict(text=f"<b>{total_bronze}</b><br><span style='font-size:10px; color:#8a9bb0;'>Total</span>", x=0.5, y=0.5, font_size=16, font_color="#ffffff", showarrow=False)]
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("""
            <div class="chart-panel">
                <div class="panel-header">
                    <span>📊 Volumetría por Capa Medallion</span>
                </div>
        """, unsafe_allow_html=True)
        
        df_layers = pd.DataFrame({
            "Capa": ["Bronze", "Silver"],
            "Registros": [total_bronze, total_silver]
        })
        fig_layers = px.bar(
            df_layers, x="Capa", y="Registros", color="Capa",
            color_discrete_map={"Bronze": "#1464A5", "Silver": "#2DCCCD"},
            text="Registros"
        )
        fig_layers.update_layout(
            height=210,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            font=dict(color='#8a9bb0', size=11),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
        )
        fig_layers.update_traces(textposition='outside')
        st.plotly_chart(fig_layers, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
        <div class="status-banner">
            <div class="status-item">
                <span class="status-dot"></span>
                <span><b>Sistema Operativo:</b> <span style="color: #2DCCCD;">Sin incidencias ●</span></span>
            </div>
            <div class="status-item">
                <span style="color: #8a9bb0;">🕒 <b>Última Ingesta:</b> Hace 12 min ●</span>
            </div>
            <div class="status-item">
                <span style="color: #8a9bb0;">⚡ <b>Próxima Ejecución:</b> En 3 h 48 min ●</span>
            </div>
            <div style="font-weight: 700; color: #ffffff; font-size: 13px;">
                Más datos. <span style="color: #2DCCCD;">Mejores decisiones.</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

elif selected_nav == "📊 Calidad de Datos":
    st.markdown("<h3 style='color: #2DCCCD; margin-bottom: 12px;'>📊 Calidad por Dataset y Lotes Procesados</h3>", unsafe_allow_html=True)
    
    q1, q2 = st.columns([1.4, 1.6])
    
    with q1:
        rows_html = ""
        for _, r in df_report.iterrows():
            b_cnt = int(r['bronze'])
            s_cnt = int(r['silver'])
            err_cnt = int(r['rechazados'])
            pct = round((s_cnt / b_cnt * 100), 1) if b_cnt > 0 else 0
            dot_color = "#2DCCCD" if err_cnt == 0 else ("#F8A000" if r.get('promueve', 'si') == 'si' else "#D32F2F")

            rows_html += f'<tr style="border-bottom: 1px solid rgba(255,255,255,0.06);"><td style="padding: 10px 12px; font-weight: 600; text-align: left;"><span style="color:{dot_color}; margin-right: 8px;">●</span>{r["dataset"]}</td><td style="padding: 10px 12px; color: #8a9bb0; text-align: center;">{b_cnt:,}</td><td style="padding: 10px 12px; color: {dot_color}; font-weight: 700; text-align: center;">{pct}%</td><td style="padding: 10px 12px; color: #ff6b6b; font-weight: 600; text-align: center;">{err_cnt:,}</td></tr>'

        table_html = f'<div class="chart-panel"><div class="panel-header">📑 Calidad por Dataset</div><table style="width: 100%; border-collapse: collapse; font-size: 13px; color: #e9eef2; margin-top: 6px;"><thead><tr style="border-bottom: 1px solid rgba(255,255,255,0.12); color: #8a9bb0; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;"><th style="padding: 8px 12px; text-align: left; width: 40%;">Dataset</th><th style="padding: 8px 12px; text-align: center; width: 20%;">Bronze</th><th style="padding: 8px 12px; text-align: center; width: 20%;">% Calidad</th><th style="padding: 8px 12px; text-align: center; width: 20%;">Errores</th></tr></thead><tbody>{rows_html}</tbody></table></div>'
        st.markdown(table_html, unsafe_allow_html=True)

    with q2:
        st.markdown('<div class="chart-panel"><div class="panel-header">📄 Lotes Recientes</div>', unsafe_allow_html=True)
        st.dataframe(df_report, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif selected_nav == "🏆 Capa Gold (KPIs)":
    st.markdown("<h3 style='color: #2DCCCD; margin-bottom: 12px;'>🏆 Consolidado Analítico de Negocio (`gold_cliente_mes`)</h3>", unsafe_allow_html=True)
    if not df_gold.empty:
        f1, f2 = st.columns(2)
        with f1:
            sel_p = st.selectbox("Periodo:", ["Todos"] + list(df_gold['periodo'].unique()))
        with f2:
            sel_c = st.selectbox("Cliente:", ["Todos"] + list(df_gold['customer_id'].unique()))

        df_f = df_gold.copy()
        if sel_p != "Todos": df_f = df_f[df_f['periodo'] == sel_p]
        if sel_c != "Todos": df_f = df_f[df_f['customer_id'] == sel_c]

        tot_ing = df_f['ingresos_totales'].sum()
        tot_gas = df_f['gastos_totales'].sum()
        flujo = df_f['flujo_neto'].sum()
        ahorro = df_f['tasa_ahorro'].mean() * 100
        deuda = df_f['ratio_endeudamiento'].mean() * 100

        g1, g2, g3, g4, g5 = st.columns(5)
        g1.metric("Ingresos Totales", f"${tot_ing:,.2f}")
        g2.metric("Gastos Totales", f"${tot_gas:,.2f}")
        g3.metric("Flujo Neto", f"${flujo:,.2f}")
        g4.metric("Tasa Ahorro Prom.", f"{ahorro:.1f}%")
        g5.metric("Ratio Endeudamiento", f"{deuda:.1f}%")

        st.write("")
        st.dataframe(df_f, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Ejecuta `python src/gold_builder.py` para generar la capa Gold.")

elif selected_nav == "🔎 Conciliación Silver vs Gold":
    st.markdown("<h3 style='color: #2DCCCD;'>🔎 Inspector de Conciliación en Vivo (Silver vs Gold)</h3>", unsafe_allow_html=True)
    if not df_gold.empty and not df_silver_tx.empty:
        c1, c2 = st.columns(2)
        with c1:
            c_id = st.selectbox("Cliente:", df_gold['customer_id'].unique())
        with c2:
            p_id = st.selectbox("Periodo:", df_gold[df_gold['customer_id'] == c_id]['periodo'].unique())

        silver_sub = df_silver_tx[(df_silver_tx['customer_id'] == c_id) & (df_silver_tx['periodo'] == p_id)]
        if 'categoria' in silver_sub.columns:
            silver_sub = silver_sub[silver_sub['categoria'] != 'TRANSFERENCIA_PROPIA']

        col_tipo = find_column(silver_sub, ['tipo_movimiento', 'tipo', 'type'])
        col_monto = find_column(silver_sub, ['monto', 'monto_total', 'amount'])

        s_ing = silver_sub[silver_sub[col_tipo] == 'INGRESO'][col_monto].sum() if col_tipo and col_monto else 0.0
        s_gas = silver_sub[silver_sub[col_tipo] == 'EGRESO'][col_monto].sum() if col_tipo and col_monto else 0.0
        s_flujo = s_ing - s_gas

        gold_row = df_gold[(df_gold['customer_id'] == c_id) & (df_gold['periodo'] == p_id)].iloc[0]
        
        diff_ing = abs(s_ing - gold_row['ingresos_totales'])
        diff_gas = abs(s_gas - gold_row['gastos_totales'])
        diff_flujo = abs(s_flujo - gold_row['flujo_neto'])
        
        if diff_ing < 0.01 and diff_gas < 0.01 and diff_flujo < 0.01:
            st.success("✅ CONCILIACIÓN EXITOSA BBVA: La suma de transacciones en Silver coincide exactamente con el registro consolidado en Gold.")
        else:
            st.error("❌ DISCREPANCIA DETECTADA: Existen diferencias numéricas entre Silver y Gold.")

        st.table(pd.DataFrame({
            "Métrica": ["Ingresos", "Gastos", "Flujo Neto"],
            "Silver (Suma Directa)": [f"${s_ing:,.2f}", f"${s_gas:,.2f}", f"${s_flujo:,.2f}"],
            "Gold (Consolidado)": [f"${gold_row['ingresos_totales']:,.2f}", f"${gold_row['gastos_totales']:,.2f}", f"${gold_row['flujo_neto']:,.2f}"],
            "Diferencia": [f"${diff_ing:,.2f}", f"${diff_gas:,.2f}", f"${diff_flujo:,.2f}"]
        }))
        st.dataframe(silver_sub, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Se requieren archivos de Silver y Gold para la conciliación.")

elif selected_nav == "🛡️ Cuarentena":
    st.markdown("<h3 style='color: #ff6b6b;'>🛡️ Auditoría de Registros en Cuarentena</h3>", unsafe_allow_html=True)
    if not df_quarantine.empty:
        st.dataframe(df_quarantine, use_container_width=True, hide_index=True)
    else:
        st.info("Sin registros en cuarentena.")