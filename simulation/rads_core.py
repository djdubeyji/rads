"""
RADS Layer-1 simulation — core model.
Implements the paper's Eqs. 1-9. Money is in units of $1,000 (kUSD).
This file is import-safe so the DORA app can reuse the scoring core.
"""
import numpy as np
from dataclasses import dataclass, field

# ---------------------------------------------------------------- PT primitives
# Eq. 1 — value function (S-shaped, loss-averse). x is money relative to reference.
def value(x, alpha=0.88, beta=0.88, lam=2.25):
    x = np.asarray(x, dtype=float)
    return np.where(x >= 0, np.power(np.abs(x), alpha),
                    -lam * np.power(np.abs(x), beta))

# Eq. 2 — Tversky-Kahneman (1992) probability weighting.
def weight(p, gamma=0.61):
    p = np.clip(np.asarray(p, dtype=float), 1e-9, 1 - 1e-9)
    return p**gamma / (p**gamma + (1 - p)**gamma) ** (1 / gamma)

# ---------------------------------------------------------------- PT parameters
@dataclass
class PTParams:
    alpha: float = 0.88
    beta: float = 0.88
    lam: float = 2.25       # loss aversion
    gamma: float = 0.61     # probability weighting curvature

# ------------------------------------------------ build the two decision lotteries
# Each action -> list of (probability, monetary_outcome<=0) states.
def pay_lottery(R, L_rec, C_down, t_pay, C_re, D_leak, p_key, p_re, p_leak_p):
    states = []
    for key, pk in ((True, p_key), (False, 1 - p_key)):
        base = C_down * t_pay if key else L_rec  # key fails -> you still self-recover
        for re, pr in ((True, p_re), (False, 1 - p_re)):
            for leak, pl in ((True, p_leak_p), (False, 1 - p_leak_p)):
                out = -(R + base + (C_re if re else 0.0) + (D_leak if leak else 0.0))
                states.append((pk * pr * pl, out))
    return states

def recover_lottery(L_rec, D_leak, p_leak_np):
    return [(p_leak_np,       -(L_rec + D_leak)),
            (1 - p_leak_np,   -(L_rec))]

# ---------------------------------------------------------------- valuations
def expected_value(states):                      # Eqs. 3-4 (as expectations)
    return sum(p * x for p, x in states)

def pt_value(states, r, pt: PTParams):           # Eq. 6 (separable weighting)
    return sum(weight(p, pt.gamma) * value(x - r, pt.alpha, pt.beta, pt.lam)
               for p, x in states)

# ---------------------------------------------------------------- scenario draw
@dataclass
class DrawConfig:
    n: int = 20000
    seed: int = 7
    # medians / shape knobs — anchor these to current Coveware / Sophos / IBM figures.
    ransom_median: float = 300.0      # kUSD
    ransom_sigma: float = 0.9
    cdown_median: float = 50.0        # kUSD per day of downtime
    clab_median: float = 20.0         # kUSD labour
    vdata_median: float = 120.0       # kUSD value of current data
    dleak_median: float = 500.0       # kUSD leak/reputational damage
    ref_gain: float = 1.0             # how hard the attacker inflates the catastrophe frame

def draw_scenarios(cfg: DrawConfig):
    rng = np.random.default_rng(cfg.seed)
    n = cfg.n
    def lognorm(med, sig): return np.exp(rng.normal(np.log(med), sig, n))

    phi        = rng.beta(2, 2, n)                       # backup coverage (feasibility)
    R          = lognorm(cfg.ransom_median, cfg.ransom_sigma)
    C_down     = lognorm(cfg.cdown_median, 0.6)
    C_lab      = lognorm(cfg.clab_median, 0.6)
    V_data     = lognorm(cfg.vdata_median, 0.7)
    D_leak     = lognorm(cfg.dleak_median, 0.8)
    t_rec      = 3 + (1 - phi) * rng.uniform(5, 30, n)   # worse backups -> longer recovery
    t_pay      = rng.uniform(1, 5, n)
    C_re       = 0.5 * R * rng.uniform(0.5, 1.5, n)
    p_key      = rng.beta(6.5, 3.5, n)                   # decryptor works ~0.65
    p_re       = rng.beta(2.5, 7.5, n)                   # re-extortion ~0.25
    p_leak_p   = rng.beta(3.5, 6.5, n)                   # leak if paid ~0.35
    p_leak_np  = rng.beta(7.0, 3.0, n)                   # leak if not paid ~0.70
    u          = rng.beta(6.0, 2.0, n)                   # urgency ~0.75

    L_rec = C_down * t_rec + C_lab + (1 - phi) * V_data
    # Eq. 7 — attacker's reference shift magnitude (perceived catastrophe baseline)
    delta_ref = u * cfg.ref_gain * (R + L_rec + D_leak)

    return dict(phi=phi, R=R, C_down=C_down, C_lab=C_lab, V_data=V_data, D_leak=D_leak,
                t_rec=t_rec, t_pay=t_pay, C_re=C_re, p_key=p_key, p_re=p_re,
                p_leak_p=p_leak_p, p_leak_np=p_leak_np, u=u, L_rec=L_rec,
                delta_ref=delta_ref)

