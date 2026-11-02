"""Seawater Desalination Performance Analyzer — presentation-only redesign.

All engineering calculations remain in the original, unchanged models.py.
All experiment datasets remain original, unchanged CSV files.
Run with: python -m streamlit run app.py
"""
from __future__ import annotations

import base64
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from models import (
    minimum_work_nacl,
    osmotic_pressure_nacl,
    interpolate_phreeqc,
    ro_model,
    med_model,
)

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
ASSETS = BASE / "assets"
CYAN = "#1EC8E8"
TEAL = "#00A8A8"
LIGHT = "#7FDBFF"
ORANGE = "#FFA94D"
WHITE = "#F4FAFF"
MUTED = "#B8C7D9"
PALETTE = [CYAN, TEAL, ORANGE, LIGHT, "#8B9EFF", "#79D6B6"]

st.set_page_config(
    page_title="Seawater Desalination Analyzer",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)
CSS = (BASE / "styles.css").read_text(encoding="utf-8")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
KPI_CSS = CSS.split("/* KPI_FRAME_START */", 1)[1].split("/* KPI_FRAME_END */", 1)[0]


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


# --------------------------- UI helpers only ---------------------------
def section_header(title: str, summary: str) -> None:
    st.markdown(
        f'<div class="section-head"><h2>{escape(title)}</h2>'
        f'<p>{escape(summary)}</p></div>',
        unsafe_allow_html=True,
    )


def insight_card(label: str, number: str, conclusion: str) -> None:
    st.markdown(
        '<div class="insight-card">'
        f'<div class="insight-label">{escape(label)}</div>'
        f'<div class="insight-number">{escape(number)}</div>'
        f'<p>{escape(conclusion)}</p></div>',
        unsafe_allow_html=True,
    )


def notice(message: str, kind: str = "info") -> None:
    st.markdown(
        f'<div class="note note-{escape(kind)}">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


def style_fig(fig: go.Figure, y_title: str = "", height: int = 410) -> go.Figure:
    """Apply the same visual styling to every Plotly chart, not its data."""
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=76, b=36),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", size=16, color=MUTED),
        colorway=PALETTE,
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#09213C", font=dict(color=WHITE, size=15)),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.08, x=0,
            font=dict(size=15, color=WHITE), bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(gridcolor="rgba(184,199,217,0.12)", zeroline=False,
                   linecolor="rgba(184,199,217,0.25)", tickfont=dict(size=15),
                   title_font=dict(size=17)),
        yaxis=dict(gridcolor="rgba(184,199,217,0.12)", zeroline=False,
                   linecolor="rgba(184,199,217,0.25)", tickfont=dict(size=15),
                   title_font=dict(size=17)),
        bargap=0.38,
    )
    fig.update_traces(selector=dict(type="scatter"), line_width=4, marker_size=10)
    fig.update_traces(selector=dict(type="bar"), marker_line_width=0,
                      textfont=dict(size=18, color=WHITE))
    if y_title:
        fig.update_yaxes(title_text=y_title)
    return fig


def mark_selected(fig: go.Figure, x: float, label: str) -> None:
    """Selected-point guide: presentation only, doesn't modify a series."""
    fig.add_vline(
        x=x, line_width=2, line_dash="dot", line_color=ORANGE,
        annotation_text=label, annotation_position="top right",
        annotation_font=dict(color=ORANGE, size=16),
    )


def chart_card(title: str, fig: go.Figure, key: str) -> None:
    with st.container(border=True):
        st.markdown(f'<h3 class="chart-title">{escape(title)}</h3>', unsafe_allow_html=True)
        st.plotly_chart(
            fig, use_container_width=True, key=key,
            config={
                "displaylogo": False,
                "displayModeBar": "hover",
                "scrollZoom": False,
                "modeBarButtons": [["zoom2d", "resetScale2d", "toImage"]],
                "toImageButtonOptions": {"format": "png", "filename": key, "scale": 2},
                "responsive": True,
            },
        )


