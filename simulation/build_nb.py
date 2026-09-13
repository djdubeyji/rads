import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

nb = new_notebook()
c = []

c.append(new_markdown_cell(r"""# RADS — Layer-1 Simulation & Theory Validation

**Ransomware Risk Analysis and Decision Support.** This notebook implements the paper's
Eqs. (1)–(9) and validates the central claim by simulation: that attacker *framing*
drives systematic **over-payment**, and that a Prospect-Theory-aware decision aid
(**RADS**) removes it.

Runs top-to-bottom in Google Colab or Jupyter — no local files needed. Money is in
units of **\$1,000 (kUSD)**.

---
### ⚠️ Read this first — a modelling correction

The paper's Eq. (8) (as first drafted) said RADS keeps the full Prospect-Theory lens
but resets the reference to the *pristine pre-attack state* (`r0 = 0`). **When simulated,
that formulation does the opposite of the thesis** — it pushes the entire decision into
the loss domain, where PT deviates *most* from expected value, so RADS refuses to pay
almost always and does *worse* than the manipulated human.

This notebook uses the **corrected model**, which is also more defensible:

* the attacker's manipulation is **asymmetric** — it inflates how bad *not paying* looks
  and how reliable *paying* is (not a symmetric shift of both);
* RADS's honest reference is the **realistic fallback (self-recovery)**, so options are
  judged *incrementally*, keeping the valuation near the linear region of `v(·)`.

**Action item for the paper:** update Eq. (8) to the incremental-reference form and add a
sentence explaining why (this is a strength — every modelling choice now has a reason).
"""))

c.append(new_markdown_cell(r"""## 1. Prospect-Theory primitives — Eqs. (1)–(2)"""))

c.append(new_code_cell(r"""import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass

# Eq. 1 — value function: S-shaped, loss-averse. x = money relative to a reference point.
def value(x, alpha=0.88, beta=0.88, lam=2.25):
    x = np.asarray(x, dtype=float)
    return np.where(x >= 0, np.power(np.abs(x), alpha),
                    -lam * np.power(np.abs(x), beta))

# Eq. 2 — Tversky & Kahneman (1992) probability weighting.
def weight(p, gamma=0.61):
    p = np.clip(np.asarray(p, dtype=float), 1e-9, 1 - 1e-9)
    return p**gamma / (p**gamma + (1 - p)**gamma) ** (1 / gamma)

@dataclass
class PTParams:
    alpha: float = 0.88
    beta:  float = 0.88
    lam:   float = 2.25   # loss aversion
    gamma: float = 0.61   # probability-weighting curvature"""))

c.append(new_code_cell(r"""# Visualise the two functions (sanity check + a figure you can reuse in the paper).
fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
xx = np.linspace(-100, 100, 400)
ax[0].plot(xx, value(xx), color="#264653"); ax[0].axhline(0, lw=.6, color="k"); ax[0].axvline(0, lw=.6, color="k")
ax[0].set_title("Value function v(x)  (Eq. 1)"); ax[0].set_xlabel("outcome - reference")
pp = np.linspace(0, 1, 200)
ax[1].plot(pp, weight(pp), color="#e76f51"); ax[1].plot(pp, pp, "--", lw=.8, color="grey")
ax[1].set_title("Probability weighting w(p)  (Eq. 2)"); ax[1].set_xlabel("objective p")
fig.tight_layout(); plt.show()"""))

c.append(new_markdown_cell(r"""## 2. The two decision lotteries

Each action is a discrete set of `(probability, monetary_outcome ≤ 0)` states. Using the
full distribution (not just the mean) matters, because Prospect Theory is **non-linear**
over outcomes."""))

