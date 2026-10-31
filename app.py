"""Seawater Desalination: Thermodynamic Performance Analyzer.

Reproducible educational application based on the user's experiment datasets.
Run: python -m streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path
import io
import zipfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from models import (
    FEED_DENSITY, osmotic_pressure_nacl, minimum_work_nacl,
    interpolate_phreeqc, ro_model, med_model,
)

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
ASSETS = BASE / "assets"
NAVY, TEAL, CYAN, MUTED, AMBER, RED = "#152A40", "#007F86", "#24A2B4", "#6E8293", "#E99B36", "#DA6572"

st.set_page_config(page_title="Seawater Desalination | Thermodynamic Analyzer",
                   page_icon="🌊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  .stApp {background: #F7FAFC;}
  header[data-testid="stHeader"] {background: #F7FAFC;}
  [data-testid="stSidebar"] {background: #EEF5F8; border-right: 1px solid #DDE9EF;}
  div[data-testid="stMetric"] {padding: 16px 18px; background: white; border: 1px solid #E2EAF1; border-radius: 15px; box-shadow: 0 3px 14px rgba(10,40,60,.035);}
  div[data-testid="stMetricLabel"] {font-weight:600; color:#688096;}

div[data-testid="stMetricValue"] {
    color: #142A40;
    font-size: clamp(1.35rem, 2vw, 1.9rem);
    white-space: nowrap;
}
div[data-testid="stMetric"] {
    min-width: 0;
}
  .hero {border-radius:22px; padding:32px 35px; margin:4px 0 22px; color:white;
         background:linear-gradient(114deg,#112B42 0%,#145269 56%,#00868D 100%);
         box-shadow:0 16px 40px rgba(20,60,80,.14);}
  .hero .eyebrow {font-size:12px; font-weight:800; letter-spacing:2px; color:#8CE0DC;}
  .hero h1 {font-size:2.15rem; color:white; line-height:1.14; margin:12px 0 8px; letter-spacing:-.5px;}
  .hero p {color:#C6E2E9; max-width:800px; font-size:1rem; margin-bottom:0;}
  .section-kicker {text-transform:uppercase; font-size:12px; font-weight:800; color:#007F86; letter-spacing:1.8px; margin:12px 0 2px;}
  .small-note {border-left:3px solid #43AAB2; background:#EDF5F6; padding:13px 16px;
               font-size:14px; color:#41596C; border-radius:0 9px 9px 0; margin:12px 0;}
  .flow-card {background:#fff; border:1px solid #E0E9EF; border-radius:15px; text-align:center;
              padding:18px 8px; min-height:100px;}
  .flow-card h4 {margin:5px 0; color:#16394A; font-size:17px;}
  .flow-card p {margin:0; font-size:13px; color:#6B7F91;}
  .text-muted {color:#6E8293;}
  h1,h2,h3 {letter-spacing:-.3px;}
  [data-testid="stTabs"] button p {font-weight:700;}
  div[data-testid="stDataFrame"] {border-radius:11px; overflow:hidden;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def read_data(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)

exp1 = read_data("Experiment_1_Results.csv")
refcase = read_data("Seawater_Reference_Case.csv")
ph = read_data("PHREEQC_Recovery_Results.csv").sort_values("Recovery (%)")
modelcmp = read_data("Exp3_Model_Comparison.csv")
mit = read_data("MIT_PHREEQC_Validation.csv")
robase = read_data("Experiment_4_RO_Energy_Results.csv")
medbase = read_data("Experiment_5_RO_vs_MED.csv")


def section(eyebrow: str, heading: str, explanation: str = ""):
    st.markdown(f'<p class="section-kicker">{eyebrow}</p>', unsafe_allow_html=True)
    st.subheader(heading)
    if explanation:
        st.caption(explanation)


def format_chart(fig: go.Figure, yaxis: str | None = None, height: int = 350) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=15, t=38, b=18),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Arial, sans-serif", color=NAVY, size=12),
                      legend=dict(orientation="h", yanchor="bottom", y=1.025, x=0),
                      hovermode="x unified", colorway=[TEAL, AMBER, CYAN, RED],
                      xaxis=dict(showline=True, linecolor="#D6E2EA", gridcolor="#E6EDF2", zeroline=False),
                      yaxis=dict(showline=False, gridcolor="#E6EDF2", zeroline=False))
    if yaxis:
        fig.update_yaxes(title_text=yaxis)
    return fig


def plot(fig: go.Figure, key: str):
    st.plotly_chart(fig, width="stretch", key=key, config={"displaylogo": False, "scrollZoom": False})


def artifact_image(path: str, caption: str):
    file = ASSETS / path
    if file.exists():
        st.image(str(file), caption=caption, use_container_width=True)


def download_data(df: pd.DataFrame, filename: str, label: str = "Download table as CSV"):
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=filename,
                       mime="text/csv", key=f"dl-{filename}")


def work_reference(s: int, r: int):
    if s == 35:
        return interpolate_phreeqc(ph, r, "Minimum Work (kWh/m3)"), "PHREEQC-derived work · lookup/interpolated"
    return minimum_work_nacl(s, r/100), "Simplified NaCl · recalculated"


# ---- Sidebar: all inputs, independent of individual tabs ----
with st.sidebar:
    st.markdown("### 🌊 BlueEnergy Lab")
    st.caption("IIT Indore · Chemical Engineering")
    st.divider()
    st.markdown("**Seawater feed & recovery**")
    salinity = st.slider("Feed salinity (g/kg)", 20, 50, 35, 5,
                         help="PHREEQC data are only available at the original 35 g/kg feed.")
    recovery = st.slider("Target mass recovery (%)", 10, 60, 50, 10)
    feed_flow = st.number_input("Feed flow (m³/h)", min_value=10.0, max_value=1000.0, value=100.0, step=10.0)
    st.divider()
    st.markdown("**Reverse osmosis**")
    pressure = st.slider("Applied RO pressure (bar)", 60, 90, 70, 1)
    pump_eff = st.slider("Pump efficiency (%)", 60, 95, 80, 5)
    erd_eff = st.slider("Turbine energy recovery (%)", 40, 95, 85, 5)
    st.divider()
    with st.expander("MED scenario settings"):
        med_heat = st.slider("MED heat (kWhth/m³)", 40, 120, 60, 5)
        med_electricity = st.slider("MED electricity (kWh/m³)", 1.0, 4.0, 2.2, 0.1)
        source_temp = st.slider("Heat-source temperature (°C)", 55, 95, 70, 5)
    st.caption("Reference case: 35 g/kg · 25°C · 50% recovery · 100 m³/h")

r = recovery/100
ro = ro_model(feed_flow, r, pressure, pump_eff/100, erd_eff/100, feed_salinity_gkg=salinity)
med = med_model(med_heat, med_electricity, source_temp)
w_min, work_source = work_reference(salinity, recovery)
eta_ro_off = 100 * w_min / ro.sec_without
eta_ro_on = 100 * w_min / ro.sec_with
eta_med = 100 * w_min / med.total_exergy_kwh_m3
brine_salinity = salinity / (1-r)
pi_brine = (interpolate_phreeqc(ph, recovery, "Osmotic Pressure (bar)")
            if salinity == 35 else osmotic_pressure_nacl(brine_salinity))
pressure_margin = ro.p_brine_bar - pi_brine

st.markdown('''<div class="hero"><div class="eyebrow">THERMODYNAMIC ENGINEERING · INTERACTIVE CASE STUDY</div>
<h1>Seawater Desalination<br>Performance Analyzer</h1>
<p>From molecular thermodynamics to process energy: explore five experiments, real PHREEQC outputs,
model comparisons, reverse-osmosis energy recovery, and RO–MED exergy trade-offs.</p></div>''', unsafe_allow_html=True)

if salinity != 35:
    st.info("**Property-model scope:** PHREEQC was simulated for a 35 g/kg feed only. For this alternate salinity, the dashboard uses the simplified non-ideal NaCl model for minimum work and brine osmotic pressure. It does not invent new PHREEQC results.")
if pressure_margin <= 0:
    st.error(f"**Potentially infeasible RO setting:** modeled brine pressure ({ro.p_brine_bar:.1f} bar) is not above the estimated brine osmotic pressure ({pi_brine:.1f} bar). Pump-energy results remain a fixed-recovery hypothetical, not evidence that the membrane can produce this water flow.")
elif pressure_margin < 8:
    st.warning(f"**Limited membrane pressure margin:** only {pressure_margin:.1f} bar between brine pressure and estimated osmotic pressure. Membrane flux and feasible recovery were not solved.")

k1,k2,k3,k4 = st.columns(4)

k1.metric(
    "Min. work (kWh/m³)",
    f"{w_min:.3f}",
    help=work_source
)

k2.metric(
    "RO SEC · no ERD (kWh/m³)",
    f"{ro.sec_without:.2f}"
)

k3.metric(
    "RO SEC · with ERD (kWh/m³)",
    f"{ro.sec_with:.2f}"
)

k4.metric(
    "Energy savings (%)",
    f"{ro.savings_pct:.1f}"
)

st.caption(f"Live scenario · {salinity} g/kg · {recovery}% mass recovery · {pressure} bar · {work_source}. RO values use the simplified fixed-recovery hydraulic model.")

pages = st.tabs(["🏠 Overview", "01 · Salinity", "02 · Recovery", "03 · Seawater models", "04 · RO energy", "05 · RO vs MED", "📁 Data & methods"])

with pages[0]:
    section("The system", "One consistent reference plant", "Your original 100 m³/h case is the reference; sliders explore conditional scenarios.")
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown(f'<div class="flow-card"><div style="font-size:24px">🌊</div><h4>Seawater feed</h4><p>{feed_flow:.1f} m³/h · {salinity} g/kg · 25°C</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="flow-card"><div style="font-size:24px">⚙️</div><h4>RO system</h4><p>High-pressure pump · membrane · optional brine turbine</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="flow-card"><div style="font-size:24px">💧</div><h4>Products</h4><p>{ro.q_permeate:.1f} m³/h permeate · {ro.q_brine:.1f} m³/h brine</p></div>', unsafe_allow_html=True)
    st.markdown('''<div class="small-note">The app prescribes mass recovery and approximates stream densities. It does <b>not</b> solve membrane flux or predict whether the target is achievable at a given pressure.</div>''', unsafe_allow_html=True)
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        section("Live energy balance", "Where the pump energy goes")
        f = go.Figure()
        f.add_trace(go.Bar(name="Pump input", x=["Pump", "Net without ERD", "Net with ERD"],
                           y=[ro.pump_kw, ro.net_without_kw, ro.net_with_kw], marker_color=[NAVY, CYAN, TEAL],
                           text=[f"{v:.1f} kW" for v in [ro.pump_kw, ro.net_without_kw, ro.net_with_kw]], textposition="outside"))
        format_chart(f, "Electrical power (kW)", 350)
        f.update_layout(showlegend=False)
        plot(f, "overview_power")
    with right:
        section("Mass balance", "Product streams")
        f = go.Figure(go.Pie(labels=["Permeate", "Brine"],
                             values=[ro.permeate_mass_kg_h, ro.brine_mass_kg_h],
                             hole=.70, marker_colors=[TEAL, "#D1E5ED"],
                             textinfo="percent+label", sort=False))
        format_chart(f, height=350)
        f.update_layout(showlegend=False, annotations=[dict(text=f"{ro.feed_mass_kg_h:,.0f}<br>kg/h", x=.5, y=.5, showarrow=False, font=dict(size=20, color=NAVY))])
        plot(f, "overview_mass")
    st.markdown("#### The five experiments")
    for name, detail in [
        ("01 · Salt concentration", "What happens to minimum work as feed salinity increases?"),
        ("02 · Water recovery", "What happens as more fresh water is extracted?"),
        ("03 · Seawater thermodynamics", "How do a simplified NaCl model, multicomponent PHREEQC and MIT compare?"),
        ("04 · Reverse osmosis", "How much hydraulic power can a brine turbine recover?"),
        ("05 · RO vs MED", "How do electrical and thermal inputs compare on a second-law basis?")]:
        st.markdown(f"**{name}** — {detail}")

with pages[1]:
    section("Experiment 01", "Effect of feed salinity on minimum separation work", "Source: original Experiment_1_Results.csv + original simplified NaCl equation.")
    c1,c2 = st.columns([1.5,1], gap="large")
    with c1:
        f=go.Figure()
        for s in sorted(exp1['Feed Salinity (g/kg)'].unique()):
            sub=exp1[exp1['Feed Salinity (g/kg)']==s]
            f.add_trace(go.Scatter(x=sub['Recovery (%)'], y=sub['Minimum Work (kWh/m3)'],
                                   name=f"{s:g} g/kg", mode="lines+markers", line=dict(width=2)))
        f.update_xaxes(title_text="Recovery (%)")
        format_chart(f, "Minimum work (kWh/m³)", 410)
        plot(f,"exp1_curves")
    with c2:
        st.markdown("#### Selected recovery comparison")
        s_grid = np.linspace(10,70,90)
        w_grid = [minimum_work_nacl(s, r) for s in s_grid]
        f=go.Figure(go.Scatter(x=s_grid,y=w_grid,mode="lines",line=dict(color=TEAL,width=3),name="Simplified non-ideal NaCl"))
        f.add_vline(x=salinity, line_dash="dot", line_color=AMBER)
        f.update_xaxes(title_text="Feed salinity (g/kg)")
        format_chart(f, "Work (kWh/m³)", 315)
        plot(f,"exp1_salinity")
        st.metric("Work at selected salinity", f"{minimum_work_nacl(salinity,r):.3f} kWh/m³")
        st.caption(f"Calculated at {recovery}% recovery. For 35 g/kg PHREEQC work, see Experiment 3.")
    with st.expander("Numerical data · original experiment"):
        st.dataframe(exp1, width="stretch", hide_index=True)
        download_data(exp1,"Experiment_1_Results.csv")
    st.info("Interpretation: higher feed salinity increases osmotic pressure and theoretical minimum-work estimates. The analytical model assumes NaCl-only chemistry, complete salt rejection, and constant density.")

with pages[2]:
    section("Experiment 02", "What happens as freshwater recovery increases?", "PHREEQC and simplified NaCl predictions at the reference feed salinity of 35 g/kg.")
    c1,c2=st.columns([1.35,1],gap="large")
    with c1:
        f=go.Figure()
        f.add_trace(go.Scatter(x=modelcmp['Recovery (%)'], y=modelcmp['NaCl Model (kWh/m3)'],
                               mode="lines+markers",line=dict(color=AMBER,width=3), name="Simplified NaCl"))
        f.add_trace(go.Scatter(x=modelcmp['Recovery (%)'], y=modelcmp['PHREEQC Model (kWh/m3)'],
                               mode="lines+markers",line=dict(color=TEAL,width=3), name="PHREEQC mixture"))
        f.add_vline(x=recovery,line_dash="dot",line_color="#8394A4")
        f.update_xaxes(title_text="Target mass recovery (%)")
        format_chart(f,"Approx. minimum work (kWh/m³)",400)
        plot(f,"recovery_work")
    with c2:
        f=go.Figure(go.Scatter(x=ph['Recovery (%)'],y=ph['Water Activity'],mode="lines+markers",name="PHREEQC a₍w₎",line=dict(color=TEAL,width=3)))
        f.update_xaxes(title_text="Recovery (%)")
        format_chart(f,"Water activity",315)
        plot(f,"recovery_activity")
        st.markdown("**Why it rises:** extracting fresh water concentrates the remaining brine. Water activity falls, osmotic pressure rises, and the reversible work per unit product increases.")
    with st.expander("See original recovery dataset"):
        st.dataframe(ph, width="stretch", hide_index=True)
        download_data(ph,"PHREEQC_Recovery_Results.csv")
    st.caption("PHREEQC data are from seven actual external simulation points (0%, 10%, …, 60%); connecting curves are for visualization. Apparent minimum work was obtained separately by numerical integration.")

with pages[3]:
    section("Experiment 03", "Real seawater chemistry: three levels of modeling", "Aqueous chemistry simulated in USGS PHREEQC with pitzer.dat; independent MIT osmotic-pressure correlation comparison.")
    col1,col2,col3=st.columns(3)
    col1.metric("Initial water activity", f"{ph['Water Activity'].iloc[0]:.5f}")
    col2.metric("Initial ionic strength",f"{ph['Ionic Strength (mol/kg)'].iloc[0]:.3f} mol/kg")
    col3.metric("MIT vs PHREEQC mean difference",f"{mit['Difference (%)'].abs().mean():.3f}%")
    left,right=st.columns([1.2,1],gap="large")
    with left:
        f=go.Figure()
        f.add_trace(go.Scatter(x=mit['Salinity (g/kg)'],y=mit['PHREEQC (bar)'],name="PHREEQC Pitzer · uploaded run",mode="lines+markers",line=dict(color=TEAL,width=3)))
        f.add_trace(go.Scatter(x=mit['Salinity (g/kg)'],y=mit['MIT Approx. (bar)'],name="MIT approximation · uploaded analysis",mode="lines+markers",line=dict(color=AMBER,dash="dash",width=2)))
        f.update_xaxes(title_text="Brine salinity (g/kg)")
        format_chart(f,"Osmotic pressure (bar)",390)
        plot(f,"chem_validate")
    with right:
        f=go.Figure()
        f.add_trace(go.Scatter(x=ph['Recovery (%)'],y=ph['Osmotic Coefficient'],name="PHREEQC osmotic coefficient",mode="lines+markers",line=dict(color=TEAL,width=3)))
        f.update_xaxes(title_text="Recovery (%)")
        format_chart(f,"Osmotic coefficient",310)
        plot(f,"chem_phi")
        st.caption("At 50% recovery: simulated PHREEQC brine osmotic pressure is 55.47 bar. MIT-based approximate value is 55.21 bar.")
    st.markdown("#### Ideal vs simplified non-ideal vs simulated seawater")
    r_grid=np.arange(10,61,10,dtype=float)
    ideal_curve=np.array([minimum_work_nacl(35,x/100,ideal=True) for x in r_grid])
    nacl_curve=np.array([minimum_work_nacl(35,x/100) for x in r_grid])
    ph_curve=np.array([interpolate_phreeqc(ph,x,"Minimum Work (kWh/m3)") for x in r_grid])
    f=go.Figure()
    for name, vals, color, dash in [
        ("Ideal ionic NaCl (φ = 1)",ideal_curve,NAVY,"dot"),
        ("Simplified non-ideal NaCl",nacl_curve,AMBER,"solid"),
        ("PHREEQC multicomponent seawater",ph_curve,TEAL,"solid")]:
        f.add_trace(go.Scatter(x=r_grid,y=vals,name=name,mode="lines+markers",line=dict(color=color,width=3,dash=dash)))
    f.update_xaxes(title_text="Recovery (%)")
    format_chart(f,"Approx. minimum work (kWh/m³)",375)
    plot(f,"chem_three_models")
    st.markdown('''<div class="small-note"><b>Validation interpretation:</b> 0.245% is the mean absolute <b>model-to-model difference</b> for the seven points—not experimental measurement error. The MIT series uses the <i>approximate reproduction</i> from the original Colab notebook, not a direct MATLAB run. The models also differ in electrolyte representation.</div>''', unsafe_allow_html=True)
    with st.expander("View the uploaded model-comparison and MIT-validation tables"):
        st.write("**Simplified NaCl vs PHREEQC**")
        st.dataframe(modelcmp, hide_index=True, width="stretch")
        st.write("**MIT approximation vs PHREEQC**")
        st.dataframe(mit, hide_index=True, width="stretch")
        download_data(mit,"MIT_PHREEQC_Validation.csv")

with pages[4]:
    section("Experiment 04", "RO energy recovery: hydraulic engineering model", "Energy estimates respond to your sidebar settings. Recovery is imposed, not predicted by membrane transport.")
    a,b,c,d=st.columns(4)
    a.metric("High-pressure pump",f"{ro.pump_kw:.1f} kW")
    b.metric("Hydraulic recovery",f"{ro.recovered_kw:.1f} kW")
    c.metric("Net with turbine",f"{ro.net_with_kw:.1f} kW")
    d.metric("Savings vs no turbine",f"{ro.savings_pct:.1f}%")
    left,right=st.columns([1,1.1],gap="large")
    with left:
        f=go.Figure(go.Bar(x=["Without ERD","With brine turbine"],y=[ro.sec_without,ro.sec_with],
                           marker_color=[AMBER,TEAL],text=[f"{ro.sec_without:.2f}",f"{ro.sec_with:.2f}"],textposition="outside"))
        format_chart(f,"SEC (kWh/m³)",375)
        f.update_layout(showlegend=False)
        plot(f,"ro_compare")
    with right:
        pvals=np.linspace(60,90,61)
        rovals=[ro_model(feed_flow,r,float(p),pump_eff/100,erd_eff/100,feed_salinity_gkg=salinity) for p in pvals]
        f=go.Figure()
        f.add_trace(go.Scatter(x=pvals,y=[x.sec_without for x in rovals],mode="lines",name="No energy recovery",line=dict(color=AMBER,width=3)))
        f.add_trace(go.Scatter(x=pvals,y=[x.sec_with for x in rovals],mode="lines",name="Brine turbine",line=dict(color=TEAL,width=3)))
        f.add_vline(x=pressure,line_dash="dot",line_color=NAVY)
        f.update_xaxes(title_text="RO applied pressure (bar)")
        format_chart(f,"SEC (kWh/m³)",375)
        plot(f,"ro_pressure")
    st.markdown("#### Mass and energy check")
    stream_table=pd.DataFrame({"Stream":["Feed","Permeate","Brine"],
        "Mass flow (kg/h)":[ro.feed_mass_kg_h,ro.permeate_mass_kg_h,ro.brine_mass_kg_h],
        "Volumetric flow (m³/h)":[ro.q_feed,ro.q_permeate,ro.q_brine],
        "Salt content (g/kg)":[salinity,0,brine_salinity]})
    st.dataframe(stream_table.style.format({"Mass flow (kg/h)":"{:,.1f}","Volumetric flow (m³/h)":"{:,.2f}","Salt content (g/kg)":"{:.1f}"}),width="stretch",hide_index=True)
    st.caption(f"Pressure feasibility check: modeled brine pressure {ro.p_brine_bar:.1f} bar vs estimated brine osmotic pressure {pi_brine:.1f} bar. Margin = {pressure_margin:.1f} bar; a positive margin is necessary but not sufficient for feasible membrane flux.")
    st.info("**Device modeled:** hydraulic recovery turbine at a specified efficiency. It is not a pressure exchanger. Intake pumping, pretreatment, auxiliary equipment, concentration polarization, membrane transport and fouling are excluded.")
    ro_table=pd.DataFrame({"Configuration":["Without ERD","With turbine"],"Power (kW)":[ro.net_without_kw,ro.net_with_kw],"SEC (kWh/m³)":[ro.sec_without,ro.sec_with],"Second-law indicator (%)":[eta_ro_off,eta_ro_on]})
    download_data(ro_table,"RO_scenario_results.csv")

with pages[5]:
    section("Experiment 05", "RO versus MED · second-law screening", "Compare electricity with the work-potential (exergy) of a thermal heat source, not thermal kWh directly.")
    st.latex(r"Ex_{heat}=Q_{heat}\left(1-\frac{T_0}{T_h}\right),\qquad \eta_{II}=\frac{W_{min}}{Ex_{input}}\times100\%")
    labels=["RO · no turbine","RO · with turbine","MED · scenario"]
    exergies=[ro.sec_without,ro.sec_with,med.total_exergy_kwh_m3]
    efficiencies=[eta_ro_off,eta_ro_on,eta_med]
    left,right=st.columns(2,gap="large")
    with left:
        f=go.Figure(go.Bar(x=labels,y=exergies,marker_color=["#B6C7D3",TEAL,AMBER],text=[f"{x:.2f}" for x in exergies],textposition="outside"))
        format_chart(f,"Exergy input (kWh/m³)",365)
        f.update_layout(showlegend=False)
        plot(f,"med_exergy")
    with right:
        f=go.Figure(go.Bar(x=labels,y=efficiencies,marker_color=["#B6C7D3",TEAL,AMBER],text=[f"{x:.1f}%" for x in efficiencies],textposition="outside"))
        format_chart(f,"Conditional second-law efficiency (%)",365)
        f.update_layout(showlegend=False)
        plot(f,"med_efficiency")
    st.caption(f"MED scenario: {med_heat:.0f} kWhth/m³ heat at {source_temp}°C + {med_electricity:.1f} kWh/m³ electricity; assumed environment 25°C. Heat exergy = {med.heat_exergy_kwh_m3:.2f} kWh/m³.")
    section("Isolating one variable", "Heat-source temperature sensitivity")
    t_grid=np.linspace(55,95,81)
    eff=[100*w_min/med_model(med_heat,med_electricity,float(t)).total_exergy_kwh_m3 for t in t_grid]
    f=go.Figure(go.Scatter(x=t_grid,y=eff,mode="lines",line=dict(color=TEAL,width=3),name="MED scenario"))
    f.add_vline(x=source_temp,line_color=AMBER,line_dash="dash")
    f.update_xaxes(title_text="Heat source temperature (°C)")
    format_chart(f,"Conditional second-law efficiency (%)",300)
    plot(f,"med_temp")
    st.warning("**Interpretation boundary:** MED heat and electricity demands are assumed inputs, not predicted by a distillation model; temperature sensitivity holds them constant. This comparison does NOT prove RO is universally superior to MED. Heat-source availability and losses strongly affect practical performance.")
    combined=pd.DataFrame({"Process":labels,"Electricity (kWh/m³)":[ro.sec_without,ro.sec_with,med.electricity_kwh_m3],
                           "Heat (kWhth/m³)":[0,0,med.heat_kwhth_m3],"Exergy input (kWh/m³)":exergies,
                           "Second-law indicator (%)":efficiencies})
    st.dataframe(combined.style.format(precision=3),hide_index=True,width="stretch")
    download_data(combined,"RO_MED_scenario_results.csv")

with pages[6]:
    section("Reproducibility", "Data provenance & project files", "All included datasets are from the user's uploaded notebooks and simulation outputs.")
    a,b,c=st.columns(3)
    a.metric("Experiment themes", "5")
    b.metric("PHREEQC recovery points", len(ph))
    c.metric("MIT comparison points", len(mit))
    st.markdown("#### Model and source distinctions")
    st.markdown("""
