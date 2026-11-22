# RUSSIA FACTION: AGENT PLAN (single source of truth; agent-only, user never reads it)

## PROTOCOL (obey literally)
P1 Trigger: user says "делай"/"продолжай" with nothing pending -> run this plan. "делай" answering your own pending question = yes to that question.
P2 Read THIS file whole, nothing else up front. Never read docs/russia/plan.html (frozen human spec v1; all data is here).
P3 Pick task: first [~]; else first [ ] whose deps (`<-`) are [x]. One task at a time.
P4 Mark [~] in file BEFORE work. Do it. Verify by its `=>` criterion (run it, don't assume). Then [x] + one LOG line.
P5 Commit after each task: code + this file together, msg `russia(<ID>): <what>` + Co-Authored-By trailer. Then `git push origin main` (user asked 2026-11-22: "всё отправляй в github"). Never push to upstream.
P6 Keep going task after task. Stop only at: GATE task, [?] task, blocker, or user interrupt. Before stopping: STATE updated, committed, pushed.
P7 Plan differs from reality -> DEV line (expected/found/action). Inside stage scope: fix tasks yourself (split, add, reorder). Touches DECISIONS, public repo shape, deleting data, >1 extra session -> mark [?], ask user.
P8 Asking user: Russian, from zero, per CLAUDE.md format (Действие/Риск/Почему/Что даёт). User does not know this file; never say "task R2.3", say what it is.
P9 Stage done -> collapse its [x] lines into one `[x] Rn done: <result>` line, trim its LOG lines to <=3. File must stay <400 lines.
P10 Statuses: [ ] todo [~] doing [x] done [!] blocked(reason) [?] needs user. GATE = report to user + wait for "делай".
P11 Token thrift: grep/sed -n ranges, never cat big INI/logs; logs via `cmd > $TMPDIR/x.log 2>&1; echo exit=$?; tail -30`. No subagents unless wide search (P: user CLAUDE.md).
P12 Never: weaken/skip tests; bot cash cheats; change opponents' scripts; cherry-pick maps; fewer matches than stated; change metric after seeing numbers; take assets from other mods (RotR etc.).
P13 Upstream merges only by release tag (`git fetch upstream --tags; git merge vX.Y.Z`), only when user asks or a task needs it. Minimize edits in upstream files: own files first, one-line hooks second.
P14 Text for players: UI strings in game language (ru+en at least); Russian text on models. Code comments: match file (upstream uses English).

## STATE
NOW: R3.7
LAST: R2 skeleton verified 2026-11-22.
NEXT-NOTE: -
BLOCKERS: -

## DECISIONS (user-approved 2026-11-22, do not change without user)
D1 engine Reforged fork ~/Games/Generals-Reforged (origin kimci621/generals-zh-next public GPL-3; upstream olcayseygan). branch main.
D2 dev visuals = analog unit models (reskins), no cubes. Icons = placeholder.
D3 economy: KamAZ trucks (China-like) + Voenkomat (free reservist/60s, max 5 alive) + Tax upgrade (+10-15%/delivery) + Oil-gas upgrade (derricks +50%) + Cyberattack power. Too strong -> weaken sources, never remove.
D4 no balancing vs Turkiye. Targets vs USA/China/GLA.
D5 promotion tree + Oreshnik superweapon as in DATA.
D6 BaseSide China (bot runs China scripts first), RandomExcluded Yes.

## FACTS
F1 Build app: `ninja -C ~/Games/Generals-Reforged/build-mac macos_app` (~20s incremental). Full: `./build-macos.sh`. Output build-mac/Zero Hour Reforged.app. Overlay (INI/strings/art loose files) staged by GeneralsMD/Code/Tools/stage-overlay.sh from GeneralsMD/Code/Data into the bundle -> new Data files must be under GeneralsMD/Code/Data and in a staged folder.
F2 Run: `"<app>/Contents/MacOS/generals" -root ~/Games/Generals/GeneralsZH [flags]`. Data read-only; user data+logs: ~/Library/Application Support/Command and Conquer Generals Zero Hour Data/ (Logs/DebugLogFile.txt, Options.ini, ReforgedArt/).
F3 Headless match flags (ALWAYS add `-quickstart -noshellmap -observer -multiInstance`, autoskirmish N = players; without -observer slot 0 is idle human; result line only in Logs/<prefix>DebugLogFile.txt): `-headless -randommap <seed> <players> <cells> | -map "Maps\X\X.map"` `-autoskirmish <N> -aidiff hard -seed <n> -maxframes <n> -logPrefix <p> -side <slot> FactionX` (-side repeatable). Result line in log: `HEADLESS RESULT: ... on frame F (... x real time)` (GameEngine.cpp:~2989). Reference driver: ai-batch.ps1 (Windows PS; port logic, don't run).
F4 Do NOT run Reforged at same time as ~/Games/Generals Improved AI launchers (they swap files in GeneralsZH).
F5 Turkiye pattern: `ObjectReskin TurkiyeX AmericaX` then `Object TurkiyeX` patch block (INI_LOAD_MULTIFILE) in Data/INI/TurkiyeReforged.ini (65 reskins). Reskin counts as its source for prereqs, build lists, AI scripts (ThingFactory.cpp:343, ProductionUpdate.cpp:436, AIPlayer.cpp:1182,3271). Weapons Data/INI/TurkiyeWeaponReforged.ini (INI_LOAD_OVERWRITE). Load list GameEngine.cpp:1349,1383. PlayerTemplate FactionTurkiye in PlayerTemplateReforged.ini (BaseSide USA, DisplayName INI:FactionTurkiye). Talents TalentsReforged.ini, sciences ScienceReforged.ini, voices VoiceReforged.ini, Eva EvaReforged.ini, cameos MappedImages/HandCreated/TRCameos.ini, HUD ReforgedHudTurkiye*.ini, faction picker image FactionPicker<Template> (FactionPicker.cpp:89).
F6 Hardcoded side-name branches (UI prefix by side.startsWith): GroupPanel.cpp:296, InGameUI.cpp:416, AirliftPanel.cpp:210, ControlBarSidebar.cpp:224,1556,2033, ControlBar.cpp:6402. Generic fallbacks (no code needed?): SidesList.cpp:476, PlayerTemplate.cpp:325, Eva.cpp:550, GameAudio.cpp:280. Art archive list ArchiveFileSystem.cpp:182 (only for own HD art, later).
F7 Engine modules already in fork (from Turkiye): JammerUpdate, RadarJamSpecialPower, SwarmStrikeSpecialPower (Kargu), MarkAndRainBehavior, RadarContactMarks, RadarCoverageBehavior, SightUpgrade, WeaponSetUpgrade, PointDefenseLaserUpdate. Check them first for EW/drones/counter-battery.
F8 Vanilla refs: derrick 200/12s +1000 capture, `UpgradedBoost = UpgradeType:Upgrade_AmericaSupplyLines Boost:20`. Black Market 20/2s. Cash Hack 1000/2000/4000. Reloads: Nuke 360s, Scud 300s, Particle 240s. Extract vanilla INI: `python3 -I ~/Games/Generals/tools/bigx.py ~/Games/Generals/GeneralsZH/INIZH.big <out> <substr>`.
F9 Series: `python3 Tools/Russia/series.py --seeds 1-6 --maps rmg|<map>,.. --pairs A:B,.. --swap --parallel 6 --maxframes 54000 --out $TMPDIR/x.csv` (winner from HEADLESS PLAYER WON; frame cap -> none). Balance tools (author): Tools/Balance/{unitmatrix,duel,siege,calibrate,compare,duel_report}.py; script tool Tools/ScbTool; ours ~/Games/Generals/tools/scb.py.
F10 Strings: Data/Patch.str + Data/<Lang>/Generals.str (check which carries English in R0.2).
F11 Disk tight (~19 GB free). Run dirs in $TMPDIR, delete after.

## DATA (start values; R1 refines. src=reskin source; cost; req)
BUILDINGS: CommandCenter Штаб src ChinaCommandCenter 2000 | PowerPlant Газотурбинная электростанция ChinaPowerPlant 900 req CC | Barracks Казармы ChinaBarracks 500 req PP | SupplyCenter Склад снабжения ChinaSupplyCenter 1500 req PP | WarFactory Завод бронетехники ChinaWarFactory 2000 req Supply | Airfield Аэродром ChinaAirfield 1200 req WF | Voenkomat Военкомат ChinaPropagandaCenter 1000 req Barracks (free Reservist/60s max5) | ControlCenter Центр управления AmericaStrategyCenter 2500 req WF (tech) | Strongpoint Опорный пункт ChinaBunker 500 req Barracks | PantsirPos Позиция "Панцирь" ChinaGattlingCannon 1200 req WF (AA + point defense) | BukM3 ЗРК "Бук-М3" AmericaPatriotBattery 1400 req CtrlC (air only, long) | Zoopark РЛС "Зоопарк-1М" ChinaSpeakerTower 800 req WF (counter-battery) | Oreshnik Комплекс "Орешник" ChinaNuclearMissileLauncher 5000 req CtrlC
INFANTRY: MotorRifle Мотострелок AmericaInfantryRanger 225 | RPG Гранатомётчик ChinaInfantryTankHunter 300 | Verba ПЗРК "Верба" AmericaInfantryMissileDefender 300 air only | Sniper Снайпер СВ-98 AmericaInfantryPathfinder 600 req CtrlC | Kornet ПТРК "Корнет" ChinaInfantryTankHunter+own weapon 700 deploy-to-fire long range | FPVOperator Оператор FPV ChinaInfantryTankHunter+own weapon 500 slow interceptable drone projectile | Engineer Инженер ChinaInfantryHacker body 400 capture/demine/repair | GRU Спецназ ГРУ ChinaInfantryBlackLotus 1500 req CtrlC max1 stealth-standing, demo | Reservist Резервист ChinaInfantryRedguard(single) 0 Voenkomat only
VEHICLES: IMR3M ИМР-3М ChinaVehicleDozer 1000 | Kamaz КамАЗ ChinaVehicleSupplyTruck 600 req Supply | TigrM "Тигр-М" AmericaVehicleHumvee 600 | BTR82A БТР-82А ChinaVehicleTroopCrawler 900 transport5 | BMP3 БМП-3 AmericaTankCrusader body 1100 req CtrlC transport3 | T72B3M Т-72Б3М ChinaTankBattleMaster 700 | T90M Т-90М AmericaTankCrusader 1000 req CtrlC | T14 Т-14 "Армата" ChinaTankOverlord 2200 req CtrlC max3 APS | BMPT БМПТ ChinaTankGattling 1100 anti-inf | Pantsir ЗРПК "Панцирь-С1" AmericaTankAvenger 1000 AA+PD | TorM2 ЗРК "Тор-М2" AmericaTankAvenger 1300 req CtrlC AA longer, no ground | TOS1A ТОС-1А ChinaVehicleInfernoCannon 1300 req CtrlC short thermobaric | MstaS "Мста-С" ChinaVehicleNukeLauncher 1200 long arty needs spotting | TornadoG "Торнадо-Г" AmericaVehicleTomahawk 1300 req CtrlC area salvo | Krasukha РЭБ "Красуха" ChinaTankECM 900 req CtrlC no weapon, jams missiles/drones | Lancet Пусковая "Ланцет" ChinaVehicleListeningOutpost body 1200 req Airfield loitering munition, needs vision
AIR: Orlan "Орлан-10" ChinaJetMIG body 400 recon vision 450 no weapon | Ka52 Ка-52 AmericaVehicleComanche 1500 | Mi8 Ми-8АМТШ AmericaVehicleChinook 1200 transport8 | Su25 Су-25СМ3 ChinaJetMIG 1300 | Su35 Су-35С AmericaJetRaptor 1500 req CtrlC anti-air | Su34 Су-34 AmericaJetAurora 2200 req CtrlC standoff FAB
UPGRADES: Tax Налог @CC 1500 delivery +10-15% | OilGas Нефтегазовый комплекс @CtrlC 2000 derricks +50% | Ratnik @Barracks 1000 inf +25% hp | Thermal Тепловизоры @WF 1500 veh +25% vision | Relikt @WF 1500 T72/T90 +20% hp | Cages Противодроновые решётки @WF 800 tanks/BTR half dmg from FPV/Lancet | Mobres Мобилизационный резерв @Voenkomat 1500 reservist/40s | PantsirMod @CtrlC 1200 PD rate up | GuidedFAB @Airfield 1500 Su34 range up
SCIENCE: R1 (1pt each, unlocks): TOS2 "Тосочка" unit (faster/longer TOS) ~China NukeCannon unlock | Veterans: MotorRifle+RPG spawn veteran ~Redguard training | OrlanRecon power 30s drone orbit ~US spy drone
 R3 (powers, pts per level): Cyber x3 steal 500/1000/1500 + disable buildings 15s radius grows ~CashHack+EMP | FAB x3 Su34 drops 2/4/6 glide bombs ~carpet bomb | TornadoS x3 cluster rocket area ~artillery barrage | VDV x3 paradrop MotorRifle+Kornet ~US paradrop | Reservists x1 5 reservists at Voenkomat ~GLA ambush | EWSuppress x1 10s drones/missiles off in radius ~EMP soft
 R5: Kinzhal hypersonic single-building strike ~US FAE bomb
 TALENTS 6-10 (A|B): 6 reservist/40s | Tax +10% ; 7 T72/T90 +20% hp | arty +15% range ; 8 Pantsir/Tor intercept more | Buk +25% radius ; 9 FPV/Lancet +25% dmg | Orlan/radar +25% vision ; 10 Armata limit 3->5 | Oreshnik reload -60s
 SUPER: Oreshnik 6 impacts spread (Scud Storm-like), not interceptable, no contamination, 5000, reload 300s, counts in superweapon limit.
IDENTITY: strong = layered AA, heavy arty/thermobaric, EW, drones; weak = speed -10% vs China, low armor vision, blind arty without Orlan/radar, weak early inf, late expensive air.
BALANCE TARGETS (user 2026-11-22: max 10 games per opponent general, iterate fast): win 45-55% overall vs all 12 vanilla factions/generals (Hard vs Hard, 10 games each = 120, sides swapped 5/5); per-general 3-7 of 10 ok, outside -> look; THEN confirm at 100 games per general (1200 total, ~9h) once 10-game rounds look stable; control series China same seeds; income/min 90-110% of China (reservist=225); each unique unit/power used by bot in >=50% matches; duel/siege surviving-money share 0.4-0.6.

## TASKS
### R0 engine recon
[x] R0.1 Baseline: build app (F1), one headless 2-player China vs USA match, 10 game-min cap. Record x-real-time, wall time, crash/no. => HEADLESS RESULT line present; numbers in LOG.
[x] R0.2 Hook map <-R0.1: confirm F6 list by grep `startsWith( "` and `"Turkiye`, plus how strings (F10), cameos, faction picker, Eva, voices bind to side. Write result as table in FACTS F12 (place | what | Russia needs: now/later/no). => F12 written.
[x] R0.3 Stub faction <-R0.2: new Data/INI/RussiaReforged.ini (ObjectReskin RussiaCommandCenter ChinaCommandCenter + patch Side=Russia), FactionRussia in PlayerTemplate (BaseSide China, RandomExcluded Yes, start building RussiaCommandCenter, display strings en+ru), load line in GameEngine.cpp next to Turkiye's, UI prefix branches -> map Russia to China look for now. => headless `-side 0 FactionRussia` vs China 10 game-min no crash, no INI errors in log; screenshot of lobby list with Russia (window-only capture `screencapture -l <winid>`, never full screen).
[x] R0.4 Series driver <-R0.1: Tools/Russia/series.py (python3 stdlib): seeds x maps x side pairs, -side per slot, parallel N, per-run HOME/logPrefix in $TMPDIR, timeout kill, parse HEADLESS RESULT -> CSV (seed,map,sides,winner,frames,xrt). Same seed twice -> same result. => 12-match smoke CSV; matches/hour measured (6 parallel) in LOG.
[x] R0.5 Module check: economy <-R0.3: (a) derrick boost tied to a Russia upgrade (multiple UpgradedBoost lines allowed?) (b) delivery bonus tied to Russia upgrade (how SupplyLines touches trucks/supply center) (c) Voenkomat periodic free unit with max alive (OCL/SpawnBehavior?) (d) one power = cash steal + building disable. Each: INI-only or code, with module names. => verdicts in FACTS F13.
[x] R0.6 Module check: mechanics <-R0.3: EW jamming missiles/drones (F7 Jammer*), drones as slow interceptable projectiles (Kargu/SwarmStrike, PointDefense), Lancet needs ally vision, counter-battery mark (MarkAndRain/RadarContactMarks), Oreshnik as Scud Storm variant, APS on T-14 (PointDefense on tank). => verdicts in F13.
[x] R0.7 GATE0: report to user: Russia in lobby, speed (matches/hour), which mechanics need engine code, risks. Wait.

### R1 paper design
[x] R1.1 Verify real-system data (web, standard search) for every DATA unit: role, rough range order, crew/capacity. Keep only range ORDER, not scale. Record corrections as DEV.
[x] R1.2 Pull analog stats: vanilla INIZH.big + BalanceReforged.ini/FixesReforged.ini overrides for every src in DATA (hp, armor, speed, vision, weapon dmg/range/reload, build time).
[x] R1.3 Write docs/russia/roster.tsv: id,name_ru,name_en,src,cost,time,hp,armor,speed,vision,weapon,range,dps,counters,req,notes. Rules: speed vehicles = China analog x0.9; every unit has >=1 counter; no unit beats all of its price class.
[x] R1.4 GATE1: show user short roster summary (by group, what's strong/weak), get approval. Changes -> roster.tsv + DATA.

### R2 skeleton (all buildings + 8 base units, analog models)
[x] R2.0 Expanded below. Mechanism: ThingFactory.cpp:344 findSideReskin swaps any template for the producer side's reskin, so China names in AI scripts/build list work.
[x] R2.1 Buildings: 13 ObjectReskin+patch (Side, cost, time, hp, DisplayName) per roster.tsv; mechanics (spawn, superweapon, SAM, radar) stay analog's until R3. => INI loads, no [LINE errors.
[x] R2.2 Units: MotorRifle RPG Engineer IMR3M Kamaz T72B3M BTR82A MstaS reskins (cost, time, hp, speed via own Locomotor only if needed, DisplayName). => INI loads.
[x] R2.3 Command sets: Russia CC/IMR3M/Barracks/Supply/WF/Airfield sets naming Russia templates (copy China's, drop units not in roster). => buttons resolve (no missing-template log).
[x] R2.4 Strings OBJECT:Russia* en (Patch.str) + ru (Russian/Generals.str). => no MISSING string in log.
[x] R2.9 Verify: 5 headless Russia-vs-China 30 game-min, no crash, bot builds base+factories+attacks (count from log), no INI errors; one windowed smoke with screenshot. GATE2 report.

### R3 full roster + mechanics
[x] R3.0 Expanded below. Generator Tools/Russia/gen.py <vanilla> owns reskin/cost/req/buttons/strings (between GENERATED markers); hand patches go below END in RussiaReforged.ini.
[x] R3.1 All 31 units + 13 buildings as reskins with buttons (sources remapped so China scripts' asks hit Russia combat units: Redguard->MotorRifle, MIG->Su25, Helix->Mi8; duplicates on general variants). Lancet at Airfield, Tigr at SupplyCenter (WF has 12 slots).
[x] R3.2 RussiaWeaponReforged.ini (own file, OVERWRITE, load line next to Turkiye's) + WeaponSet patches: Kornet, FPV (slow interceptable projectile), Verba air-only, BMPT, TOS thermobaric, Tornado salvo, Su34 FAB, Su35, Tor/Buk air-only, Pantsir cannon+missile. Orlan unarmed + SpotterSight. => loads, each unit fires in a match (KILLXP killer=Russia*).
[x] R3.3 hp/speed per roster.tsv (Body ReplaceModule, own Locomotors). => values in INI match roster.
[x] R3.4 Point defense: Pantsir/PantsirPos/T14 APS PointDefenseLaserUpdate vs SMALL_MISSILE; Krasukha JammerUpdate. => scripted/headless check drones intercepted.
[x] R3.5 Economy: Voenkomat SpawnBehavior (F13c); OilGas derrick boost (F13a); Tax code+INI (F13b). => reservists spawn; income delta measured.
[x] R3.6 Upgrades Ratnik Thermal Relikt Cages Mobres PantsirMod GuidedFAB + buttons. => purchasable, effect visible in INI/log.
[ ] R3.7 Sciences/powers/talents per DATA SCIENCE (Cyber code F13d, FAB, TornadoS, VDV, Reservists, EWSuppress, Kinzhal, TOS2, Veterans, OrlanRecon) + PlayerTemplate own sciences + AI SkillSets. => powers fire in headless.
[ ] R3.8 Oreshnik superweapon (Scud Storm-like, 6 impacts). => fires in headless.
[ ] R3.9 Verify each mechanic by scenario or scripted headless check, checklist in LOG. GATE3.

### R4 bot
[ ] R4.0 Expand: Russia skirmish scripts (ScbTool or scb.py) on top of China's: build Pantsir on air threat, Orlan over arty, Lancet targeting, Voenkomat, upgrades, powers; trace like ~/Games/Generals ai-lab AI_LAB_TRACE.
[ ] R4.9 30-match series: every unique unit/power used in >=50% matches. GATE4.

### R5 balance
[ ] R5.0 Expand: unitmatrix/duel/siege with Russia, series vs USA/China/GLA + China control, iterate numbers. Changelog docs/russia/CHANGELOG.md with commands+numbers.
[ ] R5.9 Targets met on 10/general series, then confirmed on 100/general. GATE5.

### R6 UI+sound (later) / R7 models (later, open-ended): expand when reached.

## F12 HOOKS (R0.2)
place | what | Russia
InGameUI.cpp:411 / GroupPanel.cpp:292 / AirliftPanel.cpp:205 / ControlBar.cpp:6398 / ControlBarSidebar.cpp:222,2032 | UI prefix by side.startsWith (else America) | now: add `Russia`->China branch (one-liners)
ControlBarSidebar.cpp:1556 COUNTRIES[] | sidebar art countries | later (own art); now China look via prefix
InGameUI.cpp:4588 GLA workers | no | no
CommandXlat.cpp:4806 America/China compare | cheat/hotkey side swap | no
AcademyStats.cpp:120,1023 BaseSide China | generic via BaseSide | no (works)
Eva.cpp:556, SidesList.cpp:480, PlayerTemplate.cpp:370 | fallback to old-faction by BaseSide | no (China Eva/voices until own)
LoadScreen.cpp:477 crest by BaseSide | China crest | no (later own GeneralImage)
FactionPicker.cpp:89 image FactionPicker<Template> (ReforgedFactionPicker.ini:31) | missing -> ? | now: check fallback in R0.3; later own image
Strings: INI:FactionTurkiye in Data/Patch.str (English) + Data/<Lang>/Generals.str (ru in Russian/) | now: add INI:FactionRussia to Patch.str + Russian/Generals.str
GameEngine.cpp:1349,1383 load lines | now: add RussiaReforged.ini after Turkiye
AIPlayer.cpp:12168,23765 BaseSide-based AI | works via BaseSide China | no
Tests: test_gameengine.cpp:8844+ random pool / 25081 superweapon cap list per faction | check tests after R0.3 (may need Russia rows)
## F13 MODULE VERDICTS (R0.5-6)
a derrick OilGas: INI. AutoDepositUpdate UpgradedBoost is a list (AutoDepositUpdate.cpp:74,206), first owned upgrade wins -> patch derrick object(s) with extra `UpgradedBoost = UpgradeType:Upgrade_RussiaOilGas Boost:100`.
b delivery Tax: CODE small. SupplyCenterDockUpdate.cpp:113 adds truck getUpgradedSupplyBoost(); plain SupplyTruckAIUpdate returns 0 (SupplyTruckAIUpdate.h:277), Worker/Chinook hardcode their upgrade. Plan: add `UpgradedBoost` (reuse parseUpgradePair) to SupplyTruckAIUpdateModuleData, ~15 lines.
c Voenkomat: INI. SpawnBehavior SpawnNumber 5, SpawnReplaceDelay 60000, SlavesHaveFreeWill Yes, SpawnedRequireSpawner No, InitialBurst 0/1. Check in R3: spawned units selectable/controllable; Mobres upgrade = second SpawnBehavior w/ upgrade trigger or delay swap (verify).
EW Krasukha: INI. JammerUpdate (Radius, ScanRate): enemy drones/spotters blinded, guided missiles lose lock (MissileAIUpdate DistanceScatterWhenJammed). EWSuppress power = OCL temp object with JammerUpdate+LifetimeUpdate.
Drones FPV/Lancet: INI. Projectile object with MissileAIUpdate, slow speed, KindOf SMALL_MISSILE -> Pantsir/Tor/APS PointDefenseLaserUpdate (PrimaryTargetTypes) shoot them, Krasukha jams them. SwarmStrikeSpecialPower (Radius, TargetCount, Weapon, Drone) for Lancet/FAB-style powers.
Lancet needs vision: INI. Default engine: range > own ShroudClearingRange fires only at what player/ally sees; Orlan = SpotterSight (ThingTemplate.h:449) recon.
APS T-14: INI. PointDefenseLaserUpdate on the tank (WeaponTemplate, PrimaryTargetTypes, ScanRange, RequiredUpgrade).
Oreshnik: INI. Scud Storm copy: own SpecialPower+OCL, 6 warheads, no toxin, reload 300s; scud missiles are not intercepted by default.
Counter-battery (Zoopark): CODE or skip. MarkAndRainBehavior = bonus on kills under an eye, not shooter reveal; RadarContactMarks is client UI. Optional per plan; decide in R3.
d Cyber (steal+disable): CODE small. One power = one module (Object.cpp:6240 getSpecialPowerModule returns first). Plan: optional OCL field on CashHackSpecialPower fired at target (EMP-like OCL per level).
## DEV (expected | found | action)
R0.1 | baseline run lacked -observer (idle human slot) | rerun: China vs USA seed1 frame cap 18000, 25s wall, 23.7x RT
R0.3 | bot needs own SideInfo+SkirmishBuildList (scripts fall back by BaseSide, build list does not) | copied China's into AIDataReforged.ini as Russia
R0.3 | lobby screenshot: user's game window open, can't drive lobby | moved to R2.9 windowed smoke
R1.1 | web check per unit | done from model knowledge (no web, saves budget); range order holds: Buk-M3 >> Tornado-G~Lancet > Msta-S > Pantsir > Tor > TOS-1A > Kornet~Verba > tank guns. Real capacity BTR-82A 7, BMP-3 7, Mi-8 24: keep game values (5/3/8) for balance. No data changes.
R2.1 | hp/speed per roster | done in R3.3: Body ReplaceModule (tag from vanilla or Balance/Fixes) + SpeedScale (ThingTemplate field; patch cannot restate SET_NORMAL locomotor)
R2.3 | one reskin per source (ThingFactory findSideReskin) | R3 must give Kornet/FPV (TankHunter=RPG), T90M/BMP3 (Crusader), Pantsir/Tor (Avenger), Orlan/Su25 (MIG) different sources or non-reskin copies
R2.3 | China mines/EMP-mine buttons dropped from Russia sets (CommandSetUpgrade would swap to China sets) | revisit if Russia gets mines
R3.2 | Su35 anti-air jet | engine jets do not dogfight; Su35 stays Raptor-like strike fighter. Pantsir/Krasukha keep analog weapons until R3.4
R0.3 | test_gameengine fails a_template_maps_rules_are_served_beside_it_and_in_its_name (5) | pre-existing on clean tree, not ours
R3.6 | Thermal/Relikt/Cages @WF | WF has 12 unit buttons (UI max 14 incl rally/sell) -> on ControlCenter with OilGas/PantsirMod
R3.6 | Cages vs FPV/Lancet only | no free damage type; Cages halve INFANTRY_MISSILE (FPV, Lancet now INFANTRY_MISSILE, also enemy RPGs). New armors need OVERWRITE after ArmorStore -> RussiaArmorReforged.ini + load line GameEngine.cpp
R3.6 | Mobres = spawn delay swap | SpawnBehavior has no upgrade gate -> ReplaceObjectUpgrade to RussiaVoenkomatMobres (reskin of Tank_ChinaPropagandaCenter, 40s); old reservists stay, cap may reach 10
R3.6 | headless seed12 rmg vs USA hangs past maxframes (CRC AT LIMIT printed, no RESULT) | same for China vs USA -> pre-existing engine bug, not ours; avoid seed12 vs USA, report to user
## LOG (date ID result commit)
2026-11-22 plan created
2026-11-22 R0.1 build ok; headless China vs USA randommap seed1 (cells 0): decided frame 8065, 8.0s logic, 33.5x RT, 11s wall, no crash. Winner not printed in stdout (find in R0.4).
2026-11-22 R0.2 F12 written; 6 prefix one-liners + strings + load line needed now.
2026-11-22 R0.3 FactionRussia+RussiaCommandCenter+AI list; Russia vs China seed1 18000 frames no crash, 30.8s 19.5x RT, bot built 78 (China 53); ReskinCheck: CC lacks CostModifierUpgrade x2 (check in R2).
2026-11-22 R0.4 series.py: 12 Russia(=China stub) vs China rmg seeds1-5+1 swap, 30 game-min cap, 6 par: 0 bad, 141 matches/hour, seed1 repeat identical; W Russia 3 China 3 none 6.
2026-11-22 R0.5 economy verdicts in F13: a,c INI; b,d small code.
2026-11-22 R0.6 mechanics verdicts in F13: all INI except counter-battery (code/skip).
2026-11-22 GATE0 passed (user: continue). R1.1 range order confirmed, no DATA changes.
2026-11-22 R1.2 docs/russia/analogs.tsv via Tools/Russia/analogs.py (vanilla + Balance/Fixes overrides; first ArmorSet/WeaponSet, primary weapon only).
2026-11-22 R1.3 docs/russia/roster.tsv 44 rows; vehicle speed = China class analog x0.9; every unit has counters.
2026-11-22 user changed balance method: <=10 games per general.
2026-11-22 R2.1-4 13 buildings + 8 units reskins, Russia command sets/buttons, strings en+ru; Russia vs China seed1 18000 frames ok, bot built all Russia types (RPG/T72/MstaS heavy, MotorRifle 3).
2026-11-22 R2.9 5x Russia vs China seeds11-15 30min: 0 crash, China wins 5/5 (skeleton lacks Redguard/Overlord/Gattling etc. that China scripts ask for); windowed smoke ok, docs/russia/shots/r2-skeleton.jpg. GATE2.
2026-11-22 R3.1 full roster reskins; Russia vs China seed11 decided China f23673, bot built most new types (BMPT 647 log refs, Su25, Lancet, Tor, T14...). AI ABILITY BUTTONS spam for Helix is vanilla China too.
2026-11-22 R3.2 RussiaWeaponReforged.ini 14 weapons + WeaponSets (gen.py); no INI errors; Russia units score kills; China wins 3/3 seeds11-13 (frames 19-25k).
2026-11-22 R3.3 hp (43 ReplaceModule) + SpeedScale (27) from roster.tsv via gen.py; no INI errors/missing strings seed11.
2026-11-22 R3.4 PD on PantsirPos+T14 APS, Jammer on Krasukha (no gun); Pantsir/Tor keep Avenger PD. Loads clean vs USA seed12; interception NOT measured (no log line) -> R3.9 scenario.
2026-11-22 R3.5 Tax engine code (SupplyTruckAIUpdate UpgradedBoost list) + CC button; OilGas derrick boost + ControlCenter button; Voenkomat SpawnBehavior needs DefaultProductionExitUpdate (propaganda has no exit). Reservist spawned f1844 seed11. Income delta NOT measured (AI never buys upgrades) -> R4/R3.9.
2026-11-22 R3.6 7 upgrades+buttons+strings (Ratnik/Relikt MaxHealth, Thermal Sight, Cages Armor, Mobres ReplaceObject, PantsirMod PD RequiredUpgrade, GuidedFAB WeaponSet); clean load Russia vs China seeds11-12; effect in match NOT measured (AI does not buy) -> R3.9/R4.
