import math
from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import minimum_work_nacl, osmotic_pressure_nacl, ro_model, med_model, interpolate_phreeqc


DATA = Path(__file__).resolve().parents[1] / 'data'


def test_reference_nacl_matches_notebook():
    assert abs(minimum_work_nacl(35,0.5)-1.12080283879) < 1e-8
    assert minimum_work_nacl(35,0.5, ideal=True)>minimum_work_nacl(35,0.5)


def test_reference_ro_matches_experiment_4():
    ro=ro_model()
    assert abs(ro.pump_kw-239.58333333333)<1e-7
    assert abs(ro.net_with_kw-162.52003968254)<1e-7
    assert abs(ro.sec_without-4.669884327142)<1e-9
    assert abs(ro.sec_with-3.167790411798)<1e-9
    assert abs(ro.savings_pct-32.165548)<0.01
    assert abs(ro.feed_mass_kg_h-ro.permeate_mass_kg_h-ro.brine_mass_kg_h)<1e-8


def test_med_matches_experiment_5():
    med=med_model()
    assert abs(med.heat_exergy_kwh_m3-7.8682791782)<1e-8
    assert abs(med.total_exergy_kwh_m3-10.0682791782)<1e-8


def test_phreeqc_interpolation_matches_source():
    ph=pd.read_csv(DATA/'PHREEQC_Recovery_Results.csv')
    assert abs(interpolate_phreeqc(ph,50,'Minimum Work (kWh/m3)')-1.030640407190924)<1e-9
    assert abs(interpolate_phreeqc(ph,50,'Osmotic Pressure (bar)')-55.46625520533746)<1e-9


def test_monotonic_energy_and_model_difference():
    assert minimum_work_nacl(50,0.5)>minimum_work_nacl(20,0.5)
    assert minimum_work_nacl(35,0.6)>minimum_work_nacl(35,0.3)
    a=ro_model(100,0.5,70,0.8,0.85)
    b=ro_model(100,0.5,70,0.8,0.95)
    assert b.sec_with<a.sec_with
