# Reference run (holdout) — sealed/holdout  [SYNTHETIC]

Trades 88, sessions 60; KX 60, PX 28; strategy versions: {'KX_ORB_v2': 60, 'PX_REV_v1': 28}
P0 net $4,949 (journal $5,462); KX mean R +0.723, PX mean R +0.033

## Stage A comparison table (reference fill model; paired on identical entries; costs on every fill)

| policy              | family   |   trades |   sessions |   net_usd |   mean_R |   worst_session |   max_dd |   top10_usd_base |   n_top10 |   d_usd |   d_usd_lo |   d_usd_hi |   dR_entry |   dR_lo |   dR_hi |   changed |   losses_avoided_usd |   n_losses_avoided |   winners_cut_usd |   n_winners_cut |   losers_worsened_usd |   winners_improved_usd |   top10_usd_alt |   top10_cut |   pct_benefit_top3_sessions |
|:--------------------|:---------|---------:|-----------:|----------:|---------:|----------------:|---------:|-----------------:|----------:|--------:|-----------:|-----------:|-----------:|--------:|--------:|----------:|---------------------:|-------------------:|------------------:|----------------:|----------------------:|-----------------------:|----------------:|------------:|----------------------------:|
| P0                  | KX       |       60 |         60 |      4758 |    0.723 |            -379 |    -1277 |             2579 |         6 |     nan |        nan |        nan |    nan     | nan     | nan     |       nan |                  nan |                nan |               nan |             nan |                   nan |                    nan |             nan |         nan |                         nan |
| P0                  | PX       |       28 |         28 |       191 |    0.033 |            -162 |     -704 |              650 |         3 |     nan |        nan |        nan |    nan     | nan     | nan     |       nan |                  nan |                nan |               nan |             nan |                   nan |                    nan |             nan |         nan |                         nan |
| C1_stall_BE         | KX       |       60 |         60 |      5625 |    0.821 |            -218 |    -1166 |             2579 |         6 |     866 |      -1005 |       2400 |      0.098 |  -0.096 |   0.265 |        10 |                 1562 |                  8 |              -696 |               2 |                     0 |                      0 |            2579 |           0 |                          89 |
| C2_late_BE20        | KX       |       60 |         60 |      5033 |    0.748 |            -377 |    -1277 |             2579 |         6 |     274 |          0 |        824 |      0.025 |   0     |   0.075 |         1 |                  274 |                  1 |                 0 |               0 |                     0 |                      0 |            2579 |           0 |                         100 |
| C3_add_stop_entry   | KX       |       60 |         60 |      4912 |    0.741 |            -287 |    -1277 |             2579 |         6 |     154 |       -418 |        662 |      0.018 |  -0.042 |   0.074 |         5 |                  354 |                  4 |              -200 |               1 |                     0 |                      0 |            2579 |           0 |                         189 |
| C4_PX_far_target    | PX       |       28 |         28 |      1003 |    0.23  |            -162 |     -658 |              650 |         3 |     812 |       -545 |       1993 |      0.197 |  -0.109 |   0.467 |        16 |                    0 |                  0 |              -716 |               4 |                     0 |                   1528 |             544 |           2 |                          73 |
| D1_KX_notarget_BE2R | KX       |       60 |         60 |     23895 |    3.184 |            -379 |    -1084 |             2579 |         6 |   19137 |       4741 |      36206 |      2.462 |   0.593 |   4.744 |        26 |                  238 |                  1 |             -5532 |              11 |                     0 |                  24430 |            4929 |           2 |                          61 |
| D2_PX_notarget      | PX       |       28 |         28 |      2756 |    0.625 |            -162 |     -613 |              650 |         3 |    2566 |         -8 |       5255 |      0.593 |  -0.009 |   1.238 |        16 |                    0 |                  0 |             -1142 |               6 |                     0 |                   3708 |             901 |           2 |                          68 |
| D3_stall_EXIT       | KX       |       60 |         60 |      4938 |    0.742 |            -218 |    -1307 |             2579 |         6 |     179 |      -2306 |       2387 |      0.02  |  -0.253 |   0.262 |        13 |                 1987 |                  8 |             -1808 |               5 |                     0 |                      0 |            2579 |           0 |                         583 |
| D4_fail15           | KX       |       60 |         60 |      4792 |    0.707 |            -379 |     -921 |             2579 |         6 |      34 |      -1424 |       1162 |     -0.016 |  -0.215 |   0.133 |        12 |                  858 |                 10 |              -824 |               2 |                     0 |                      0 |            2579 |           0 |                        1092 |
| D4b_time15          | KX       |       60 |         60 |      2609 |    0.4   |            -283 |    -1160 |             2579 |         6 |   -2149 |      -4893 |        713 |     -0.323 |  -0.657 |   0.007 |        31 |                 2086 |                 13 |             -4235 |              18 |                     0 |                      0 |            1764 |           4 |                         -59 |

### Five sessions contributing most to each paired difference (session: paired Δ$)