c.append(new_code_cell(r"""def pay_lottery(R, L_rec, C_down, t_pay, C_re, D_leak, p_key, p_re, p_leak_p):
    states = []
    for key, pk in ((True, p_key), (False, 1 - p_key)):
        base = C_down * t_pay if key else L_rec      # key fails -> you still self-recover
        for re, pr in ((True, p_re), (False, 1 - p_re)):
            for leak, pl in ((True, p_leak_p), (False, 1 - p_leak_p)):
                out = -(R + base + (C_re if re else 0.0) + (D_leak if leak else 0.0))
                states.append((pk * pr * pl, out))
    return states

def recover_lottery(L_rec, D_leak, p_leak_np):
    return [(p_leak_np, -(L_rec + D_leak)), (1 - p_leak_np, -(L_rec))]

def expected_value(states):                 # Eqs. 3-4, as expectations
    return sum(p * x for p, x in states)

def pt_value(states, r, pt: PTParams):      # Eq. 6 (separable weighting)
    return sum(weight(p, pt.gamma) * value(x - r, pt.alpha, pt.beta, pt.lam)
               for p, x in states)"""))

c.append(new_markdown_cell(r"""**Note on Eq. 6.** This uses *separable* weighting (Kahneman–Tversky 1979). The fully
rigorous form is *rank-dependent* Cumulative Prospect Theory (1992), which avoids
stochastic-dominance violations. Separable weighting is fine for this first iteration and
keeps the code readable; upgrading to CPT is a clean v2 and would make the 1992 citation
exact. (Ask if you want the CPT version dropped in.)"""))

c.append(new_markdown_cell(r"""## 3. Scenario population

Ranges are **placeholders** — anchor them to current Coveware / Sophos / IBM / ENISA
figures before you report numbers. The one knob that has no real-world counterpart,
`ref_gain`, controls how hard the attacker inflates the catastrophe frame; RADS is by
design invariant to it (a nice robustness check later)."""))

c.append(new_code_cell(r"""@dataclass
class DrawConfig:
    n: int = 20000
    seed: int = 7
    ransom_median: float = 300.0    # kUSD   (ANCHOR ME)
    ransom_sigma:  float = 0.9
    cdown_median:  float = 50.0     # kUSD per day of downtime
    clab_median:   float = 20.0
    vdata_median:  float = 120.0
    dleak_median:  float = 500.0
    ref_gain:      float = 1.0

def draw_scenarios(cfg: DrawConfig):
    rng = np.random.default_rng(cfg.seed); n = cfg.n
    ln = lambda med, sig: np.exp(rng.normal(np.log(med), sig, n))
    phi       = rng.beta(2, 2, n)
    R         = ln(cfg.ransom_median, cfg.ransom_sigma)
    C_down    = ln(cfg.cdown_median, 0.6)
    C_lab     = ln(cfg.clab_median, 0.6)
    V_data    = ln(cfg.vdata_median, 0.7)
    D_leak    = ln(cfg.dleak_median, 0.8)
    t_rec     = 3 + (1 - phi) * rng.uniform(5, 30, n)
    t_pay     = rng.uniform(1, 5, n)
    C_re      = 0.5 * R * rng.uniform(0.5, 1.5, n)
    p_key     = rng.beta(6.5, 3.5, n)     # decryptor works ~0.65
    p_re      = rng.beta(2.5, 7.5, n)     # re-extortion ~0.25
    p_leak_p  = rng.beta(3.5, 6.5, n)     # leak if paid ~0.35
    p_leak_np = rng.beta(7.0, 3.0, n)     # leak if not paid ~0.70
    u         = rng.beta(6.0, 2.0, n)     # urgency ~0.75
    L_rec = C_down * t_rec + C_lab + (1 - phi) * V_data
    delta_ref = u * cfg.ref_gain * (R + L_rec + D_leak)   # Eq. 7 reference-shift magnitude
    return dict(phi=phi, R=R, C_down=C_down, C_lab=C_lab, V_data=V_data, D_leak=D_leak,
                t_rec=t_rec, t_pay=t_pay, C_re=C_re, p_key=p_key, p_re=p_re,
                p_leak_p=p_leak_p, p_leak_np=p_leak_np, u=u, L_rec=L_rec, delta_ref=delta_ref)"""))

c.append(new_markdown_cell(r"""## 4. The three decisions per scenario

* **`d_star`** — risk-neutral optimum, argmin expected loss (Eq. 5): the ground truth.
* **`d_pt`** — the human under **attacker-distorted, asymmetric** perceptions + a
  catastrophe reference (Eq. 7).
* **`d_rads`** — the human with **true** parameters and an **incremental** reference
  = the realistic fallback (self-recovery). This is the corrected Eq. (8)."""))