def data_table(frame: pd.DataFrame, filename: str, title: str = "View numerical results") -> None:
    with st.expander(title, expanded=False):
        st.dataframe(frame, use_container_width=True, hide_index=True)
        st.download_button(
            "Download CSV", frame.to_csv(index=False).encode("utf-8"),
            file_name=filename, mime="text/csv", key=f"csv-{filename}",
        )


def hero_image_url() -> str | None:
    path = ASSETS / "hero.jpg"
    if not path.exists():
        return None
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def render_hero() -> None:
    url = hero_image_url()
    overlay = "linear-gradient(90deg,rgba(3,18,37,.98) 0%,rgba(3,18,37,.88) 43%,rgba(3,18,37,.18) 100%)"
    image_layer = f',url("{url}") center / cover no-repeat' if url else ",linear-gradient(125deg,#06203a 0%,#0A5866 100%)"
    st.markdown(
        f'<div class="hero" style="background:{overlay}{image_layer};">'
        '<h1>Seawater Desalination<br>Performance Analyzer</h1>'
        '<p>Explore the science of freshwater production through five interactive engineering experiments.</p>'
        '</div>', unsafe_allow_html=True,
    )


def kpi_card(cards: list[tuple[str, float, int, str, float | None]]) -> None:
    """Four responsive count-up cards; numbers are passed in, never recomputed."""
    columns = st.columns(4, gap="medium")
    for column, (label, value, places, unit, delta) in zip(columns, cards):
        if delta is None or abs(delta) < 1e-9:
            delta_html = '<span class="delta neutral">Reference</span>'
        else:
            arrow = "↑" if delta > 0 else "↓"
            klass = "positive" if delta > 0 else "negative"
            delta_html = f'<span class="delta {klass}">{arrow} {abs(delta):.{places}f} since last change</span>'
        html = f"""<!doctype html><html><head>
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700;800&display=swap" rel="stylesheet">
        <style>{KPI_CSS}</style></head><body><div class="kpi">
        <div class="label">{escape(label)}</div>
        <div class="value counter" data-value="{value:.12f}" data-places="{places}">{value:.{places}f}</div>
        <div class="unit">{escape(unit)}</div>{delta_html}</div>
        <script>
          if(!window.matchMedia('(prefers-reduced-motion:reduce)').matches){{
            const el=document.querySelector('.counter'),target=Number(el.dataset.value),places=Number(el.dataset.places);
            const start=performance.now();function tick(now){{const p=Math.min(1,(now-start)/850);
              el.textContent=(target*(1-Math.pow(1-p,3))).toFixed(places);
              if(p<1)requestAnimationFrame(tick);else el.textContent=target.toFixed(places);}}
            requestAnimationFrame(tick);
          }}
        </script></body></html>"""
        with column:
            components.html(html, height=182, scrolling=False)


def flow_diagram(q_feed: float, q_product: float, q_brine: float) -> None:
    st.markdown(
        '<div class="flow-wrap">'
        f'<div class="flow-step"><b>Feed</b><span>{q_feed:.1f} m³/h</span></div><div class="flow-arrow">→</div>'
        '<div class="flow-step"><b>High-pressure pump</b><span>Electrical input</span></div><div class="flow-arrow">→</div>'
        '<div class="flow-step"><b>RO membrane</b><span>Salt separation</span></div>'
        '</div><div class="flow-split">Two outlet streams</div><div class="flow-wrap flow-output">'
        f'<div class="flow-step product"><b>Product water</b><span>{q_product:.1f} m³/h</span></div>'
        '<div class="flow-branch">or</div>'
        f'<div class="flow-step"><b>Brine</b><span>{q_brine:.1f} m³/h</span></div>'
        '<div class="flow-arrow">→</div>'
        '<div class="flow-step erd"><b>Energy recovery</b><span>Brine turbine</span></div>'
        '</div>', unsafe_allow_html=True,
    )