- C1_stall_BE: 2026-06-26:+660;2026-05-26:+274;2026-05-08:+254;2026-07-13:+240;2026-05-06:+238
- C2_late_BE20: 2026-05-26:+274;2026-05-01:+0;2026-05-05:+0;2026-05-04:+0;2026-05-07:+0
- C3_add_stop_entry: 2026-06-26:+200;2026-07-13:+120;2026-05-26:+92;2026-05-06:+80;2026-05-08:+64
- C4_PX_far_target: 2026-06-04:+362;2026-07-28:+282;2026-07-17:+272;2026-06-12:+159;2026-05-20:+148
- D1_KX_notarget_BE2R: 2026-07-09:+4907;2026-05-22:+3894;2026-07-29:+2883;2026-05-18:+2582;2026-07-21:+1696
- D2_PX_notarget: 2026-07-28:+640;2026-05-11:+621;2026-05-14:+492;2026-06-30:+433;2026-06-11:+419
- D3_stall_EXIT: 2026-06-26:+660;2026-05-01:+516;2026-07-13:+394;2026-06-01:+380;2026-05-26:+350
- D4_fail15: 2026-05-28:+484;2026-06-24:+340;2026-06-08:+170;2026-05-08:+106;2026-05-13:+95
- D4b_time15: 2026-05-06:+596;2026-05-26:+507;2026-05-28:+484;2026-05-01:+446;2026-07-06:+418

## The user's decision: KX reached >= +0.8R then closed <= +0.3R (stall set, trades still open under P0)

- stall set n = 13 trades / 13 sessions; P0 mean R -0.110
- C1 tighten to breakeven: mean R +0.344; paired ΔR +0.454 [-0.44, +1.12]
- D3 exit now: mean R -0.020; paired ΔR +0.090 [-1.11, +1.24]
- P(final R < -0.5R): P0 0.62, C1 0.31
  - KX_ORB_v2: n=13 ΔR +0.454 [-0.44, +1.12]

## C2 conditioned set (open at minute 20 with close >= +0.3R)

- n = 13 / 13 sessions; paired ΔR +0.115 [+0.00, +0.35]
- P(R < -0.5R): P0 0.08 -> C2 0.08; worst-decile mean R: P0 +0.21 -> C2 +0.96

## C3 add trades

- add trades n = 23 / 23 sessions; paired Δ$ +154 [-418, +622]
- worst session KX: P0 -379 -> C3 -287; max DD KX: P0 -1,277 -> C3 -1,277
- among add trades, C3 changed 5; of those originally TARGET: 1

## Fill-assumption grid (paired Δ$ vs P0 under the same fill model; KX candidates on KX, C4 on PX)

| variant              |   C1_stall_BE |   C1_stall_BE_amb |   C2_late_BE20 |   C2_late_BE20_amb |   C3_add_stop_entry |   C3_add_stop_entry_amb |   C4_PX_far_target |   C4_PX_far_target_amb |   D1_KX_notarget_BE2R |   D1_KX_notarget_BE2R_amb |
|:---------------------|--------------:|------------------:|---------------:|-------------------:|--------------------:|------------------------:|-------------------:|-----------------------:|----------------------:|--------------------------:|
| reference            |           866 |                 0 |            274 |                  0 |                 154 |                       0 |                812 |                      0 |                 19137 |                         0 |
| penetrate_stop       |           866 |                 0 |            274 |                  0 |                 154 |                       0 |                812 |                      0 |                 19137 |                         0 |
| slip0                |           868 |                 0 |            274 |                  0 |                 155 |                       0 |                814 |                      0 |                 19166 |                         0 |
| slip2                |           865 |                 0 |            274 |                  0 |                 154 |                       0 |                810 |                      0 |                 19108 |                         0 |
| target_first         |           866 |                 0 |            274 |                  0 |                 154 |                       0 |                812 |                      0 |                 19137 |                         0 |
| no_bracket_entry_bar |           866 |                 0 |            274 |                  0 |                 154 |                       0 |                812 |                      0 |                 19137 |                         0 |

(`_amb` = bars in which a live stop and a live target were both touched; 0 means ordering is moot)

## Stage B (chronological, position limit 4, rejected signals eligible, reference fill model)

| policy              |   executed |   rejected |   net_usd |   max_dd |   worst_session |   blocked_vs_export |   freed_vs_export |   d_net_vs_P0 |
|:--------------------|-----------:|-----------:|----------:|---------:|----------------:|--------------------:|------------------:|--------------:|
| P0                  |         88 |          1 |      4945 |    -1233 |            -539 |                   0 |                 0 |             0 |
| C1_stall_BE         |         89 |          0 |      6141 |    -1121 |            -350 |                   0 |                 1 |          1196 |
| C2_late_BE20        |         88 |          1 |      5380 |    -1233 |            -379 |                   0 |                 0 |           435 |
| C3_add_stop_entry   |         88 |          1 |      5099 |    -1233 |            -419 |                   0 |                 0 |           154 |
| C4_PX_far_target    |         88 |          1 |      5758 |    -1298 |            -539 |                   0 |                 0 |           813 |
| D1_KX_notarget_BE2R |         88 |          1 |     26414 |    -1408 |            -539 |                   0 |                 0 |         21469 |
