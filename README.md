# 🌊 Seawater Desalination — Thermodynamic Performance Analyzer

A polished, self-contained **Streamlit web app** built from the five experiments and uploaded source files for a Chemical Engineering desalination course project.

## What the app does

- **Overview:** reference-plant mass balance and live power accounting
- **Experiment 1:** minimum-work response to salt concentration
- **Experiment 2:** effect of water recovery on calculated work
- **Experiment 3:** ideal NaCl, simplified non-ideal NaCl, externally simulated **USGS PHREEQC** seawater, and independent **MIT seawater-property comparison**
- **Experiment 4:** simplified reverse osmosis with and without a hydraulic recovery turbine
- **Experiment 5:** RO/MED comparison using electrical energy and thermal exergy
- **Data & methods:** provenance, source datasets, figures, assumptions, CSV downloads

The **sidebar sliders are interactive**. Salinity and recovery change the theoretical-work comparison; pressure and efficiencies change RO SEC; MED heat, electricity and source temperature change MED exergy and the resulting second-law indicator.

## How to run on Windows with VS Code

1. Extract `Seawater_Desalination_Analyzer.zip`.
2. Open the **extracted folder** in VS Code (**File → Open Folder**).
3. Open **Terminal → New Terminal** and run:

   ```powershell
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe -m streamlit run app.py
   ```

   Using `.venv\Scripts\python.exe` avoids changing PowerShell execution policies.

4. Your browser should open the app. If it doesn't, visit the local URL printed in the terminal (usually `http://localhost:8501`).
5. To stop the app, press `Ctrl + C` in that terminal.

**If `python` is not found:** install a supported recent Python version first or use `py -3.11` / `py -3.12` as your interpreter, if installed. On Windows, you may substitute `py -3.11 -m venv .venv` for the first command.

### Alternative without a virtual environment

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Data and methods: scientific boundaries

This app incorporates the actual source values you provided. It is **a classroom engineering study**, not a digitally calibrated plant or real-time PHREEQC simulation.

| Part | Source | What it supports |
|---|---|---|
| Salinity and recovery | `data/Experiment_1_Results.csv` | Simplified non-ideal NaCl minimum-work calculations |
| PHREEQC recovery | `data/PHREEQC_Recovery_Results.csv` | Seven externally simulated thermodynamic states at original feed salinity 35 g/kg, 25°C |
| Model comparison | `data/Exp3_Model_Comparison.csv` | NaCl-vs-multicomponent predicted work |
| MIT cross-check | `data/MIT_PHREEQC_Validation.csv` | Model-to-model osmotic-pressure comparisons using an *approximate reproduction* of the MIT library functions |
| RO energy | `data/Experiment_4_RO_Energy_Results.csv` | Fixed-recovery hydraulic pump and brine turbine calculations |
| MED exergy | `data/Experiment_5_RO_vs_MED.csv` | Assumed MED heat and electricity inputs; heat-source Carnot factor |
| Original numerical code | `Original_Colab_Notebook.ipynb` | User-run reference calculations and original graph outputs |

### Critical qualifications

1. **PHREEQC is not recalculated** on each slider change. For a **35 g/kg** feed, the app interpolates only within the 10–60% PHREEQC grid. A different feed salinity switches to the simplified NaCl work model and states this in the UI.
2. Recovery is a **mass fraction**, not a volumetric fraction. Densities are assumed constant for each stream.
3. The approximate minimum-work integral comes from the course proposal's simple concentration-path model. It is **not** a complete Gibbs free-energy separation calculation.
4. **RO** is hydraulic energy-balance modeling with specified pressure and recovery; not membrane transport (no permeability, concentration polarization, fouling or realistic pressure/recovery closure). The energy recovery device is a **turbine**, *not* a pressure exchanger.
5. **MED** thermal and electrical inputs are scenario assumptions; no independent MED unit-operation simulation was performed. The heat-exergy value assumes heat provided from a constant-temperature reservoir.
6. The observed **0.245%** MIT–PHREEQC mean absolute difference compares two models and is **not a laboratory validation error**. MIT values here come from an **approximate Python expression**, not the original MATLAB execution.
7. Check pressure feasibility warnings. Positive pressure margin is necessary but **not sufficient** for an RO system to achieve the selected water recovery.

## Project files

```text
Seawater_Desalination_Analyzer/
├── app.py                    # Streamlit interface
├── models.py                 # Analytical equations and energy balance
├── requirements.txt          # Python dependencies
├── README.md                 # This guide
├── Original_Colab_Notebook.ipynb
├── .streamlit/config.toml    # Brand styling
├── data/                     # Source CSVs and PHREEQC files
├── assets/                   # Source experiment figures
└── tests/test_models.py      # Regression tests for baseline outputs
```

## Optional: rerun mathematical checks

```powershell
.venv\Scripts\python.exe -m pip install pytest
.venv\Scripts\python.exe -m pytest -q
```

## Publishing to Streamlit Community Cloud

Put this extracted folder into a GitHub repository and deploy `app.py` as the entrypoint on [Streamlit Community Cloud](https://streamlit.io/cloud). Keep the supplied `data/`, `assets/`, and `models.py` folders in the same repository. Note that deployment creates a public demo if you choose public sharing: do not upload private project data without permission.

## Acknowledgments and source links

- [USGS PHREEQC](https://water.usgs.gov/water-resources/software/PHREEQC/)
- [MIT Seawater Thermophysical Properties Library](https://web.mit.edu/seawater/)
- [Streamlit Docs](https://docs.streamlit.io/)