def reference_work(feed_salinity: int, target_recovery: int) -> tuple[float, str]:
    if feed_salinity == 35:
        return interpolate_phreeqc(ph, target_recovery, "Minimum Work (kWh/m3)"), "PHREEQC lookup / interpolation"
    return minimum_work_nacl(feed_salinity, target_recovery / 100), "Simplified NaCl model"


# --------------------------- Sidebar controls ---------------------------
DEFAULTS = dict(
    feed_salinity=35, target_recovery=50, feed_flow=100.0,
    ro_pressure=70, pump_efficiency=80, turbine_efficiency=85,
    med_heat=60, med_electricity=2.2, med_temperature=70,
)
for setting, default in DEFAULTS.items():
    st.session_state.setdefault(setting, default)


def reset_defaults() -> None:
    for setting, default in DEFAULTS.items():
        st.session_state[setting] = default


with st.sidebar:
    st.markdown('<div class="sidebar-title">PROCESS CONTROLS</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-group">FEED</div>', unsafe_allow_html=True)
    st.slider("Salinity (g/kg)", 20, 50, step=5, key="feed_salinity")
    st.number_input("Flow rate (m³/h)", min_value=10.0, max_value=1000.0, step=10.0, key="feed_flow")
    st.markdown('<div class="sidebar-group">RECOVERY</div>', unsafe_allow_html=True)
    st.slider("Target mass recovery (%)", 10, 60, step=10, key="target_recovery")
    st.markdown('<div class="sidebar-group">REVERSE OSMOSIS</div>', unsafe_allow_html=True)
    st.slider("Operating pressure (bar)", 60, 90, step=1, key="ro_pressure")
    st.slider("Pump efficiency (%)", 60, 95, step=5, key="pump_efficiency")
    st.slider("Turbine efficiency (%)", 40, 95, step=5, key="turbine_efficiency")
    with st.expander("MED scenario inputs"):
        st.slider("Heat (kWhth/m³)", 40, 120, step=5, key="med_heat")
        st.slider("Electricity (kWh/m³)", 1.0, 4.0, step=0.1, key="med_electricity")
        st.slider("Heat source (°C)", 55, 95, step=5, key="med_temperature")
    st.button("Reset to default", key="reset_parameters", on_click=reset_defaults, use_container_width=True)

salinity = st.session_state.feed_salinity
recovery = st.session_state.target_recovery
feed_flow = st.session_state.feed_flow
pressure = st.session_state.ro_pressure
pump_eff = st.session_state.pump_efficiency
erd_eff = st.session_state.turbine_efficiency
med_heat = st.session_state.med_heat
med_electricity = st.session_state.med_electricity
source_temp = st.session_state.med_temperature
r = recovery / 100

# These are the EXACT SAME calls, constants, and outputs as the original app.
ro = ro_model(feed_flow, r, pressure, pump_eff/100, erd_eff/100, feed_salinity_gkg=salinity)
med = med_model(med_heat, med_electricity, source_temp)
w_min, work_source = reference_work(salinity, recovery)
eta_ro_off = 100 * w_min / ro.sec_without
eta_ro_on = 100 * w_min / ro.sec_with
eta_med = 100 * w_min / med.total_exergy_kwh_m3
brine_salinity = salinity / (1-r)
pi_brine = (interpolate_phreeqc(ph, recovery, "Osmotic Pressure (bar)")
            if salinity == 35 else osmotic_pressure_nacl(brine_salinity))
pressure_margin = ro.p_brine_bar - pi_brine

# Slider deltas compare two runs; no thermodynamic values are altered.
current_kpis = (w_min, ro.sec_without, ro.sec_with, ro.savings_pct)
previous_kpis = st.session_state.get("_previous_kpis")
deltas = (None,) * 4 if previous_kpis is None else tuple(
    current - previous for current, previous in zip(current_kpis, previous_kpis)
)
st.session_state["_previous_kpis"] = current_kpis

