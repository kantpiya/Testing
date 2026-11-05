# Common Factual Brief — Research Panel, 2026-11-05

**Issued by:** Research director (Claude, cloud session) · **Decision clock:** 2026-11-05 02:15 ET; session credits expire 02:59 ET. First-pass reports are due within ~12 minutes of issue; judges follow; synthesis follows.

## 1. Workspace inventory (verified by direct inspection, 02:13 ET)

| Source class | Looked for | Found |
|---|---|---|
| Git repository `kantpiya/Testing` | commits, branches, files | **Empty.** Zero commits locally; `git ls-remote origin` returns no refs. |
| Datasets (bars, trades, quotes, depth) | `*.parquet`, `*.csv`, MNQ/NQ/ES/MES files | **None** on the container filesystem. |
| Strategy code (KX, PX, engulfing, weak reversal, sell-off recovery) | any source files | **None.** |
| Logs (eligible signals, rejected signals, executed trades, positions, fills) | journals, logs | **None.** Therefore it is **unknown** whether the user's logs record rejected signals; every specialist must state what the logs *must* contain for their test. |
| Study reports (Study 66, Study 71 / 71-A) | documents | **None.** |
| Account-rule sources (prop-firm rules) | documents | **None.** |
| User's own computer | Remote Control folders | **None linked.** |
| Network | web | `WebSearch` works. Direct page fetch is blocked for most domains by the environment's network policy. |

**Consequence:** Every statement about Study 66, Study 71/71-A, strategy definitions, sizing ideas, SMT signals, pyramiding, event-VWAP work, and account mechanics is **USER-SUPPLIED CONTEXT (unverified)**. Label it as such. Do not invent file names, versions, or field names. Where a result would normally be cited from a file, write a **test specification** (inputs, unit of analysis, denominator, metric, failure criterion) or a **clearly labeled SYNTHETIC example** instead.

## 2. User-supplied context (verbatim summary; unverified)

- Primary instrument MNQ; some strategies read NQ or ES and execute in MNQ; also trades MES.
- Focus: intraday strategies, session effects, price action, systematically defined entries. Several strategies can trigger on the same move. A **strategy slot** = named strategy/variant eligible to trade under a specified set of conditions.
- Study 66: random-entry comparisons across shifted calendars and parameter grids; must distinguish a preselected rule's performance from the best result across a search.
- Study 71 / 71-A: "chop" = poor follow-through after an entry; changing the break definition materially changed the event count.
- Session-aware ATR and sizing: compare volatility to the relevant session/minute-of-day; hypothesis of giving calm conditions two micros.
- ES–NQ divergence / SMT: signals may use direction and magnitude; test whether ES adds information after NQ's own recent movement.
- Pyramiding: trade-off between retaining large winners and giving back open profit.
- Event-anchored VWAP around CPI, NFP, FOMC; anchor, available information and earliest executable time must be explicit.
- Strategy families KX and PX; setups engulfing, weak reversal, sell-off recovery. Definitions are NOT available; similar names do not imply similar exposures.
- Prop accounts with different evaluation/funded/drawdown/payout mechanics. Account constraints and strategy quality are separate questions.

## 3. Public instrument facts (from general knowledge; label "public, verify against CME specs")

- NQ: $20/index point, tick 0.25 pt ($5). MNQ: $2/point, tick 0.25 pt ($0.50). ES: $50/point, tick 0.25 ($12.50). MES: $5/point, tick 0.25 ($1.25).
- US cash equity RTH 09:30–16:00 ET. CME Globex equity index futures trade ~18:00 ET (prior day) to 17:00 ET with a daily maintenance halt 17:00–18:00 ET.
- Scheduled US releases: CPI and NFP at 08:30 ET; FOMC statement 14:00 ET with press conference ~14:30 ET. (Verify dates for any specific event.)

## 4. Rules for this panel

1. Work independently. **Do not read any other specialist's report** (do not open other files under `reports/`). Judges have not yet been convened.
2. Separate every claim into one of: **OBSERVED** (you inspected it), **EXTERNALLY SUPPORTED** (public source; give date + link; say "search result only" if you could not open the page), **HYPOTHESIS**, or **SYNTHETIC EXAMPLE**.
3. For every proposed trading filter, specify how to compute: eligible signals; trades retained; losses avoided; winners discarded; net change after costs; independent trading sessions; contribution to the portfolio. A better win rate alone is insufficient.
4. The user is a physician-researcher fluent in causal inference, interactions, sensitivity analysis and out-of-sample validation. Do not explain those. **Do** explain market-specific assumptions explicitly. Favor a strong simple baseline and say when complexity earns its place.
5. Small Python/R snippets and synthetic simulations are welcome; run them in your scratch directory and paste the output; label as SYNTHETIC.
6. Length: ≤ 1,200 words plus at most two tables/code blocks. Write your report to the file path you are given, then reply with a 5-line summary.

## 5. Required report sections (use these headings)

1. Strongest finding or proposal, and the decision it would change
2. Evidence (with labels) and the strongest competing explanation
3. Worked example / reproducible check / formula / wireframe / data spec
4. When following this proposal would make the decision worse
5. Cheapest decisive test, and the result that would retire the idea
6. Missing inputs that materially limit the conclusion
7. Filter accounting (the seven quantities in rule 3), as a table or a spec
