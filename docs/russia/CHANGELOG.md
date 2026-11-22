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
