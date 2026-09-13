# RADS — Ransomware Risk Analysis & Decision Support

A Prospect-Theory model of ransom-payment decisions, plus a practical,
organisation-level decision-support tool aligned with DORA asset/resilience
obligations.

> **Decision support only — not legal advice, and not authorisation to pay.**
> A ransom payment can breach EU/OFAC sanctions and funds criminal activity.
> See [`tool/`](tool/) and always involve legal counsel and law enforcement
> before acting.

---

## What's here

RADS models how ransomware attackers exploit **Prospect Theory** — shifting the
victim's reference point and using time-urgency to distort probabilities — to push
organisations into paying, and how that distortion can be mathematically reversed
to reach a rational *pay vs. self-recover* decision.

The repo has two halves that share one scoring core:

| Folder | What it is |
|---|---|
| [`paper/`](paper/) | The research manuscript (LaTeX, MDPI *Journal of Cybersecurity and Privacy* template) and bibliography. |
| [`simulation/`](simulation/) | The model implemented and validated in Python — the value function, probability weighting, expected-value benchmark, attacker manipulation, and the RADS correction, plus a Monte-Carlo study. |
| [`tool/`](tool/) | An Excel-based, organisation-level decision tool and a worked example. Doubles as a DORA-aligned ICT asset register with risk scoring. |

---

## Quick start

### Run the simulation
Open [`simulation/RADS_simulation.ipynb`](simulation/RADS_simulation.ipynb) in
Google Colab (or Jupyter) and **Run all**. It is self-contained. To regenerate
the figures from the command line:

```bash
pip install -r requirements.txt
cd simulation && python rads_analysis.py
```

`rads_core.py` is the reusable engine (value function `v(x)`, weighting `w(p)`,
lotteries, expected value, and the decision logic) — import it anywhere.

### Use the decision tool
1. Open [`tool/RADS_Registry_Template.xlsx`](tool/RADS_Registry_Template.xlsx).
2. Read the **Legal_Ethics** sheet first.
3. Fill the yellow cells on **Org_Info** and list affected applications on **Assets**
   (criticality, backup coverage, value, downtime cost).
4. Read the single organisation-level recommendation on **Results**.

See [`tool/examples/Redport_DE_example.xlsx`](tool/examples/Redport_DE_example.xlsx)
for a fully worked case (a fictional large logistics operator, 52 affected apps).
To rebuild the workbooks from source: `cd tool && python build_xlsx.py`.

---

## How this supports DORA

The tool is effectively a **DORA-aligned ICT asset register with live risk scoring**,
rather than a static spreadsheet:

- **Art. 8 (identification & classification):** the Assets sheet is a criticality-classified
  inventory of ICT assets.
- **Resilience / backup & recovery:** backup coverage per asset drives whether it is
  self-recoverable, feeding the decision directly.
- **Art. 29 (concentration risk):** concentration logic (e.g. the +15% same-platform
  multiplier from the DORA Registry app) plugs into the same scoring.
- **Shared engine:** the same Prospect-Theory scoring core powers both the validated
  research model and the compliance tool, so the tooling is grounded in a defensible,
  documented method.

---

## Status & honest caveats

- **Early iteration.** The model is being actively refined.
- **Placeholder parameters.** Simulation and example figures use illustrative ranges.
  Anchor them to current incident data (Coveware / Sophos / IBM / ENISA) before quoting
  any number.
- **Citations to verify.** Some references were reconstructed and are flagged `% [VERIFY]`
  in [`paper/references.bib`](paper/references.bib).
- **The tool never authorises payment.** It routes to legal/sanctions review.

---

## Repository layout

```
rads/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── paper/
│   ├── main.tex              # MDPI JCP manuscript
│   ├── references.bib
│   └── figures/              # add the paper's PNGs here (see note below)
├── simulation/
│   ├── RADS_simulation.ipynb # Colab-ready validation notebook
│   ├── rads_core.py          # reusable scoring engine (Eqs. 1–9)
│   ├── rads_analysis.py      # regenerates the figures
│   ├── build_nb.py           # rebuilds the notebook from source
│   └── figures/              # generated figures
└── tool/
    ├── RADS_Registry_Template.xlsx   # blank, upload-ready
    ├── build_xlsx.py                 # rebuilds the workbooks
    └── examples/
        └── Redport_DE_example.xlsx   # worked example
```

> **Note:** `paper/figures/` is empty on purpose — add the manuscript's own images
> (`statistic_ransomware.png`, `shifted_s-shaped.png`, `RADS.png`) from your Overleaf
> project, or regenerate them.

---

## Citation

If you use this work, please cite the paper (details to be completed on publication):

> Sharma, P. *Taming the Ransomware Threats: Leveraging Prospect Theory for Rational
> Payment Decisions.* (in preparation).
