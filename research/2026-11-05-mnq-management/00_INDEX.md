# MNQ post-entry management panel — 2026-11-05 — index

**Question.** After one of the desk's MNQ entries fills, can a simple, executable management policy improve net results or materially reduce drawdown at an acceptable cost in profits? Should management depend on the setup, on what price does after entry, or on elapsed time?

**Status of the evidence.** The workspace contained **no signals, fills, strategy code or market data** (`02_inventory_and_export_fields.md`). Every number in this folder is from a **SYNTHETIC** test case built in the exact export schema, with a sealed chronological holdout and planted ground truth. The results test the *method*; the deliverables that transfer to the real desk are the replay engine, the field list, the pre-registered policies and the forward-simulation specification.

**Independent runs.** Six specialist agents (S1–S6), two reviewer agents (A, B), and the director's own replay (`src/director/reproduce.py`), all separate contexts; specialists did not read each other; reviewers did not read each other. First-pass reports were committed before any conclusion was shared (`git log`).

## Read in this order

| # | File | What it is |
|---|---|---|
| 1 | `synthesis/01_decision_brief.md` | **One-page decision brief**: which policy, if any, deserves forward simulation, for which strategy, and why; reviewer verdicts and preserved disagreements |
| 2 | `synthesis/02_comparison_table.md` | One comparison table (development + holdout): net $, R per entry, worst session, max drawdown, losses avoided, winners cut, largest-winner contribution |
| 3 | `synthesis/03_profit_vs_protection.md` | For every tighter exit: losses avoided, surrendered on recovered winners, incremental costs, net; five sessions driving each |
| 4 | `charts/replay_1..4_*.png` | Four charted trade replays with the first knowable instant marked (SYNTHETIC, labelled) |
| 5 | `synthesis/05_forward_simulation_spec.md` | Shadow-mode forward simulation: triggers, order actions, fields to log, promotion and retirement criteria |
| 6 | `synthesis/04_ground_truth_audit.md` | What was planted in the synthetic data vs what the panel found; where the generator misled and where the methods held |
| 7 | `02_inventory_and_export_fields.md` | Inventory of what exists and the **exact fields to export** for the real replay |
| 8 | `01_common_brief.md` | The identical factual brief every specialist received |
| 9 | `prereg/challengers.md` | Pre-registration of P0 + four challengers (mechanism, decision time, parameters, fills, objective), frozen before the holdout was opened |

## Specialist and reviewer reports (first pass, unedited after submission)

| Report | Role | Core finding (SYNTHETIC) |
|---|---|---|
| `reports/S1_trade_paths.md` | Trade-path statistician | "Given what was observable, what happened next" tables; holding beats exit-now in every KX state with n ≥ 20; late profit-conditional breakeven is the only cost-neutral tail reducer |
| `reports/S2_failed_followthrough.md` | Breakout / failed follow-through | No-progress exit at 15 min: −0.08R per entry; unconditional time exit far worse; 46 cells, none positive with CI excluding 0 |
| `reports/S3_reversals.md` | Reversal / profit-taking | No PX timing rule helps; breakout rule harms reversals; only the target level matters and that gain is drift |
| `reports/S4_pyramiding.md` | Pyramiding / winner retention | Add earns +0.29R of its own risk; every separate add management costs money; add-stop-at-entry buys drawdown only |
| `reports/S5_replay_engine.md` | Execution / replay engineer | Reconciliation 282/332 exact (316 under the generator's conventions), 10 MANUAL unexplained; exact-touch ambiguity swings 6.8% of net; engine + README |
| `reports/S6_skeptic.md` | Skeptical portfolio manager | Every tightening loses; the only "winner" (drop the KX target) is generator drift that cannot be verified on real data in under ~2.5 years |
| `reports/reviewer_A_methods.md` | Reviewer A, quantitative methods | C1 revise, C2 revise, C3 retire, C4 retire, P0 advance as control; the minute-10 drift gauge is the first number to compute on real data |
| `reports/reviewer_B_execution.md` | Reviewer B, MNQ execution trader | C1 retire, C2 advance, C3 revise, C4 advance conditional, P0 control; materiality floor $1,000/yr or 2R; eleven fixes to the forward-sim spec (applied) |

## Runnable artefacts

| Path | Purpose | Command |
|---|---|---|
| `src/S5/replay.py`, `src/S5/reconcile.py`, `src/S5/run.py`, `src/S5/README.md` | Reference replay engine, journal reconciliation, verification checklist | `python3 src/S5/reconcile.py data/real src/S5/out_real` |
| `src/director/holdout_run.py` | Pre-registered policies P0, C1–C4, diagnostics D1–D4; comparison metrics; fill grid; Stage B | `python3 src/director/holdout_run.py --data data/real --tag real --stage_b` |
| `src/director/reproduce.py` | Independent engine (cross-check of P0, C1, D3, D1) | `python3 src/director/reproduce.py --data data/real` |
| `src/S1..S6/run.py` | Each specialist's analysis | `python3 src/S<k>/run.py` |
| `src/director/make_charts.py`, `src/director/plot_replay.py` | The four replay charts | `python3 src/director/make_charts.py` |
| `sealed/make_synthetic.py` | The synthetic generator (seed 20261105) | `python3 sealed/make_synthetic.py` |

To run on the real export: place the files listed in `02_inventory_and_export_fields.md` under `data/real/` with the same names as `data/synthetic/`; run reconciliation first, then `holdout_run.py`.

## Data

- `data/synthetic/` — development set, 2025-05-01 → 2026-04-30 (242 sessions, 332 trades).
- `sealed/holdout/` — holdout, 2026-05-01 → 2026-07-30 (60 sessions, 88 trades); opened only after `prereg/challengers.md` was committed.
- `sealed/ground_truth.md`, `sealed/ground_truth_trades.csv` — planted structure; opened for `synthesis/04_ground_truth_audit.md` after all reports were saved.

Live settings and source data: none existed in the repository; nothing outside this folder was changed.
