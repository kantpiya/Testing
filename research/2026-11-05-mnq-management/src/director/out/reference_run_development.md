# Reference run (development) — data/synthetic  [SYNTHETIC]

Trades 332, sessions 242; KX 240, PX 92; strategy versions: {'KX_ORB_v1': 162, 'PX_REV_v1': 92, 'KX_ORB_v2': 78}
P0 net $15,314 (journal $15,370); KX mean R +0.357, PX mean R +0.191

## Stage A comparison table (reference fill model; paired on identical entries; costs on every fill)

| policy              | family   |   trades |   sessions |   net_usd |   mean_R |   worst_session |   max_dd |   top10_usd_base |   n_top10 |   d_usd |   d_usd_lo |   d_usd_hi |   dR_entry |   dR_lo |   dR_hi |   changed |   losses_avoided_usd |   n_losses_avoided |   winners_cut_usd |   n_winners_cut |   losers_worsened_usd |   winners_improved_usd |   top10_usd_alt |   top10_cut |   pct_benefit_top3_sessions |
|:--------------------|:---------|---------:|-----------:|----------:|---------:|----------------:|---------:|-----------------:|----------:|--------:|-----------:|-----------:|-----------:|--------:|--------:|----------:|---------------------:|-------------------:|------------------:|----------------:|----------------------:|-----------------------:|----------------:|------------:|----------------------------:|
| P0                  | KX       |      240 |        240 |     12638 |    0.357 |            -392 |    -1994 |            11116 |        24 |     nan |        nan |        nan |    nan     | nan     | nan     |       nan |                  nan |                nan |               nan |             nan |                   nan |                    nan |             nan |         nan |                         nan |
| P0                  | PX       |       92 |         92 |      2676 |    0.191 |            -196 |     -528 |             1455 |         9 |     nan |        nan |        nan |    nan     | nan     | nan     |       nan |                  nan |                nan |               nan |             nan |                   nan |                    nan |             nan |         nan |                         nan |
| C1_stall_BE         | KX       |      240 |        240 |      9238 |    0.27  |            -224 |    -3180 |            11116 |        24 |   -3400 |      -7892 |        783 |     -0.086 |  -0.2   |   0.025 |        53 |                 5543 |                 31 |             -8943 |              22 |                     0 |                      0 |            9438 |           3 |                         -22 |
| C2_late_BE20        | KX       |      240 |        240 |     12760 |    0.367 |            -341 |    -1823 |            11116 |        24 |     121 |      -2633 |       2504 |      0.01  |  -0.064 |   0.073 |        21 |                 2676 |                 15 |             -2555 |               6 |                     0 |                      0 |            9958 |           2 |                         617 |
| C3_add_stop_entry   | KX       |      240 |        240 |     12318 |    0.351 |            -272 |    -1936 |            11116 |        24 |    -320 |      -1407 |        618 |     -0.006 |  -0.035 |   0.019 |        19 |                  888 |                 11 |             -1208 |               8 |                     0 |                      0 |           10648 |           3 |                        -102 |
| C4_PX_far_target    | PX       |       92 |         92 |      8138 |    0.587 |            -196 |     -457 |             1455 |         9 |    5462 |       3547 |       7157 |      0.396 |   0.26  |   0.515 |        64 |                    0 |                  0 |             -1183 |               5 |                     0 |                   6645 |            2482 |           1 |                          11 |
| D1_KX_notarget_BE2R | KX       |      240 |        240 |     73750 |    2.116 |            -392 |    -1997 |            11116 |        24 |   61112 |      39766 |      82018 |      1.76  |   1.156 |   2.341 |        98 |                  258 |                  1 |            -12503 |              34 |                     0 |                  73357 |           24315 |           7 |                          16 |
| D2_PX_notarget      | PX       |       92 |         92 |     15241 |    1.072 |            -196 |     -518 |             1455 |         9 |   12566 |       7458 |      18376 |      0.881 |   0.51  |   1.298 |        64 |                    0 |                  0 |             -3502 |              19 |                     0 |                  16067 |            2698 |           3 |                          22 |
| D3_stall_EXIT       | KX       |      240 |        240 |      7969 |    0.224 |            -224 |    -3559 |            11116 |        24 |   -4669 |      -9568 |       -158 |     -0.133 |  -0.268 |  -0.007 |        60 |                 6414 |                 31 |            -11084 |              29 |                     0 |                      0 |            8632 |           5 |                         -19 |
| D4_fail15           | KX       |      240 |        240 |      9767 |    0.278 |            -392 |    -1996 |            11116 |        24 |   -2871 |      -6148 |        143 |     -0.079 |  -0.169 |   0.004 |        43 |                 2642 |                 29 |             -5514 |              14 |                     0 |                      0 |           10481 |           1 |                         -20 |
| D4b_time15          | KX       |      240 |        240 |       623 |    0.029 |            -326 |    -3262 |            11116 |        24 |  -12015 |     -17206 |      -6378 |     -0.328 |  -0.47  |  -0.174 |       127 |                 8127 |                 50 |            -20142 |              77 |                     0 |                      0 |            5862 |          19 |                         -11 |

### Five sessions contributing most to each paired difference (session: paired Δ$)