# --------------------------- Hero / KPIs ---------------------------
render_hero()
kpi_card([
    ("Minimum Work", w_min, 3, "kWh/m³", deltas[0]),
    ("RO SEC without ERD", ro.sec_without, 2, "kWh/m³", deltas[1]),
    ("RO SEC with ERD", ro.sec_with, 2, "kWh/m³", deltas[2]),
    ("Energy Savings", ro.savings_pct, 1, "%", deltas[3]),
])

if salinity != 35:
    notice("PHREEQC was simulated at a 35 g/kg feed only. This selection uses the simplified NaCl calculation, not invented PHREEQC results.")
if pressure_margin <= 0:
    notice(f"Pressure check: brine pressure {ro.p_brine_bar:.1f} bar does not exceed estimated osmotic pressure {pi_brine:.1f} bar. The fixed-recovery scenario may be infeasible.", "warning")
elif pressure_margin < 8:
    notice(f"Pressure check: only {pressure_margin:.1f} bar remains above estimated brine osmotic pressure. Membrane transport feasibility was not solved.", "warning")

# --------------------------- Seven views ---------------------------
tabs = st.tabs(["Overview", "Salinity", "Recovery", "Seawater models", "RO energy", "RO vs MED", "Data & methods"])

with tabs[0]:
    section_header("The reference plant", "Follow the seawater from feed to freshwater and the energy recovery loop.")
    flow_diagram(feed_flow, ro.q_permeate, ro.q_brine)
    a, b = st.columns(2, gap="large")
    with a:
        fig = go.Figure(go.Bar(
            x=["Pump", "No ERD", "With ERD"],
            y=[ro.pump_kw, ro.net_without_kw, ro.net_with_kw],
            marker_color=[CYAN, ORANGE, TEAL],
            text=[f"{x:.1f}" for x in [ro.pump_kw, ro.net_without_kw, ro.net_with_kw]],
            textposition="outside",
        ))
        fig.update_layout(showlegend=False)
        chart_card("Electrical power flow", style_fig(fig, "Power (kW)"), "overview-power")
    with b:
        fig = go.Figure(go.Pie(
            labels=["Permeate", "Brine"],
            values=[ro.permeate_mass_kg_h, ro.brine_mass_kg_h], hole=.72,
            marker_colors=[CYAN, TEAL], textinfo="percent+label", sort=False,
            textfont=dict(size=17, color=WHITE),
        ))
        fig.update_layout(showlegend=False)
        chart_card("Mass distribution", style_fig(fig), "overview-mass")
    insight_card("REFERENCE CASE", f"{feed_flow:.0f} m³/h", f"Feed at {salinity} g/kg and {recovery}% recovery; output changes with the sidebar controls.")

with tabs[1]:
    section_header("Effect of salinity", "See how salt concentration changes the theoretical energy required to produce freshwater.")
    left, right = st.columns(2, gap="large")
    with left:
        fig = go.Figure()
        for i, s in enumerate(sorted(exp1["Feed Salinity (g/kg)"].unique())):
            sub = exp1[exp1["Feed Salinity (g/kg)"] == s]
            fig.add_trace(go.Scatter(
                x=sub["Recovery (%)"], y=sub["Minimum Work (kWh/m3)"],
                name=f"{s:g} g/kg", mode="lines+markers", line=dict(color=PALETTE[i]),
            ))
        mark_selected(fig, recovery, f"{recovery}% recovery")
        fig.update_xaxes(title_text="Recovery (%)")
        chart_card("Minimum work across feed salinities", style_fig(fig, "Minimum work (kWh/m³)"), "salinity-curves")
    with right:
        s_grid = np.linspace(10, 70, 90)
        w_grid = [minimum_work_nacl(s, r) for s in s_grid]
        fig = go.Figure(go.Scatter(x=s_grid, y=w_grid, mode="lines", name="Non-ideal NaCl", line=dict(color=CYAN)))
        mark_selected(fig, salinity, f"{salinity} g/kg")
        fig.update_xaxes(title_text="Feed salinity (g/kg)")
        chart_card("Current recovery: salinity sensitivity", style_fig(fig, "Minimum work (kWh/m³)"), "salinity-selected")
    insight_card("SELECTED SCENARIO", f"{minimum_work_nacl(salinity, r):.3f} kWh/m³", "The NaCl model predicts greater minimum work at higher feed salinity.")
    data_table(exp1, "Experiment_1_Results.csv", "See original salinity/recovery data")

