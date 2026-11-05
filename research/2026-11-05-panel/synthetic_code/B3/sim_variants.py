"""SYNTHETIC variants: ambiguity vs stop size relative to 1-min bar range; overlap with persistent signal."""
import numpy as np
rng = np.random.default_rng(7)
def one_trade(path, stop, tgt):
    bars = path.reshape(-1, 12)
    for bar in bars:
        hi, lo = bar.max(), bar.min()
        hs, ht = lo <= -stop, hi >= tgt
        if hs and ht:
            i_s = np.argmax(bar <= -stop); i_t = np.argmax(bar >= tgt)
            return -stop, tgt, (-stop if i_s < i_t else tgt)
        if hs: return -stop, -stop, -stop
        if ht: return tgt, tgt, tgt
    return (path[-1],) * 3
print("=== SYNTHETIC same-bar ambiguity vs stop/bar-range ratio (target=1.5*stop, 60 bars) ===")
print("stop/avg1minRange  ambiguous%  cons  truth  optim  spread(R/trade)")
for ratio in [2.0, 1.0, 0.5, 0.33]:
    s = 0.35 / ratio  # tick sd scaled so avg 1-min range ~ stop/ratio
    cons, opt, tru = [], [], []
    for _ in range(8000):
        path = np.cumsum(rng.standard_normal(60*12) * s)
        c, o, t = one_trade(path, 1.0, 1.5); cons.append(c); opt.append(o); tru.append(t)
    cons, opt, tru = map(np.array, (cons, opt, tru))
    print(f"{ratio:>8.2f}  {100*(cons!=opt).mean():9.1f}  {cons.mean():+.3f} {tru.mean():+.3f} {opt.mean():+.3f}  {opt.mean()-cons.mean():+.3f}")
print("\n=== SYNTHETIC overlapping labels with PERSISTENT (AR1 rho=.98) noise signal, H=30 ===")
H=30; px=np.cumsum(rng.standard_normal(5000)); fwd=px[H:]-px[:-H]; n=len(fwd)
hits_naive=hits_adj=0
for _ in range(500):
    e=rng.standard_normal(n); s=np.empty(n); s[0]=e[0]
    for i in range(1,n): s[i]=0.98*s[i-1]+e[i]
    c=np.corrcoef(s,fwd)[0,1]
    hits_naive += abs(c*np.sqrt(n))>1.96
    hits_adj   += abs(c*np.sqrt(n/H))>1.96
print(f"noise signals 'significant': naive n -> {hits_naive/500:.2f}; n/H -> {hits_adj/500:.2f} (nominal 0.05)")
