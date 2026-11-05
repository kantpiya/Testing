# Research Index — Independent Panel, 2026-11-05

Convened as research director for a systematic MNQ/MES intraday futures operation. **Workspace was empty** (no data, code, logs, study reports, or account rules — see brief §1), so all internal claims are labeled USER-SUPPLIED CONTEXT, all numbers are SYNTHETIC, and every proposal is delivered as a test specification.

**Agent runs that actually occurred:** 15 specialist agents (A1–A6, B1–B6, C1–C3) launched concurrently in one wave; each read only the common brief and wrote its own report before any other was shared. 3 judges (J1–J3) launched concurrently after all 15 reports were saved; each judged all 15 anonymized reports without seeing the other judges. Total independent runs: **18** (+ the director session).

## Start here
1. [Decision brief](synthesis/01_decision_brief.md) — what to use now, what to validate, what to drop, three next actions.
2. [Market-to-strategy table](synthesis/02_market_to_strategy_table.md)
3. [Conditional session playbook](synthesis/03_conditional_session_playbook.md)
4. [Clickable prototype](prototype/decision_support_prototype.html) — open in a browser; sample data only; five scenarios (clean, overlapping, insufficient evidence, account locked, input unavailable); "why did the decision change" diff.
5. [Ranked experiment backlog](synthesis/05_ranked_experiment_backlog.md)

## Inputs
- [Common brief](00_common_brief.md) — workspace inventory, user-supplied context, rules, required sections.

## First-pass reports (independent, private until all submitted)
| Panel A — market | Panel B — strategy/stats/risk | Panel C — application |
|---|---|---|
| [A1 Macro releases](reports/A1_macro_releases.md) | [B1 Portfolio manager](reports/B1_portfolio_manager.md) | [C1 UX layouts](reports/C1_ux_layouts.md) |
| [A2 Cross-asset](reports/A2_cross_asset.md) | [B2 Heterogeneous effects](reports/B2_heterogeneous_effects.md) | [C2 Data schema / replay](reports/C2_data_schema.md) |
| [A3 Microstructure](reports/A3_microstructure.md) | [B3 Backtest audit](reports/B3_backtest_audit.md) | [C3 Human factors](reports/C3_human_factors.md) |
| [A4 Price action](reports/A4_price_action.md) | [B4 Portfolio tail risk](reports/B4_portfolio_tail_risk.md) | |
| [A5 Vol & sizing](reports/A5_vol_sizing.md) | [B5 Prop-account paths](reports/B5_prop_account_paths.md) | |
| [A6 ES–NQ SMT](reports/A6_es_nq_smt.md) | [B6 Ops & behavioral](reports/B6_ops_behavioral.md) | |

## Independent verdicts
- [J1 Director of quantitative research](verdicts/J1_quant_research_director.md)
- [J2 Portfolio manager (capital)](verdicts/J2_capital_pm.md)
- [J3 Head trader / product owner](verdicts/J3_head_trader.md)

## Synthetic code (preserved from specialists' scratch runs)
`synthetic_code/<specialist>/` — A3 cost example, A4 break definitions, A5 sizing simulation, A6 SMT nested test, B1 policy simulation, B2 interaction simulation, B3 selection/reality-check simulation, B4 portfolio example, B5 prop-account path simulator, C2 replay demo. All run on synthetic data; none touch a feed or broker.

## Unfinished items (precise)
See the end of the decision brief.