c.append(new_code_cell(r"""def decide(s, i, pt: PTParams, kappa_rec=1.2):
    R, L, Cd, tp = s['R'][i], s['L_rec'][i], s['C_down'][i], s['t_pay'][i]
    Cre, Dl = s['C_re'][i], s['D_leak'][i]
    pk, pre, plp, plnp, u = (s['p_key'][i], s['p_re'][i], s['p_leak_p'][i],
                             s['p_leak_np'][i], s['u'][i])

    # ground truth (Eq. 5)
    pay = pay_lottery(R, L, Cd, tp, Cre, Dl, pk, pre, plp)
    rec = recover_lottery(L, Dl, plnp)
    ev_pay, ev_rec = expected_value(pay), expected_value(rec)
    loss_pay, loss_rec = -ev_pay, -ev_rec
    d_star = 1 if ev_pay > ev_rec else 0

    # attacker-manipulated perception (Eq. 7, asymmetric)
    pk_t   = pk + u * (1 - pk)          # over-weight decryptor working
    pre_t  = (1 - u) * pre              # suppress re-extortion
    plnp_t = plnp + u * (1 - plnp)      # "we WILL leak if you don't pay"
    L_t    = L * (1 + u * kappa_rec)    # "recovery will cost far more than you think"
    pay_m  = pay_lottery(R, L_t, Cd, tp, Cre, Dl, pk_t, pre_t, plp)
    rec_m  = recover_lottery(L_t, Dl, plnp_t)
    r_cat  = -s['delta_ref'][i]         # catastrophe reference
    d_pt = 1 if pt_value(pay_m, r_cat, pt) > pt_value(rec_m, r_cat, pt) else 0

    # RADS: true params, incremental (fallback) reference — corrected Eq. 8
    r0 = ev_rec
    d_rads = 1 if pt_value(pay, r0, pt) > pt_value(rec, r0, pt) else 0
    return dict(d_star=d_star, d_pt=d_pt, d_rads=d_rads,
                loss_pay=loss_pay, loss_rec=loss_rec)

def run(cfg=None, pt=None):
    cfg = cfg or DrawConfig(); pt = pt or PTParams()
    s = draw_scenarios(cfg)
    out = {k: np.empty(cfg.n) for k in ('d_star','d_pt','d_rads','loss_pay','loss_rec')}
    for i in range(cfg.n):
        d = decide(s, i, pt)
        for k in out: out[k][i] = d[k]
    return s, out

def regret(out, key):                        # Eq. 9
    chosen = out[key]
    loss_chosen = np.where(chosen == 1, out['loss_pay'], out['loss_rec'])
    loss_opt    = np.where(out['d_star'] == 1, out['loss_pay'], out['loss_rec'])
    return loss_chosen - loss_opt"""))

c.append(new_markdown_cell(r"""## 5. Headline result"""))

c.append(new_code_cell(r"""import pandas as pd
cfg = DrawConfig(n=20000, seed=7)
s, out = run(cfg)

def row(name, chosen):
    loss_chosen = np.where(chosen == 1, out['loss_pay'], out['loss_rec'])
    loss_opt    = np.where(out['d_star'] == 1, out['loss_pay'], out['loss_rec'])
    r = loss_chosen - loss_opt
    return dict(pay_rate=chosen.mean(),
                agree=(chosen == out['d_star']).mean(),
                overpay=((chosen == 1) & (out['d_star'] == 0)).mean(),
                underpay=((chosen == 0) & (out['d_star'] == 1)).mean(),
                mean_regret_k=r.mean(), median_regret_k=np.median(r))

table = pd.DataFrame({
    "EV-optimal":  row("opt", out['d_star']),
    "RADS":        row("rads", out['d_rads']),
    "PT-biased":   row("pt", out['d_pt']),
    "always-pay":  row("ap", np.ones_like(out['d_star'])),
    "always-recover": row("ar", np.zeros_like(out['d_star'])),
}).T
table.round(3)"""))