with tabs[2]:
    section_header("Effect of recovery", "Watch the brine concentrate and the energy requirement rise as water is extracted.")
    a, b = st.columns(2, gap="large")
    with a:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=modelcmp["Recovery (%)"], y=modelcmp["NaCl Model (kWh/m3)"],
                                 mode="lines+markers", name="Simplified NaCl", line=dict(color=ORANGE)))
        fig.add_trace(go.Scatter(x=modelcmp["Recovery (%)"], y=modelcmp["PHREEQC Model (kWh/m3)"],
                                 mode="lines+markers", name="PHREEQC", line=dict(color=CYAN)))
        mark_selected(fig, recovery, f"{recovery}% recovery")
        fig.update_xaxes(title_text="Recovery (%)")
        chart_card("Minimum work versus recovery", style_fig(fig, "Minimum work (kWh/m³)"), "recovery-compare")
    with b:
        fig = go.Figure(go.Scatter(x=ph["Recovery (%)"], y=ph["Water Activity"], mode="lines+markers",
                                    name="PHREEQC water activity", line=dict(color=TEAL)))
        mark_selected(fig, recovery, f"{recovery}% recovery")
        fig.update_xaxes(title_text="Recovery (%)")
        chart_card("Water activity versus recovery", style_fig(fig, "Water activity"), "recovery-activity")
    insight_card("REFERENCE FEED", f"{interpolate_phreeqc(ph, recovery, 'Minimum Work (kWh/m3)'):.3f} kWh/m³",
                 "At 35 g/kg, the PHREEQC-derived minimum-work curve increases with recovery.")
    with st.expander("Play recovery 20–70% (simplified NaCl model)"):
        values = np.arange(20, 71, 5, dtype=int)
        works = [minimum_work_nacl(35, float(p)/100) for p in values]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=values, y=works, mode="lines", name="NaCl model", line=dict(color=CYAN)))
        fig.add_trace(go.Scatter(x=[values[0]], y=[works[0]], mode="markers", name="Animated recovery",
                                 marker=dict(size=17, color=ORANGE, line=dict(color=WHITE, width=2))))
        fig.frames = [go.Frame(
            name=str(v), traces=[1], data=[go.Scatter(x=[v], y=[w], mode="markers",
                         marker=dict(size=17, color=ORANGE, line=dict(color=WHITE, width=2)))],
        ) for v, w in zip(values, works)]
        fig.update_layout(updatemenus=[dict(type="buttons", direction="left", showactive=False,
            x=0, y=1.27, buttons=[dict(label="Play 20–70%", method="animate",
              args=[None, {"frame": {"duration": 350, "redraw": True}, "transition": {"duration": 120},
                           "fromcurrent": False, "mode": "immediate"}])])])
        fig.update_xaxes(title_text="Recovery (%)")
        chart_card("Recovery playback — NaCl only", style_fig(fig, "Minimum work (kWh/m³)", 370), "recovery-play")
        notice("This playback uses the existing NaCl equation; PHREEQC data only cover 0–60% recovery.")
    data_table(ph, "PHREEQC_Recovery_Results.csv", "See PHREEQC recovery table")

