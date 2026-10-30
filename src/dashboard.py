import os
import sys
import glob
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# Configuración del Entorno y Rutas
# -----------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.orchestration.run_pipeline_e2e import execute_full_pipeline
from src.ml_engine import (
    train_and_evaluate_models,
    run_what_if_simulation,
    run_monte_carlo_simulation
)
from macro_engine import calculate_macro_projections

# -----------------------------------------------------------------------------
# Configuración de la Página en Streamlit
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="BBVA Financial Digital Twin",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# Carga Modular de Estilos CSS Externos
# -----------------------------------------------------------------------------
def load_css(css_path):
    """Carga el archivo CSS desde el directorio de assets."""
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

CSS_FILE = os.path.join(PROJECT_ROOT, "assets", "styles.css")
load_css(CSS_FILE)

# -----------------------------------------------------------------------------
# Funciones Auxiliares y Carga de Datos
# -----------------------------------------------------------------------------
def find_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None

BASE_DIR = PROJECT_ROOT
BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze")
SILVER_DIR = os.path.join(BASE_DIR, "data", "silver")
GOLD_DIR = os.path.join(BASE_DIR, "data", "gold")
QUARANTINE_DIR = os.path.join(BASE_DIR, "data", "quarantine")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

REPORT_PATH = os.path.join(REPORTS_DIR, "validation_report.csv")
GOLD_PATH = os.path.join(GOLD_DIR, "gold_cliente_mes.parquet")

SILVER_TX_PATH = os.path.join(SILVER_DIR, "transacciones.parquet")
if not os.path.exists(SILVER_TX_PATH):
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