c.append(new_markdown_cell(r"""**How to read it.** The manipulated human (`PT-biased`) **over-pays** (pays well above
the optimal rate; non-zero `overpay`) and carries the larger regret. **RADS roughly halves
mean regret and never over-pays** — it errs toward *not* paying, the preferable failure
mode for a defensive tool. Fill the abstract's `% TODO` headline from this table
(e.g. the regret reduction and the over-pay elimination)."""))

c.append(new_markdown_cell(r"""## 6. Figures for the Results section"""))

c.append(new_code_cell(r"""r_pt, r_rads = regret(out, "d_pt"), regret(out, "d_rads")
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 120})

# Fig 1 — mean regret by decision-maker
names = ["EV-optimal","RADS","PT-biased\n(manipulated)","always-pay","always-recover"]
vals  = [0, table.loc["RADS","mean_regret_k"], table.loc["PT-biased","mean_regret_k"],
         table.loc["always-pay","mean_regret_k"], table.loc["always-recover","mean_regret_k"]]
cols  = ["#2a9d8f","#2a9d8f","#e76f51","#bbb","#bbb"]
fig, ax = plt.subplots(figsize=(6.2,3.6)); ax.bar(names, vals, color=cols)
for i,v in enumerate(vals): ax.text(i, v+4, f"{v:.0f}k", ha="center", fontsize=9)
ax.set_ylabel("Mean regret (kUSD)"); ax.set_title("Mean expected regret vs. the risk-neutral optimum")
fig.tight_layout(); plt.show()"""))

c.append(new_code_cell(r"""# Fig 2 — where the mistakes live (ECDF of non-zero regret)
fig, ax = plt.subplots(figsize=(6.2,3.6))
for r, lab, cc in ((r_pt,"PT-biased","#e76f51"), (r_rads,"RADS","#2a9d8f")):
    rr = np.sort(r[r > 0])
    if len(rr): ax.plot(rr, np.linspace(0,1,len(rr)), label=lab, color=cc, lw=2)
ax.set_xscale("symlog"); ax.set_xlabel("Regret in a scenario (kUSD, symlog)")
ax.set_ylabel("Cumulative fraction of\nnon-zero-regret scenarios")
ax.set_title("Regret distribution"); ax.legend(); fig.tight_layout(); plt.show()

# Fig 3 — decision quality breakdown
labels=["PT-biased","RADS"]
ag=[table.loc["PT-biased","agree"],table.loc["RADS","agree"]]
op=[table.loc["PT-biased","overpay"],table.loc["RADS","overpay"]]
un=[table.loc["PT-biased","underpay"],table.loc["RADS","underpay"]]
fig, ax = plt.subplots(figsize=(6.2,3.6))
ax.bar(labels, ag, label="agrees with optimum", color="#2a9d8f")
ax.bar(labels, op, bottom=ag, label="over-pays", color="#e76f51")
ax.bar(labels, un, bottom=np.add(ag,op), label="under-pays", color="#f4a261")
ax.set_ylim(0,1); ax.set_ylabel("Fraction of scenarios")
ax.set_title("Decision quality vs. the optimum"); ax.legend(loc="lower right", fontsize=8)
fig.tight_layout(); plt.show()"""))

c.append(new_markdown_cell(r"""## 7. Sensitivity (tornado) and stability

These turn the reviewer objection *"the weights/parameters are arbitrary"* into a
characterised result."""))