- C1_stall_BE: 2025-06-11:+603;2026-02-26:+582;2026-03-19:+576;2026-02-12:+520;2025-11-06:+510
- C2_late_BE20: 2026-02-26:+582;2026-03-19:+576;2025-10-16:+426;2025-05-09:+356;2025-08-20:+347
- C3_add_stop_entry: 2025-06-11:+199;2026-03-19:+192;2025-11-06:+169;2026-02-26:+146;2025-06-18:+146
- C4_PX_far_target: 2025-05-15:+349;2025-09-17:+270;2025-08-29:+256;2026-04-06:+232;2026-04-08:+207
- D1_KX_notarget_BE2R: 2025-09-18:+3984;2025-09-15:+2936;2025-12-30:+2798;2026-01-28:+2616;2025-08-26:+2436
- D2_PX_notarget: 2026-01-14:+977;2025-07-11:+939;2025-05-27:+872;2025-09-22:+762;2025-11-05:+680
- D3_stall_EXIT: 2025-06-11:+603;2026-02-26:+572;2026-03-19:+561;2026-03-05:+516;2025-11-06:+510
- D4_fail15: 2026-03-19:+634;2025-11-06:+522;2025-11-26:+465;2025-12-15:+462;2025-06-18:+448
- D4b_time15: 2026-03-19:+634;2025-06-11:+562;2025-11-06:+522;2025-11-26:+465;2025-12-15:+462

## The user's decision: KX reached >= +0.8R then closed <= +0.3R (stall set, trades still open under P0)

- stall set n = 60 trades / 60 sessions; P0 mean R +0.437
- C1 tighten to breakeven: mean R +0.091; paired ΔR -0.346 [-0.80, +0.11]
- D3 exit now: mean R -0.093; paired ΔR -0.530 [-1.05, -0.02]
- P(final R < -0.5R): P0 0.52, C1 0.18
  - KX_ORB_v1: n=41 ΔR -0.572 [-1.08, -0.04]
  - KX_ORB_v2: n=19 ΔR +0.142 [-0.76, +0.91]

## C2 conditioned set (open at minute 20 with close >= +0.3R)

- n = 63 / 63 sessions; paired ΔR +0.038 [-0.24, +0.29]
- P(R < -0.5R): P0 0.24 -> C2 0.06; worst-decile mean R: P0 -2.01 -> C2 -0.56

## C3 add trades

- add trades n = 74 / 74 sessions; paired Δ$ -320 [-1,386, +634]
- worst session KX: P0 -392 -> C3 -272; max DD KX: P0 -1,994 -> C3 -1,936
- among add trades, C3 changed 19; of those originally TARGET: 8

## Fill-assumption grid (paired Δ$ vs P0 under the same fill model; KX candidates on KX, C4 on PX)

| variant              |   C1_stall_BE |   C1_stall_BE_amb |   C2_late_BE20 |   C2_late_BE20_amb |   C3_add_stop_entry |   C3_add_stop_entry_amb |   C4_PX_far_target |   C4_PX_far_target_amb |   D1_KX_notarget_BE2R |   D1_KX_notarget_BE2R_amb |
|:---------------------|--------------:|------------------:|---------------:|-------------------:|--------------------:|------------------------:|-------------------:|-----------------------:|----------------------:|--------------------------:|
| reference            |         -3400 |                 0 |            121 |                  0 |                -320 |                       0 |               5462 |                      0 |                 61112 |                         0 |
| penetrate_stop       |         -3745 |                 0 |            121 |                  0 |                -320 |                       0 |               5462 |                      0 |                 61334 |                         0 |
| slip0                |         -3367 |                 0 |            131 |                  0 |                -316 |                       0 |               5466 |                      0 |                 61265 |                         0 |
| slip2                |         -3434 |                 0 |            112 |                  0 |                -324 |                       0 |               5458 |                      0 |                 60959 |                         0 |
| target_first         |         -3400 |                 0 |            121 |                  0 |                -320 |                       0 |               5462 |                      0 |                 61112 |                         0 |
| no_bracket_entry_bar |         -3400 |                 0 |            121 |                  0 |                -320 |                       0 |               5462 |                      0 |                 61112 |                         0 |

(`_amb` = bars in which a live stop and a live target were both touched; 0 means ordering is moot)

## Stage B (chronological, position limit 4, rejected signals eligible, reference fill model)

| policy              |   executed |   rejected |   net_usd |   max_dd |   worst_session |   blocked_vs_export |   freed_vs_export |   d_net_vs_P0 |
|:--------------------|-----------:|-----------:|----------:|---------:|----------------:|--------------------:|------------------:|--------------:|
| P0                  |        327 |         19 |     15664 |    -1807 |            -359 |                   5 |                 0 |             0 |
| C1_stall_BE         |        342 |          4 |     11821 |    -3025 |            -359 |                   2 |                12 |         -3843 |
| C2_late_BE20        |        330 |         16 |     15720 |    -1676 |            -359 |                   5 |                 3 |            56 |
| C3_add_stop_entry   |        331 |         15 |     15214 |    -1786 |            -389 |                   4 |                 3 |          -450 |
| C4_PX_far_target    |        327 |         19 |     20915 |    -1678 |            -490 |                   5 |                 0 |          5251 |
| D1_KX_notarget_BE2R |        327 |         19 |     89732 |    -1869 |            -490 |                   5 |                 0 |         74068 |
