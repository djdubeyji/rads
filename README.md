# RADS — Ransomware Risk Analysis & Decision Support

A Prospect-Theory model of ransom-payment decisions: it formalises how ransomware
operators manipulate a victim's decision through framing and time-urgency, and how that
manipulation can be reversed to reach a rational *pay vs. self-recover* decision.

> **Decision support only — not legal advice, and not authorisation to pay.**
> A ransom payment can breach EU/OFAC sanctions and funds criminal activity. Any real
> decision must involve legal counsel and law enforcement.

This repository accompanies the paper *Taming the Ransomware Threats: Leveraging Prospect
Theory for Rational Payment Decisions* (in preparation, targeting the MDPI *Journal of
Cybersecurity and Privacy*).

---

## What's here

RADS models the ransom decision as a lottery over uncertain losses. Attackers shift the
victim's reference point and distort perceived probabilities (both formalised with
Prospect Theory's value function and probability-weighting function); RADS reverses that
distortion by reinstating true parameters and anchoring the decision at the realistic
self-recovery fallback rather than an unattainable pristine state.

| Folder | Contents |
|---|---|
| [`paper/`](paper/) | The manuscript (LaTeX, MDPI JCP template), bibliography, and the Results section. |
| [`simulation/`](simulation/) | The model implemented and validated in Python: value function, probability weighting, the expected-value benchmark, the attacker-manipulation and RADS-correction operators, plus a Monte-Carlo study and the figures. |

---

## Quick start

### Run the simulation
Open [`simulation/RADS_simulation.ipynb`](simulation/RADS_simulation.ipynb) in Google
Colab (or Jupyter) and **Run all** — it is self-contained. To regenerate the figures from
the command line:

```bash
pip install -r requirements.txt
cd simulation && python rads_analysis.py
```

`rads_core.py` is the reusable engine (value function `v(x)`, weighting `w(p)`, the pay/
recover lotteries, expected value, and the decision logic of Eqs. 1–9) — import it anywhere.

### Headline result
On a population of 20,000 simulated incidents, attacker framing induces systematic
over-payment; RADS roughly halves the resulting expected regret, eliminates over-payment,
and is provably invariant to the attacker's framing intensity. See
[`simulation/figures/`](simulation/figures/) and the paper's Results section.

---

## Status & honest caveats

- **Early iteration**, actively being refined.
- **Placeholder parameters.** Simulation figures use illustrative ranges. Anchor them to
  current incident data (Coveware / Sophos / IBM / ENISA) before quoting any number.
- **Citations to verify.** Some references were reconstructed and are flagged `% [VERIFY]`
  in [`paper/references.bib`](paper/references.bib) — confirm before submission.

---

## Repository layout

```
rads/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── paper/
│   ├── template.tex          # MDPI JCP manuscript (main file)
│   ├── results.tex           # Results section (\input into the manuscript)
│   ├── references.bib
│   └── figures/              # manuscript figures
└── simulation/
    ├── RADS_simulation.ipynb # Colab-ready validation notebook
    ├── rads_core.py          # reusable engine (Eqs. 1–9)
    ├── rads_analysis.py      # regenerates the figures
    ├── build_nb.py           # rebuilds the notebook from source
    └── figures/              # generated figures
```

---

## Data availability

All code required to reproduce the simulation study and its figures is available in this
repository ([`simulation/`](simulation/)). No external or personal data were used; the
evaluation is based on synthetic scenarios generated from the parameter ranges described
in the paper.

## Citation

> Sharma, P. *Taming the Ransomware Threats: Leveraging Prospect Theory for Rational
> Payment Decisions.* (in preparation).