with tabs[3]:
    section_header("Seawater thermodynamic models", "Compare ideal NaCl, non-ideal NaCl and actual multicomponent PHREEQC output.")
    a, b = st.columns(2, gap="large")
    with a:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=mit["Salinity (g/kg)"], y=mit["PHREEQC (bar)"],
                                 mode="lines+markers", name="PHREEQC Pitzer", line=dict(color=CYAN)))
        fig.add_trace(go.Scatter(x=mit["Salinity (g/kg)"], y=mit["MIT Approx. (bar)"],
                                 mode="lines+markers", name="MIT approximation", line=dict(color=ORANGE, dash="dash")))
        mark_selected(fig, 35/(1-r), f"{35/(1-r):.1f} g/kg")
        fig.update_xaxes(title_text="Brine salinity (g/kg)")
        chart_card("PHREEQC versus MIT", style_fig(fig, "Osmotic pressure (bar)"), "models-mit")
    with b:
        fig = go.Figure(go.Scatter(x=ph["Recovery (%)"], y=ph["Osmotic Coefficient"], mode="lines+markers",
                                    name="PHREEQC", line=dict(color=TEAL)))
        mark_selected(fig, recovery, f"{recovery}% recovery")
        fig.update_xaxes(title_text="Recovery (%)")
        chart_card("Non-ideal osmotic coefficient", style_fig(fig, "Osmotic coefficient"), "models-phi")
    r_grid = np.arange(10, 61, 10, dtype=float)
    fig = go.Figure()
    for name, values, color, dash in [
        ("Ideal ionic NaCl", [minimum_work_nacl(35, x/100, ideal=True) for x in r_grid], LIGHT, "dot"),
        ("Non-ideal NaCl", [minimum_work_nacl(35, x/100) for x in r_grid], ORANGE, "solid"),
        ("PHREEQC multicomponent", [interpolate_phreeqc(ph, x, "Minimum Work (kWh/m3)") for x in r_grid], CYAN, "solid"),
    ]:
        fig.add_trace(go.Scatter(x=r_grid, y=values, mode="lines+markers", name=name,
                                 line=dict(color=color, dash=dash)))
    mark_selected(fig, recovery, f"{recovery}% recovery")
    fig.update_xaxes(title_text="Recovery (%)")
    chart_card("Three models, one seawater reference", style_fig(fig, "Minimum work (kWh/m³)", 440), "models-three")
    insight_card("MIT / PHREEQC AGREEMENT", f"{mit['Difference (%)'].abs().mean():.3f}%",
                 "Mean absolute model-to-model difference, not measured experimental error.")
    data_table(modelcmp, "Exp3_Model_Comparison.csv", "See model-comparison data")
    data_table(mit, "MIT_PHREEQC_Validation.csv", "See MIT comparison data")