- **PHREEQC Pitzer:** imported selected-output data from a representative multicomponent seawater simulation (25°C; 35 g/kg initial basis). No geochemical simulation is run inside Streamlit.
- **MIT comparison:** tabulated results from the uploaded notebook's *approximation* of `SW_OsmCoeff`/`SW_OsmPress`, not independently executed MATLAB code. Useful for model agreement, not experimental validation.
- **Simplified NaCl:** a concentration-dependent osmotic coefficient model reproduced from Experiment 1's Python code. It is a computational approximation, not the complete Pitzer electrolyte model.
- **RO:** a high-pressure pump plus *hydraulic recovery turbine* at imposed recovery. The membrane is not modeled using transport equations.
- **MED:** a constant-temperature heat-source exergy calculation using adjustable assumed thermal and electrical loads. No detailed MED flowsheet is claimed.
- **Mass recovery vs volumetric flow:** recovery controls the fraction of feed **mass** becoming permeate; stream densities are approximate, so permeate volume need not equal 50 m³/h at 50% mass recovery.
- **Minimum work:** approximate work estimate using integration of calculated osmotic pressures under a constant-density assumption. It is a useful classroom benchmark, not a fully rigorous Gibbs free-energy calculation.
""")
    st.markdown("#### Reference and baseline data")
    st.dataframe(refcase,hide_index=True,width="stretch")
    st.markdown("#### Download source datasets")
    filelist=sorted(DATA.glob('*'))
    chosen=st.selectbox("Choose a source dataset",[p.name for p in filelist])
    selected=DATA/chosen
    st.download_button(f"Download {chosen}",selected.read_bytes(),file_name=chosen,
                       mime="text/csv" if selected.suffix=='.csv' else "application/octet-stream",key="data_single")
    with st.expander("View original experiment figures"):
        selected_fig=st.selectbox("Original chart",[p.name for p in sorted(ASSETS.glob('*.png'))])
        artifact_image(selected_fig,"Source image generated by the user's Colab notebook")
    st.markdown("#### References and software")
    st.markdown("""
