# Russia balance changelog

## 2026-11-22 R5.0 baseline (no data changes)
Command: `python3 Tools/Russia/series.py --seeds 1-5 --maps rmg --pairs FactionRussia:FactionGLA,FactionChina:FactionGLA,FactionRussia:FactionChina --swap --parallel 6 --maxframes 54000 --out $TMPDIR/r50/base.csv --keeplogs $TMPDIR/r50/logs`
30 matches, 0 crashes, all decided. Economy/trades: HISTORY SAMPLE/WORTH lines averaged at fixed frames.

- Russia vs GLA 1-9; China vs GLA (control, same seeds) 0-10. GLA dominance comes from the China base scripts, not Russia data.
- Russia vs China 10-0 (target 3-7): too strong.
- Earned at 3/6/8/10 min, share of China in the same matchup: vs GLA 82/91/88/89%, vs China 92/98/100/108%. Income is within 90-110%: economy is not the cause.
- Army value destroyed/lost at 8 min: Russia vs China 91k/75k (ratio 1.22), China vs Russia 69k/94k (0.74); Russia vs GLA 58k/97k (0.59), China vs GLA 54k/110k (0.49).
- Russia builds ~10.7 Pantsir sites and 8 Buk per match vs China (6.4/4.8 vs GLA): static AA wall. Suspect: it kills China's air (MiG/Helix) for free, and is wasted money vs GLA (no real air).
- Missing: per-unit kill stats; Tools/Balance unitmatrix/duel/siege do not read Russia INIs yet.

## 2026-11-22 R5.0 round 1
Command per variant: `python3 Tools/Russia/series.py --seeds 1-10 --maps rmg --pairs <pairs> --swap --parallel 6 --maxframes 54000 --out <csv>` (20 matches per pair, W-L-draw from Russia's side).

Controls: USA vs China 3-3-14 (equal); USA vs GLA 0-8-2; China vs GLA 0-10. The GLA bot beats every base faction, so 3-7 vs GLA is out of reach without making Russia overpowered vs the rest.

Anti-GLA bot work (kept, effect on GLA result none: still 0-10 on 10 matches):
- Russia scripts: Buk only when the enemy is not GLA (flag `RussiaVsGLA`, Tools/ScbTool/russia.py).
- Engine: a `<This Player's Enemy>` miss early in the match was cached forever (ScriptConditions.cpp playerFromParam); now looked up again.
- Engine AI: air-only defenses (only Russia's Buk-M3 in the game) no longer picked by the AI's defense ring (AIPlayer.cpp nextBaseDefense); scripts still build them.

Russia vs China, single-lever experiments (reverted, 20 matches each): baseline 18-0-2; no free Veterans 16-3-1; T72B3M 800 16-2-2; TOS2 not free 16-2-2.

Applied (combined): T-72B3M 700 -> 800 (source price), TOS-2 1500 -> 1800, Veterans science: RPG gunners no longer start veteran (motor riflemen only, like China's Red Guard training).
Result: vs China 15-3-2 (target band 6-14 of 20: one above), vs USA 10-3-7 (in band). Economy vs China 96-101% of China's at 3-10 min.
