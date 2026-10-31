"""Thermodynamic and first-pass engineering calculations for the dashboard.

The two analytical NaCl models reproduce the supplied Colab notebook.
PHREEQC values are IMPORTED (not reproduced) from the user's actual selected-output data.
The RO model is a hydraulic power balance at imposed mass recovery, not membrane transport.
The MED model is an explicitly assumed heat-source exergy screening scenario.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.integrate import quad

R = 8.314462618  # J mol-1 K-1
TEMPERATURE_K = 298.15
M_NACL = 0.05844  # kg mol-1
M_WATER = 0.01801528  # kg mol-1
V_WATER = 18.07e-6  # m3 mol-1 (constant approximation)
FEED_DENSITY = 1023.0  # kg m-3 (specified baseline)
PERMEATE_DENSITY = 997.0  # kg m-3 (assumption)
BRINE_DENSITY = 1050.0  # kg m-3 (assumption)


def osmotic_coefficient_nacl(molality: float, ideal: bool = False) -> float:
    m = float(molality)
    if m < 0:
        raise ValueError('Molality must be nonnegative')
    if ideal:
        return 1.0
    return (1 - 0.391 * np.sqrt(m) / (1 + 1.2 * np.sqrt(m))
            + m * (0.0765 + 0.2664 * np.exp(-2 * np.sqrt(m)))
            + 0.00127 * m*m)


def osmotic_pressure_nacl(salinity_gkg: float, ideal: bool = False) -> float:
    """Osmotic pressure in bar for simplified NaCl solution at 25 C."""
    s = salinity_gkg / 1000.0
    if not 0 < s < 1:
        raise ValueError('Salt mass fraction must be in (0,1)')
    m = s / (M_NACL * (1 - s))
    phi = osmotic_coefficient_nacl(m, ideal)
    ln_aw = -2 * m * M_WATER * phi
    return -(R * TEMPERATURE_K / V_WATER) * ln_aw / 1e5


def minimum_work_nacl(salinity_gkg: float, recovery_fraction: float, ideal: bool = False) -> float:
    """Approximate work, kWh/m3, constant-density salt-retaining integration."""
    r = float(recovery_fraction)
    if not 0 < r < 1:
        raise ValueError('Recovery must be between 0 and 1')
    if salinity_gkg / (1-r) >= 264:
        return np.nan  # approximate NaCl solubility at 25 C
    integral, _ = quad(lambda x: osmotic_pressure_nacl(salinity_gkg/(1-x), ideal)*1e5,
                       0, r, epsabs=1e-3)
    return integral / r / 3.6e6


def osmotic_pressure_from_activity(activity: float) -> float:
    if not 0 < activity < 1:
        raise ValueError('Water activity must be between 0 and 1')
    return -R*TEMPERATURE_K*np.log(activity)/V_WATER/1e5


@dataclass(frozen=True)
class ROResult:
    q_feed: float
    q_permeate: float
    q_brine: float
    feed_mass_kg_h: float
    permeate_mass_kg_h: float
    brine_mass_kg_h: float
    brine_salinity_gkg: float
    pump_kw: float
    recovered_kw: float
    net_without_kw: float
    net_with_kw: float
    sec_without: float
    sec_with: float
    savings_pct: float
    p_brine_bar: float


def ro_model(feed_m3h: float = 100.0, recovery: float = 0.50,
             pressure_bar: float = 70.0, pump_efficiency: float = 0.80,
             erd_efficiency: float = 0.85, brine_pressure_drop: float = 2.0,
             feed_salinity_gkg: float = 35.0) -> ROResult:
    """Hydraulic turbine, not a pressure exchanger. Target mass recovery is imposed."""
    if not (0 < recovery < 1 and 0 < pump_efficiency <= 1 and 0 <= erd_efficiency <= 1):
        raise ValueError('Invalid recovery or efficiency')
    if not (feed_m3h > 0 and pressure_bar > 1 + brine_pressure_drop):
        raise ValueError('Invalid feed flow or applied pressure')
    mf = feed_m3h * FEED_DENSITY
    mp = recovery * mf
    mb = mf - mp
    qp = mp / PERMEATE_DENSITY
    qb = mb / BRINE_DENSITY
    pbr = pressure_bar - brine_pressure_drop
    pump = feed_m3h * (pressure_bar - 1) / (36 * pump_efficiency)
    recovered = erd_efficiency * qb * (pbr - 1) / 36
    net = pump - recovered
    no_sec = pump / qp
    with_sec = net / qp
    return ROResult(feed_m3h, qp, qb, mf, mp, mb, feed_salinity_gkg/(1-recovery),
                    pump, recovered, pump, net, no_sec, with_sec,
                    100*(no_sec-with_sec)/no_sec, pbr)


@dataclass(frozen=True)
class MEDResult:
    electricity_kwh_m3: float
    heat_kwhth_m3: float
    heat_source_c: float
    ambient_c: float
    heat_exergy_kwh_m3: float
    total_exergy_kwh_m3: float


def med_model(heat_kwhth_m3: float = 60.0, electricity_kwh_m3: float = 2.2,
              heat_source_c: float = 70.0, ambient_c: float = 25.0) -> MEDResult:
    if heat_kwhth_m3 < 0 or electricity_kwh_m3 < 0 or heat_source_c <= ambient_c:
        raise ValueError('Heat and electricity must be nonnegative and source hotter than ambient')
    factor = 1 - (ambient_c+273.15)/(heat_source_c+273.15)
    ex_heat = heat_kwhth_m3 * factor
    return MEDResult(electricity_kwh_m3, heat_kwhth_m3, heat_source_c,
                     ambient_c, ex_heat, ex_heat+electricity_kwh_m3)


def interpolate_phreeqc(df, recovery_percent: float, field: str) -> float:
    """Linearly interpolate the *stored* 0–60% grid; no extrapolation."""
    x = df['Recovery (%)'].to_numpy(dtype=float)
    if not x.min()-1e-8 <= recovery_percent <= x.max()+1e-8:
        raise ValueError('PHREEQC interpolation only supported for measured 0–60% grid')
    y = df[field].to_numpy(dtype=float)
    good = np.isfinite(y)
    if recovery_percent < x[good].min()-1e-8 or recovery_percent > x[good].max()+1e-8:
        raise ValueError('PHREEQC work begins at 10% recovery')
    return float(np.interp(recovery_percent, x[good], y[good]))