# ---------------------------------------------------------------- decide one scenario
def decide(s, i, pt: PTParams, kappa_rec=1.2):
    """Return dict of the three decisions + the loss of each action. PAY=1, RECOVER=0.

    Corrected model (see notebook narrative):
      * ground truth  d_star : risk-neutral argmin expected loss (Eq. 5)
      * manipulated   d_pt   : human evaluates via PT with ATTACKER-DISTORTED,
                               ASYMMETRIC perceptions + a catastrophe reference
      * RADS-assisted d_rads : human evaluates via PT with TRUE parameters and an
                               INCREMENTAL reference = the realistic fallback (recover),
                               which keeps the valuation in the ~linear region of v(.)
    """
    R, L, Cd, tp = s['R'][i], s['L_rec'][i], s['C_down'][i], s['t_pay'][i]
    Cre, Dl = s['C_re'][i], s['D_leak'][i]
    pk, pre, plp, plnp, u = (s['p_key'][i], s['p_re'][i], s['p_leak_p'][i],
                             s['p_leak_np'][i], s['u'][i])

    # ---- true lotteries -> ground truth (Eq. 5)
    pay = pay_lottery(R, L, Cd, tp, Cre, Dl, pk, pre, plp)
    rec = recover_lottery(L, Dl, plnp)
    ev_pay, ev_rec = expected_value(pay), expected_value(rec)
    loss_pay, loss_rec = -ev_pay, -ev_rec
    d_star = 1 if ev_pay > ev_rec else 0

    # ---- manipulated perception (Eq. 7, asymmetric)
    pk_t   = pk + u * (1 - pk)          # over-weight decryptor working
    pre_t  = (1 - u) * pre              # suppress re-extortion
    plnp_t = plnp + u * (1 - plnp)      # "we WILL leak if you don't pay"
    L_t    = L * (1 + u * kappa_rec)    # "self-recovery will cost far more than you think"
    pay_m  = pay_lottery(R, L_t, Cd, tp, Cre, Dl, pk_t, pre_t, plp)
    rec_m  = recover_lottery(L_t, Dl, plnp_t)
    r_cat  = -s['delta_ref'][i]         # catastrophe reference
    d_pt = 1 if pt_value(pay_m, r_cat, pt) > pt_value(rec_m, r_cat, pt) else 0

    # ---- RADS: true params, incremental (fallback) reference = -E[loss_recover]
    r0 = ev_rec                          # reference at the realistic fallback outcome
    d_rads = 1 if pt_value(pay, r0, pt) > pt_value(rec, r0, pt) else 0

    return dict(d_star=d_star, d_pt=d_pt, d_rads=d_rads,
                loss_pay=loss_pay, loss_rec=loss_rec)

def run(cfg: DrawConfig = None, pt: PTParams = None):
    cfg = cfg or DrawConfig()
    pt = pt or PTParams()
    s = draw_scenarios(cfg)
    out = {k: np.empty(cfg.n) for k in
           ('d_star', 'd_pt', 'd_rads', 'loss_pay', 'loss_rec')}
    for i in range(cfg.n):
        d = decide(s, i, pt)
        for k in out:
            out[k][i] = d[k]
    return s, out

# ---------------------------------------------------------------- metrics
def regret(out, decision_key):
    """Eq. 9 — loss(chosen) - loss(optimal), per scenario, in kUSD."""
    chosen = out[decision_key]
    loss_chosen = np.where(chosen == 1, out['loss_pay'], out['loss_rec'])
    loss_opt = np.where(out['d_star'] == 1, out['loss_pay'], out['loss_rec'])
    return loss_chosen - loss_opt

def summarise(out):
    res = {}
    for name, key in (('PT-biased', 'd_pt'), ('RADS', 'd_rads'),
                      ('always-pay', None), ('always-recover', None)):
        if key is None:
            chosen = np.ones_like(out['d_star']) if name == 'always-pay' \
                     else np.zeros_like(out['d_star'])
            loss_chosen = np.where(chosen == 1, out['loss_pay'], out['loss_rec'])
            loss_opt = np.where(out['d_star'] == 1, out['loss_pay'], out['loss_rec'])
            r = loss_chosen - loss_opt
        else:
            r = regret(out, key)
            chosen = out[key]
        agree = np.mean(chosen == out['d_star'])
        overpay = np.mean((chosen == 1) & (out['d_star'] == 0))
        underpay = np.mean((chosen == 0) & (out['d_star'] == 1))
        res[name] = dict(agreement=agree, overpay=overpay, underpay=underpay,
                         mean_regret=np.mean(r), median_regret=np.median(r))
    return res

if __name__ == '__main__':
    s, out = run()
    import json
    res = summarise(out)
    print(f"pay-rate optimal   : {out['d_star'].mean():.3f}")
    print(f"pay-rate PT-biased : {out['d_pt'].mean():.3f}")
    print(f"pay-rate RADS      : {out['d_rads'].mean():.3f}")
    print()
    for name, m in res.items():
        print(f"{name:16s} agree={m['agreement']:.3f}  overpay={m['overpay']:.3f}  "
              f"underpay={m['underpay']:.3f}  mean_regret={m['mean_regret']:8.1f}k  "
              f"median_regret={m['median_regret']:7.1f}k")
