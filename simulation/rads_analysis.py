"""Generate the Results figures + metrics table from the RADS core model."""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rads_core import (DrawConfig, PTParams, run, summarise, regret,
                       draw_scenarios, decide)

plt.rcParams.update({"figure.dpi": 130, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
OUT = "/home/claude/figs"
import os; os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- main run
cfg = DrawConfig(n=20000, seed=7)
s, out = run(cfg)
res = summarise(out)
r_pt, r_rads = regret(out, "d_pt"), regret(out, "d_rads")

# ---- Fig 1: mean regret by decision-maker
names = ["EV-optimal", "RADS", "PT-biased\n(manipulated)", "always-pay", "always-recover"]
vals  = [0.0, res["RADS"]["mean_regret"], res["PT-biased"]["mean_regret"],
         res["always-pay"]["mean_regret"], res["always-recover"]["mean_regret"]]
colors = ["#2a9d8f", "#2a9d8f", "#e76f51", "#bbb", "#bbb"]
fig, ax = plt.subplots(figsize=(6.2, 3.6))
ax.bar(names, vals, color=colors)
for i, v in enumerate(vals):
    ax.text(i, v + 4, f"{v:.0f}k", ha="center", fontsize=9)
ax.set_ylabel("Mean regret (kUSD)")
ax.set_title("Mean expected regret vs. the risk-neutral optimum")
fig.tight_layout(); fig.savefig(f"{OUT}/fig1_mean_regret.png"); plt.close(fig)

# ---- Fig 2: regret tail (ECDF, positive regret only)
fig, ax = plt.subplots(figsize=(6.2, 3.6))
for r, lab, c in ((r_pt, "PT-biased", "#e76f51"), (r_rads, "RADS", "#2a9d8f")):
    rr = np.sort(r[r > 0])
    if len(rr):
        ax.plot(rr, np.linspace(0, 1, len(rr)), label=lab, color=c, lw=2)
ax.set_xscale("symlog")
ax.set_xlabel("Regret in a scenario (kUSD, symlog)")
ax.set_ylabel("Cumulative fraction of\nnon-zero-regret scenarios")
ax.set_title("Where the mistakes live: regret distribution")
ax.legend(); fig.tight_layout(); fig.savefig(f"{OUT}/fig2_regret_ecdf.png"); plt.close(fig)

# ---- Fig 3: decision-outcome breakdown
labels = ["PT-biased", "RADS"]
agree   = [res["PT-biased"]["agreement"],  res["RADS"]["agreement"]]
overpay = [res["PT-biased"]["overpay"],    res["RADS"]["overpay"]]
under   = [res["PT-biased"]["underpay"],   res["RADS"]["underpay"]]
fig, ax = plt.subplots(figsize=(6.2, 3.6))
ax.bar(labels, agree, label="agrees with optimum", color="#2a9d8f")
ax.bar(labels, overpay, bottom=agree, label="over-pays", color="#e76f51")
ax.bar(labels, under, bottom=np.add(agree, overpay), label="under-pays", color="#f4a261")
ax.set_ylabel("Fraction of scenarios"); ax.set_ylim(0, 1)
ax.set_title("Decision quality vs. the optimum")
ax.legend(loc="lower right", fontsize=8)
fig.tight_layout(); fig.savefig(f"{OUT}/fig3_decision_breakdown.png"); plt.close(fig)

# ---- Fig 4: sensitivity tornado (effect of +/-30% on RADS mean regret)
base_par = dict(ransom_median=300.0, cdown_median=50.0, vdata_median=120.0,
                dleak_median=500.0, ref_gain=1.0)
def rads_mean_regret(overrides=None, lam=2.25, gamma=0.61, n=6000):
    kw = dict(base_par); 
    if overrides: kw.update(overrides)
    c = DrawConfig(n=n, seed=11, **kw)
    _, o = run(c, PTParams(lam=lam, gamma=gamma))
    return np.mean(regret(o, "d_rads"))
base = rads_mean_regret()
factors, lows, highs = [], [], []
for key in base_par:
    lo = rads_mean_regret({key: base_par[key]*0.7})
    hi = rads_mean_regret({key: base_par[key]*1.3})
    factors.append(key); lows.append(lo - base); highs.append(hi - base)
for lab, kw in (("lambda (loss aversion)", dict(lam_lo=2.25*0.7, lam_hi=2.25*1.3)),
                ("gamma (prob. weighting)", dict(g_lo=0.61*0.7, g_hi=0.61*1.3))):
    if "lam_lo" in kw:
        lo = rads_mean_regret(lam=kw["lam_lo"]); hi = rads_mean_regret(lam=kw["lam_hi"])
    else:
        lo = rads_mean_regret(gamma=kw["g_lo"]); hi = rads_mean_regret(gamma=kw["g_hi"])
    factors.append(lab); lows.append(lo - base); highs.append(hi - base)
order = np.argsort([abs(l)+abs(h) for l, h in zip(lows, highs)])
factors = [factors[i] for i in order]; lows=[lows[i] for i in order]; highs=[highs[i] for i in order]
fig, ax = plt.subplots(figsize=(6.4, 3.8)); y = np.arange(len(factors))
ax.barh(y, [h for h in highs], color="#e76f51", label="+30%")
ax.barh(y, [l for l in lows],  color="#2a9d8f", label="-30%")
ax.set_yticks(y); ax.set_yticklabels(factors, fontsize=8)
ax.axvline(0, color="k", lw=.8)
ax.set_xlabel(f"Change in RADS mean regret vs. baseline ({base:.0f}k)")
ax.set_title("Sensitivity of RADS regret to inputs (\u00b130%)")
ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(f"{OUT}/fig4_tornado.png"); plt.close(fig)

# ---- Fig 5: decision-stability curve under PT-parameter perturbation
cfgS = DrawConfig(n=6000, seed=3); sS = draw_scenarios(cfgS)
base_pt = PTParams()
base_dec = np.array([decide(sS, i, base_pt)["d_rads"] for i in range(cfgS.n)])
xs = np.linspace(0, 0.5, 11); stable = []
rng = np.random.default_rng(0)
for x in xs:
    if x == 0: stable.append(1.0); continue
    trials = []
    for _ in range(5):
        pt = PTParams(lam=2.25*(1+rng.uniform(-x, x)),
                      gamma=float(np.clip(0.61*(1+rng.uniform(-x, x)), 0.3, 0.99)),
                      alpha=0.88*(1+rng.uniform(-x, x)), beta=0.88*(1+rng.uniform(-x, x)))
        dec = np.array([decide(sS, i, pt)["d_rads"] for i in range(cfgS.n)])
        trials.append(np.mean(dec == base_dec))
    stable.append(np.mean(trials))
fig, ax = plt.subplots(figsize=(6.2, 3.6))
ax.plot(xs*100, stable, "-o", color="#264653", lw=2)
ax.set_xlabel("PT-parameter perturbation (\u00b1%)")
ax.set_ylabel("Fraction of RADS decisions unchanged")
ax.set_ylim(0.5, 1.02); ax.set_title("Decision stability under parameter uncertainty")
fig.tight_layout(); fig.savefig(f"{OUT}/fig5_stability.png"); plt.close(fig)

# ---- text summary
print("FIGURES WRITTEN:", os.listdir(OUT))
print(f"\nRADS mean regret baseline: {base:.1f}k")
print(f"tornado factors (sorted): {factors}")
print(f"stability at +/-50%: {stable[-1]:.3f}")
for name, m in res.items():
    print(f"{name:16s} agree={m['agreement']:.3f} overpay={m['overpay']:.3f} "
          f"underpay={m['underpay']:.3f} mean_regret={m['mean_regret']:.1f}k")