with tabs[4]:
    section_header("Reverse osmosis energy", "Discover how a pressurized brine turbine reduces the pump's electrical demand.")
    left, right = st.columns(2, gap="large")
    with left:
        fig = go.Figure(go.Bar(
            x=["Without ERD", "With turbine"], y=[ro.sec_without, ro.sec_with],
            marker_color=[ORANGE, CYAN], text=[f"{ro.sec_without:.2f}", f"{ro.sec_with:.2f}"],
            textposition="outside",
        ))
        fig.update_layout(showlegend=False)
        chart_card("RO specific energy consumption", style_fig(fig, "SEC (kWh/m³)"), "ro-sec")
    with right:
        p_grid = np.linspace(60, 90, 61)
        pressures = [ro_model(feed_flow, r, float(p), pump_eff/100, erd_eff/100,
                              feed_salinity_gkg=salinity) for p in p_grid]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=p_grid, y=[v.sec_without for v in pressures], mode="lines",
                                 name="Without ERD", line=dict(color=ORANGE)))
        fig.add_trace(go.Scatter(x=p_grid, y=[v.sec_with for v in pressures], mode="lines",
                                 name="With turbine", line=dict(color=CYAN)))
        mark_selected(fig, pressure, f"{pressure} bar")
        fig.update_xaxes(title_text="RO applied pressure (bar)")
        chart_card("Operating-pressure sensitivity", style_fig(fig, "SEC (kWh/m³)"), "ro-pressure")
    insight_card("MODELED ELECTRICITY SAVED", f"{ro.savings_pct:.2f}%",
                 f"Brine turbine recovers {ro.recovered_kw:.2f} kW under the selected assumptions.")
    with st.expander("View flow balance and configuration results"):
        streams = pd.DataFrame({
            "Stream": ["Feed", "Permeate", "Brine"],
            "Mass flow (kg/h)": [ro.feed_mass_kg_h, ro.permeate_mass_kg_h, ro.brine_mass_kg_h],
            "Volumetric flow (m³/h)": [ro.q_feed, ro.q_permeate, ro.q_brine],
            "Salt content (g/kg)": [salinity, 0, brine_salinity],
        })
        st.dataframe(streams, use_container_width=True, hide_index=True)
        table = pd.DataFrame({
            "Configuration": ["Without ERD", "With turbine"],
            "Net power (kW)": [ro.net_without_kw, ro.net_with_kw],
            "SEC (kWh/m³)": [ro.sec_without, ro.sec_with],
            "Second-law efficiency (%)": [eta_ro_off, eta_ro_on],
        })
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.download_button("Download CSV", table.to_csv(index=False).encode("utf-8"),
                           "RO_scenario_results.csv", "text/csv")
    notice("Fixed recovery and approximate densities; this is a pump-and-turbine energy model, not a membrane-transport or pressure-exchanger simulation.")

with tabs[5]:
    section_header("RO versus MED", "Compare electricity and thermal energy on the same thermodynamic exergy basis.")
    a, b = st.columns(2, gap="large")
    with a:
        insight_card("RO WITH TURBINE · SECOND-LAW EFFICIENCY", f"{eta_ro_on:.2f}%",
                     f"Electric SEC: {ro.sec_with:.3f} kWh/m³")
    with b:
        insight_card("MED SCENARIO · SECOND-LAW EFFICIENCY", f"{eta_med:.2f}%",
                     f"Total exergy: {med.total_exergy_kwh_m3:.3f} kWh/m³")
    view = st.pills("Compare", ["Second-law efficiency", "Exergy input"], default="Second-law efficiency", key="med-view")
    labels = ["RO no ERD", "RO with ERD", "MED scenario"]
    exergies = [ro.sec_without, ro.sec_with, med.total_exergy_kwh_m3]
    efficiencies = [eta_ro_off, eta_ro_on, eta_med]
    vals = exergies if view == "Exergy input" else efficiencies
    y_axis = "Exergy input (kWh/m³)" if view == "Exergy input" else "Second-law efficiency (%)"
    fig = go.Figure(go.Bar(
        x=labels, y=vals, marker_color=[LIGHT, CYAN, ORANGE],
        text=[f"{x:.2f}" for x in vals], textposition="outside",
    ))
    fig.update_layout(showlegend=False)
    chart_card("RO / MED comparison", style_fig(fig, y_axis), "med-bars")
    with st.expander("Heat-source temperature sensitivity"):
        temperatures = np.linspace(55, 95, 81)
        response = [100*w_min/med_model(med_heat, med_electricity, float(t)).total_exergy_kwh_m3
                    for t in temperatures]
        fig = go.Figure(go.Scatter(x=temperatures, y=response, mode="lines",
                                    name="MED scenario", line=dict(color=TEAL)))
        mark_selected(fig, source_temp, f"{source_temp}°C")
        fig.update_xaxes(title_text="Heat source (°C)")
        chart_card("Fixed-load temperature study", style_fig(fig, "Second-law efficiency (%)", 360), "med-temp")
    table = pd.DataFrame({
        "Process": labels,
        "Electricity (kWh/m³)": [ro.sec_without, ro.sec_with, med.electricity_kwh_m3],
        "Heat (kWhth/m³)": [0, 0, med.heat_kwhth_m3],
        "Exergy input (kWh/m³)": exergies,
        "Second-law efficiency (%)": efficiencies,
    })
    data_table(table, "RO_MED_scenario_results.csv", "View RO and MED numerical table")
    notice("MED thermal and electrical loads are scenario assumptions, not outputs from a detailed distillation simulator.")