- [USGS PHREEQC software and Pitzer activity model](https://water.usgs.gov/water-resources/software/PHREEQC/)
- [MIT Seawater Thermophysical Properties Library](https://web.mit.edu/seawater/)
- [Streamlit documentation](https://docs.streamlit.io/)
- Mistry & Lienhard: least energy of separation literature (see original project proposal)
""")
    st.markdown("#### Download current scenario")
    scenario=pd.DataFrame([{"Feed salinity (g/kg)":salinity,"Feed flow (m³/h)":feed_flow,"Recovery (%)":recovery,
        "Applied RO pressure (bar)":pressure,"Pump efficiency (%)":pump_eff,"ERD turbine efficiency (%)":erd_eff,
        "Approx. minimum work (kWh/m³)":w_min,"Minimum work model":work_source,
        "RO SEC without turbine (kWh/m³)":ro.sec_without,"RO SEC with turbine (kWh/m³)":ro.sec_with,
        "Energy savings (%)":ro.savings_pct,"MED heat (kWhth/m³)":med_heat,"MED electricity (kWh/m³)":med_electricity,
        "MED heat temperature (°C)":source_temp,"MED exergy input (kWh/m³)":med.total_exergy_kwh_m3,
        "RO with turbine eta II (%)":eta_ro_on,"MED eta II (%)":eta_med,"RO brine pressure margin (bar)":pressure_margin}])
    download_data(scenario,"Seawater_Analyzer_Current_Scenario.csv")

st.divider()
st.caption("🌊 BlueEnergy Lab · Educational Chemical Engineering model · Reference: 35 g/kg, 25°C. External PHREEQC output is preserved; no unrun simulations or measured plant data are claimed.")