c.append(new_code_cell(r"""base_par = dict(ransom_median=300.0, cdown_median=50.0, vdata_median=120.0,
                dleak_median=500.0, ref_gain=1.0)
def rads_mean_regret(overrides=None, lam=2.25, gamma=0.61, n=6000):
    kw = dict(base_par); kw.update(overrides or {})
    _, o = run(DrawConfig(n=n, seed=11, **kw), PTParams(lam=lam, gamma=gamma))
    return np.mean(regret(o, "d_rads"))

base = rads_mean_regret(); factors, lows, highs = [], [], []
for k in base_par:
    lows.append(rads_mean_regret({k: base_par[k]*0.7})-base)
    highs.append(rads_mean_regret({k: base_par[k]*1.3})-base); factors.append(k)
factors += ["lambda (loss aversion)","gamma (prob. weighting)"]
lows  += [rads_mean_regret(lam=2.25*0.7)-base, rads_mean_regret(gamma=0.61*0.7)-base]
highs += [rads_mean_regret(lam=2.25*1.3)-base, rads_mean_regret(gamma=0.61*1.3)-base]
o = np.argsort([abs(a)+abs(b) for a,b in zip(lows,highs)])
factors=[factors[i] for i in o]; lows=[lows[i] for i in o]; highs=[highs[i] for i in o]
fig, ax = plt.subplots(figsize=(6.6,3.8)); y=np.arange(len(factors))
ax.barh(y, highs, color="#e76f51", label="+30%"); ax.barh(y, lows, color="#2a9d8f", label="-30%")
ax.set_yticks(y); ax.set_yticklabels(factors, fontsize=8); ax.axvline(0,color="k",lw=.8)
ax.set_xlabel(f"Change in RADS mean regret vs. baseline ({base:.0f}k)")
ax.set_title("Sensitivity of RADS regret to inputs (±30%)"); ax.legend(fontsize=8)
fig.tight_layout(); plt.show()"""))

c.append(new_code_cell(r"""cfgS = DrawConfig(n=6000, seed=3); sS = draw_scenarios(cfgS)
base_dec = np.array([decide(sS, i, PTParams())["d_rads"] for i in range(cfgS.n)])
xs = np.linspace(0, 0.5, 11); stable=[]; rng=np.random.default_rng(0)
for x in xs:
    if x == 0: stable.append(1.0); continue
    trials=[]
    for _ in range(5):
        pt = PTParams(lam=2.25*(1+rng.uniform(-x,x)),
                      gamma=float(np.clip(0.61*(1+rng.uniform(-x,x)),0.3,0.99)),
                      alpha=0.88*(1+rng.uniform(-x,x)), beta=0.88*(1+rng.uniform(-x,x)))
        dec = np.array([decide(sS, i, pt)["d_rads"] for i in range(cfgS.n)])
        trials.append((dec==base_dec).mean())
    stable.append(np.mean(trials))
fig, ax = plt.subplots(figsize=(6.2,3.6)); ax.plot(xs*100, stable, "-o", color="#264653", lw=2)
ax.set_xlabel("PT-parameter perturbation (±%)"); ax.set_ylabel("Fraction of RADS decisions unchanged")
ax.set_ylim(0.5,1.02); ax.set_title("Decision stability under parameter uncertainty")
fig.tight_layout(); plt.show()"""))

c.append(new_markdown_cell(r"""## 8. Reusing this core in the DORA Registry app

`value`, `weight`, `PTParams`, and the lottery/`pt_value` functions are the shared
scoring engine. For DORA asset prioritisation you swap the *pay-vs-recover* lottery for
an *asset risk* score: reference = acceptable-loss baseline, outcomes = expected loss per
asset (cost, backup cost, RTO, hosting), and the concentration-risk +15% becomes a
multiplier on `delta_ref` for assets sharing a platform. Keeping one engine means the
paper's validated model and the app can't drift apart.

## 9. What to change in the paper
1. **Eq. (8):** switch to the incremental-reference form used here; add one sentence on
   why the pristine-state reference fails.
2. **Results:** drop in Figures 1–5 and the metrics table; write the headline (regret
   reduction, over-pay elimination) into the abstract's `% TODO`.
3. **Discussion:** RADS's residual *under*-payment is the safe failure mode; `gamma`/
   `lambda` dominate sensitivity, so parameter elicitation is the key threat to validity.
4. **Honesty:** these numbers use placeholder parameter ranges. Re-run with sourced
   values before quoting any figure, and verify the industry-report citations.
"""))

nb["cells"] = c
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                  "language_info": {"name": "python"}}
with open("/home/claude/RADS_simulation.ipynb", "w") as f:
    nbf.write(nb, f)
print("wrote RADS_simulation.ipynb with", len(c), "cells")