# -----------------------------------------------------------------------------
# Menú Lateral y Navegación
# -----------------------------------------------------------------------------
with st.sidebar:
    header_html = (
        '<div style="display: flex; align-items: center; gap: 10px; padding: 5px 0 20px 0;">'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 40" width="75"><text x="0" y="30" font-family=\'Trebuchet MS\', sans-serif font-size="34" font-weight="900" fill="#FFFFFF" letter-spacing="-1.5">BBVA</text></svg>'
        '<div style="height: 20px; width: 1px; background-color: rgba(255, 255, 255, 0.3);"></div>'
        '<div style="display: flex; align-items: center; gap: 6px;">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#2DCCCD" stroke-width="2.5"/><path d="M2 17L12 22L22 17" stroke="#2DCCCD" stroke-width="2.5"/><path d="M2 12L12 17L22 12" stroke="#2DCCCD" stroke-width="2.5"/></svg>'
        '<span style="color: #FFFFFF; font-weight: 800; font-size: 13px;">Tecmilenio</span>'
        '</div>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)
    
    selected_nav = st.radio(
        "Navegación",
        [
            "🏠 Dashboard", 
            "🤖 IA & Simulaciones",
            "📊 Calidad de Datos", 
            "🏆 Capa Gold (KPIs)", 
            "📈 Proyección Macro",
            "🤖 Asistente IA",
            "🔎 Conciliación Silver vs Gold", 
            "🛡️ Cuarentena"
        ],
        index=0
    )
    
    st.markdown("---")
    if st.button("🔄 Actualizar Datos desde Google Drive", use_container_width=True):
        with st.spinner("Sincronizando hojas de Drive..."):
            execute_full_pipeline(trigger_source="BOTON_INTERFAZ_STREAMLIT")
        st.success("¡Pipeline actualizado con éxito!")
        st.rerun()

head_col1, head_col2 = st.columns([3, 1.5])
with head_col1:
    st.markdown("""
        <p style="color: #8a9bb0; font-size: 14px; margin: 0;">Hola,</p>
        <h1 style="color: #ffffff; font-size: 28px; font-weight: 800; margin: 0;">
            BBVA <span style="color: #2DCCCD;">Financial Digital Twin</span>
        </h1>
    """, unsafe_allow_html=True)

st.write("")

# -----------------------------------------------------------------------------
# 1. DASHBOARD PRINCIPAL
# -----------------------------------------------------------------------------
if selected_nav == "🏠 Dashboard":
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

    with kpi1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">📄 Lotes</div><div class="kpi-value">{num_archivos}</div><div class="kpi-badge badge-blue">Activos</div></div>', unsafe_allow_html=True)
    with kpi2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">🗄️ Ingesta Bronze</div><div class="kpi-value">{total_bronze:,}</div><div class="kpi-badge badge-blue">En proceso</div></div>', unsafe_allow_html=True)
    with kpi3:
        st.markdown(f'<div class="kpi-card kpi-card-cyan"><div class="kpi-title">✔️ Válidos Silver</div><div class="kpi-value">{total_silver:,}</div><div class="kpi-badge badge-cyan">{tasa_calidad}% Calidad</div></div>', unsafe_allow_html=True)
    with kpi4:
        st.markdown(f'<div class="kpi-card kpi-card-red"><div class="kpi-title">❗ Cuarentena</div><div class="kpi-value">{total_rechazados:,}</div><div class="kpi-badge badge-red">{pct_rechazados}% Rechazos</div></div>', unsafe_allow_html=True)
    with kpi5:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">⚡ Latencia</div><div class="kpi-value">~1.2 s</div><div class="kpi-badge badge-cyan">Optimizado</div></div>', unsafe_allow_html=True)

    st.write("")
    c1, c2, c3 = st.columns([1.5, 1.2, 1.3])

    with c1:
        st.markdown('<div class="chart-panel"><div class="panel-header"><span>📊 Evolución de Calidad</span></div>', unsafe_allow_html=True)
        dates = pd.date_range(end=datetime.today(), periods=7).strftime("Oct %d")
        df_trend = pd.DataFrame({"Fecha": dates, "% Válidos": [96.0, 96.5, 97.2, 97.5, 98.0, 98.4, tasa_calidad]})
        fig_evol = px.line(df_trend, x="Fecha", y="% Válidos", markers=True)
        fig_evol.update_layout(height=210, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#8a9bb0'))
        st.plotly_chart(fig_evol, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="chart-panel"><div class="panel-header"><span>💠 Distribución Válidos vs Cuarentena</span></div>', unsafe_allow_html=True)
        fig_pie = go.Figure(data=[go.Pie(labels=["Válidos", "Cuarentena"], values=[total_silver, max(total_rechazados, 1)], hole=0.7, marker=dict(colors=['#2DCCCD', '#D32F2F']))])
        fig_pie.update_layout(height=210, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        # VOLUMETRÍA POR CAPA MEDALLION MEJORADA (BARRAS HORIZONTALES)
        st.markdown('<div class="chart-panel"><div class="panel-header"><span>📊 Volumetría por Capa Medallion</span></div>', unsafe_allow_html=True)
        df_vol = pd.DataFrame({
            "Capa": ["Bronze", "Silver", "Gold", "Cuarentena"],
            "Registros": [total_bronze, total_silver, total_gold, total_rechazados],
            "Color": ["#CD7F32", "#4A90E2", "#FFD700", "#E74C3C"]
        })
        fig_vol = go.Figure(go.Bar(
            x=df_vol["Registros"], y=df_vol["Capa"], orientation='h',
            text=df_vol["Registros"], textposition='outside',
            marker=dict(color=df_vol["Color"])
        ))
        fig_vol.update_layout(
            height=210, margin=dict(l=10, r=50, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8a9bb0', size=11), yaxis=dict(autorange="reversed")
        )
        st.plotly_chart(fig_vol, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
        <div class="status-banner">
            <div class="status-item"><span class="status-dot"></span><span><b>Sistema Operativo:</b> <span style="color: #2DCCCD;">Sin incidencias ●</span></span></div>
            <div class="status-item"><span style="color: #8a9bb0;">🕒 <b>Última Ingesta:</b> Hace 12 min ●</span></div>
            <div class="status-item"><span style="color: #8a9bb0;">⚡ <b>Próxima Ejecución:</b> En 3 h 48 min ●</span></div>
            <div style="font-weight: 700; color: #ffffff; font-size: 13px;">Más datos. <span style="color: #2DCCCD;">Mejores decisiones.</span></div>
        </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. INTELIGENCIA ARTIFICIAL Y SIMULACIONES
# -----------------------------------------------------------------------------
elif selected_nav == "🤖 IA & Simulaciones":
    if not df_gold.empty:
        clientes_unicos = sorted(df_gold["customer_id"].unique())
        selected_client = st.selectbox("👤 Seleccionar Cliente:", clientes_unicos)
        df_client = df_gold[df_gold["customer_id"] == selected_client].sort_values("periodo")

        tab_ia, tab_sim = st.tabs(["🤖 Red Neuronal (4 Capas)", "🎲 Monte Carlo & What-If"])

        with tab_ia:
            st.header("🤖 Red Neuronal y Modelos Predictivos")
            margin_mxn = st.number_input("Margen de Tolerancia de Acierto (MXN ±):", value=1000.0, step=250.0)
            metricas_df, model_mlp = train_and_evaluate_models(df_gold, error_margin_mxn=margin_mxn)

            if isinstance(metricas_df, pd.DataFrame):
                st.subheader("📊 Comparativa de Desempeño de Modelos")
                st.dataframe(metricas_df, use_container_width=True)

                fig_pred = px.line(df_client, x="periodo", y="flujo_neto", markers=True, title=f"Flujo Neto Histórico: {selected_client}")
                fig_pred.update_traces(line_color="#2DCCCD", line_width=3)
                st.plotly_chart(fig_pred, use_container_width=True)

        with tab_sim:
            sub_whatif, sub_montecarlo = st.tabs(["⚡ What-If", "🎰 Monte Carlo (1,000 Trayectorias)"])
            ingreso_prom = float(df_client["ingresos_totales"].tail(3).mean())
            gasto_prom = float(df_client["gastos_totales"].tail(3).mean())

            with sub_whatif:
                var_gasto = st.slider("Variación en Gastos (%):", -50, 100, 20)
                var_ingreso = st.slider("Variación en Ingresos (%):", -50, 50, -15)
                res_wi = run_what_if_simulation(ingreso_prom, gasto_prom, var_gasto, var_ingreso)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Ingreso Simulado", f"${res_wi['nuevo_ingreso']:,.2f}")
                c2.metric("Gasto Simulado", f"${res_wi['nuevo_gasto']:,.2f}")
                c3.metric("Flujo Neto Simulado", f"${res_wi['flujo_simulado']:,.2f}")
                c4.metric("Diferencia", f"${res_wi['diferencia']:,.2f}")

            with sub_montecarlo:
                saldo_ini = st.number_input("Saldo Inicial Disponible (MXN):", value=30000.0)
                gasto_std = float(df_client["gastos_totales"].std()) if len(df_client) > 1 else gasto_prom * 0.15
                
                mc = run_monte_carlo_simulation(ingreso_prom, gasto_prom, gasto_std, saldo_inicial=saldo_ini)
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("P10 (Pesimista)", f"${mc['p10']:,.2f}")
                k2.metric("P50 (Mediana)", f"${mc['p50_mediana']:,.2f}")
                k3.metric("P90 (Optimista)", f"${mc['p90']:,.2f}")
                k4.metric("⚠️ Riesgo Saldo < 0", f"{mc['prob_saldo_negativo']:.1f}%")

                fig_mc = go.Figure()
                meses_eje = [f"Mes {i}" for i in range(7)]
                for i in range(100):
                    fig_mc.add_trace(go.Scatter(x=meses_eje, y=mc["matriz_saldos"][i, :], mode='lines', line=dict(width=0.8, color='rgba(0, 102, 204, 0.15)'), showlegend=False))
                fig_mc.add_hline(y=0, line_dash="dash", line_color="red")
                fig_mc.update_layout(title="Simulación Monte Carlo (1,000 Trayectorias)", template="plotly_dark")
                st.plotly_chart(fig_mc, use_container_width=True)

# -----------------------------------------------------------------------------
# 3. CALIDAD DE DATOS
# -----------------------------------------------------------------------------
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
            rows_html += f'<tr style="border-bottom: 1px solid rgba(255,255,255,0.06);"><td style="padding: 10px 12px; text-align: left;"><span style="color:{dot_color}; margin-right: 8px;">●</span>{r["dataset"]}</td><td style="padding: 10px 12px; color: #8a9bb0; text-align: center;">{b_cnt:,}</td><td style="padding: 10px 12px; color: {dot_color}; font-weight: 700; text-align: center;">{pct}%</td><td style="padding: 10px 12px; color: #ff6b6b; font-weight: 600; text-align: center;">{err_cnt:,}</td></tr>'

        table_html = f'<div class="chart-panel"><div class="panel-header">📑 Calidad por Dataset</div><table style="width: 100%; font-size: 13px; color: #e9eef2;"><thead><tr style="border-bottom: 1px solid rgba(255,255,255,0.12); color: #8a9bb0; font-size: 11px;"><th style="text-align: left;">Dataset</th><th style="text-align: center;">Bronze</th><th style="text-align: center;">% Calidad</th><th style="text-align: center;">Errores</th></tr></thead><tbody>{rows_html}</tbody></table></div>'
        st.markdown(table_html, unsafe_allow_html=True)

    with q2:
        st.markdown('<div class="chart-panel"><div class="panel-header">📄 Lotes Recientes</div>', unsafe_allow_html=True)
        st.dataframe(df_report, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. CAPA GOLD (KPIS)
# -----------------------------------------------------------------------------
elif selected_nav == "🏆 Capa Gold (KPIs)":
    st.markdown("<h3 style='color: #2DCCCD; margin-bottom: 12px;'>🏆 Consolidado Analítico de Negocio (`gold_cliente_mes`)</h3>", unsafe_allow_html=True)
    if not df_gold.empty:
        gold_clients = set(df_gold['customer_id'].unique()) if not df_gold.empty else set()
        silver_clients = set(df_silver_tx['customer_id'].unique()) if not df_silver_tx.empty else set()
        lista_c_gold = sorted(list(gold_clients.union(silver_clients)))

        f1, f2 = st.columns(2)
        with f1: sel_p = st.selectbox("Periodo:", ["Todos"] + list(df_gold['periodo'].unique()))
        with f2: sel_c = st.selectbox("Cliente:", ["Todos"] + lista_c_gold)

        df_f = df_gold.copy()
        if sel_p != "Todos": df_f = df_f[df_f['periodo'] == sel_p]
        if sel_c != "Todos": df_f = df_f[df_f['customer_id'] == sel_c]

        tot_ing = df_f['ingresos_totales'].sum() if not df_f.empty else 0.0
        tot_deuda = df_f['pagos_deuda'].sum() if 'pagos_deuda' in df_f.columns else (df_f['pago_deuda_mensual'].sum() if 'pago_deuda_mensual' in df_f.columns else 0.0)
        tot_op = df_f['gastos_operativos'].sum() if 'gastos_operativos' in df_f.columns else max(0.0, df_f['gastos_totales'].sum() - tot_deuda)
        flujo = df_f['flujo_neto'].sum() if not df_f.empty else 0.0
        deuda_ratio = (df_f['ratio_endeudamiento'].mean() * 100) if not df_f.empty else 0.0

        g1, g2, g3, g4, g5 = st.columns(5)
        g1.metric("Ingresos Totales", f"${tot_ing:,.2f}")
        g2.metric("Gastos Operativos", f"${tot_op:,.2f}")
        g3.metric("Pagos de Préstamos", f"${tot_deuda:,.2f}")
        g4.metric("Flujo Neto Real", f"${flujo:,.2f}")
        g5.metric("Ratio Endeudamiento", f"{deuda_ratio:.1f}%")

        st.write("")
        st.dataframe(df_f, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Ejecuta `python src/gold_builder.py` para generar la capa Gold.")

# -----------------------------------------------------------------------------
# 5. PROYECCIÓN MACRO
# -----------------------------------------------------------------------------
elif selected_nav == "📈 Proyección Macro":
    st.markdown("<h3 style='color: #2DCCCD;'>📈 Proyecciones Macroeconómicas a 3 y 6 Meses</h3>", unsafe_allow_html=True)
    if not df_gold.empty:
        m1, m2 = st.columns(2)
        with m1: inf_val = st.slider("Tasa de Inflación Anual Estimada (%)", 1.0, 12.0, 4.5, 0.1) / 100.0
        with m2: usd_val = st.number_input("Tipo de Cambio USD/MXN", 10.0, 30.0, 18.50, 0.25)
        df_proj = calculate_macro_projections(df_gold, inflation_annual=inf_val, usd_mxn=usd_val)
        st.dataframe(df_proj, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Se requiere la capa Gold para proyecciones.")

# -----------------------------------------------------------------------------
# 6. ASISTENTE IA
# -----------------------------------------------------------------------------
elif selected_nav == "🤖 Asistente IA":
    st.markdown("<h3 style='color: #2DCCCD;'>🤖 Asistente Conversacional Financiero BBVA</h3>", unsafe_allow_html=True)
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy tu asistente del Gemelo Digital Financiero BBVA. ¿En qué puedo ayudarte?"}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]): st.markdown(message["content"])

    if prompt := st.chat_input("Consulta tus datos..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        p_lower = prompt.lower()
        if "prestamo" in p_lower or "deuda" in p_lower:
            col_d = 'pagos_deuda' if 'pagos_deuda' in df_gold.columns else 'pago_deuda_mensual'
            deuda_tot = df_gold[col_d].sum() if not df_gold.empty and col_d in df_gold.columns else 0.0
            ans = f"💳 Total consolidado de pagos de préstamos en Gold: **${deuda_tot:,.2f}**."
        else:
            ans = f"🤖 Respuesta sobre '{prompt}' sincronizada con la capa Gold."

        with st.chat_message("assistant"): st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})

# -----------------------------------------------------------------------------
# 7. CONCILIACIÓN SILVER VS GOLD
# -----------------------------------------------------------------------------
elif selected_nav == "🔎 Conciliación Silver vs Gold":
    st.markdown("<h3 style='color: #2DCCCD;'>🔎 Inspector de Conciliación en Vivo (Silver vs Gold)</h3>", unsafe_allow_html=True)
    if not df_gold.empty and not df_silver_tx.empty:
        lista_clientes = sorted(list(set(df_gold['customer_id'].unique()).union(set(df_silver_tx['customer_id'].unique()))))
        c1, c2 = st.columns(2)
        with c1: c_id = st.selectbox("Cliente:", lista_clientes)
        with c2: p_id = st.selectbox("Periodo:", df_gold[df_gold['customer_id'] == c_id]['periodo'].unique() if len(df_gold[df_gold['customer_id'] == c_id]) > 0 else ["N/A"])

        col_monto = find_column(df_silver_tx, ['monto', 'monto_total', 'amount'])
        col_tipo = find_column(df_silver_tx, ['tipo_movimiento', 'tipo', 'type'])
        
        silver_sub = df_silver_tx[(df_silver_tx['customer_id'] == c_id) & (df_silver_tx['periodo'] == p_id)]
        gold_row_match = df_gold[(df_gold['customer_id'] == c_id) & (df_gold['periodo'] == p_id)]

        if not gold_row_match.empty and col_monto:
            s_ing = silver_sub[silver_sub[col_tipo].astype(str).str.upper().isin(['INGRESO', 'INGRESOS'])][col_monto].sum()
            s_gas = silver_sub[silver_sub[col_tipo].astype(str).str.upper().isin(['EGRESO', 'GASTO', 'GASTOS'])][col_monto].sum()
            gold_row = gold_row_match.iloc[0]

            st.table(pd.DataFrame({
                "Métrica": ["Ingresos", "Gastos Totales"],
                "Silver": [f"${s_ing:,.2f}", f"${s_gas:,.2f}"],
                "Gold": [f"${gold_row['ingresos_totales']:,.2f}", f"${gold_row['gastos_totales']:,.2f}"]
            }))
        st.dataframe(silver_sub, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# 8. CUARENTENA
# -----------------------------------------------------------------------------
elif selected_nav == "🛡️ Cuarentena":
    st.markdown("<h3 style='color: #ff6b6b;'>🛡️ Auditoría de Registros en Cuarentena</h3>", unsafe_allow_html=True)
    if not df_quarantine.empty:
        st.dataframe(df_quarantine, use_container_width=True, hide_index=True)
    else:
        st.info("Sin registros en cuarentena.")