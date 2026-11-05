# SYNTHETIC: 8-pt gross edge per MNQ trade under three cost regimes. All inputs are HYPOTHESIS.
TICK=0.25; MNQ_PT=2.0
# Base trade geometry: p_win=0.5, target +30, stop -14 => gross 8 pts
p=0.5; tgt=30.0; stp=14.0
gross = p*tgt - (1-p)*stp
# regimes: (entry_slip_ticks, stop_slip_ticks, target_through_ticks, half_spread_ticks, comm_fee_usd_rt)
regimes = {
 "RTH ordinary":   {"cons":(2,4,1,0.5,1.5), "base":(1,2,1,0.5,1.0), "opt":(0.5,1,0,0.5,0.8)},
 "Open 09:30-35":  {"cons":(6,12,1,1.0,1.5), "base":(3,6,1,0.5,1.0), "opt":(1,2,0,0.5,0.8)},
 "Release 08:30/14:00":{"cons":(20,40,2,3.0,1.5), "base":(8,15,1,1.5,1.0), "opt":(3,5,1,1.0,0.8)},
}
print(f"gross edge {gross:.1f} pts = ${gross*MNQ_PT:.2f}/contract")
print(f"{'regime':22s}{'case':6s}{'cost pts':>9s}{'net pts':>9s}{'net $':>8s}{'edge kept':>10s}")
for name,cases in regimes.items():
    for c,(es,ss,tt,hs,fee) in cases.items():
        # entry: cross half-spread + slippage; stop: pay slippage on losers only; target: needs trade-through -> effectively give up tt ticks
        cost = (hs+es)*TICK + (1-p)*ss*TICK + p*tt*TICK + fee/MNQ_PT
        net = gross-cost
        print(f"{name:22s}{c:6s}{cost:9.2f}{net:9.2f}{net*MNQ_PT:8.2f}{net/gross:10.0%}")