with tabs[6]:
    section_header("Data and methods", "Explore the original experiment files and the assumptions behind each result.")
    source = st.pills("Select source", ["Data files", "Scientific methods", "Original plots"],
                      default="Data files", key="source-view")
    if source == "Data files":
        names = sorted(path.name for path in DATA.iterdir() if path.is_file())
        selected = st.selectbox("Choose a source file", names)
        file = DATA / selected
        if file.suffix.lower() == ".csv":
            st.dataframe(read_data(selected), use_container_width=True, hide_index=True)
        st.download_button("Download source file", file.read_bytes(), file_name=file.name,
                           mime="text/csv" if file.suffix == ".csv" else "application/octet-stream")
    elif source == "Scientific methods":
        for name, description in [
            ("PHREEQC Pitzer", "Original 35 g/kg multicomponent seawater simulation; Streamlit reads stored output rather than rerunning PHREEQC."),
            ("MIT reference", "The saved comparison uses an approximate reproduction of the MIT osmotic-pressure correlation, not experimental measurements."),
            ("Simplified NaCl", "The existing concentration-dependent osmotic coefficient and numerical integration functions; not a complete Pitzer model."),
            ("RO", "Fixed mass recovery with a high-pressure pump and hydraulic brine turbine; membrane transport and fouling are outside the model."),
            ("MED", "Assumed heat and electricity inputs converted to exergy using a constant-temperature heat-source model."),
        ]:
            with st.expander(name):
                st.write(description)
        st.markdown("[USGS PHREEQC](https://water.usgs.gov/water-resources/software/PHREEQC/)  ·  "
                    "[MIT Seawater Library](https://web.mit.edu/seawater/)  ·  "
                    "[Streamlit](https://docs.streamlit.io/)")
    else:
        images = sorted(ASSETS.glob("*.png"))
        if images:
            image = st.selectbox("Original experiment plot", [p.name for p in images])
            st.image(str(ASSETS / image), use_container_width=True)

    scenario = pd.DataFrame([{
        "Feed salinity (g/kg)": salinity,
        "Feed flow (m³/h)": feed_flow,
        "Recovery (%)": recovery,
        "Applied RO pressure (bar)": pressure,
        "Pump efficiency (%)": pump_eff,
        "ERD turbine efficiency (%)": erd_eff,
        "Approx. minimum work (kWh/m³)": w_min,
        "Minimum work model": work_source,
        "RO SEC without turbine (kWh/m³)": ro.sec_without,
        "RO SEC with turbine (kWh/m³)": ro.sec_with,
        "Energy savings (%)": ro.savings_pct,
        "MED heat (kWhth/m³)": med_heat,
        "MED electricity (kWh/m³)": med_electricity,
        "MED heat temperature (°C)": source_temp,
        "MED exergy input (kWh/m³)": med.total_exergy_kwh_m3,
        "RO with turbine eta II (%)": eta_ro_on,
        "MED eta II (%)": eta_med,
        "RO brine pressure margin (bar)": pressure_margin,
    }])
    st.download_button("Download current scenario CSV", scenario.to_csv(index=False).encode("utf-8"),
                       "Seawater_Analyzer_Current_Scenario.csv", "text/csv")

st.markdown('<div class="app-end">Engineering model · 25°C reference case · All values retain original calculation methods.</div>',
            unsafe_allow_html=True)
