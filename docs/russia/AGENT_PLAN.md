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
NOW: -
LAST: R8.7 PowerPlant own model 2026-11-24; bld.py UV flip fixed (Zoopark textures were upside down in game). User has not seen R8.4-R8.7 in game yet.
NEXT-NOTE: R8 queue (user-approved 2026-11-23): 1 done (R8.4) 2 done (R8.5) 3 buildings w/ animation (R8.6 Zoopark, R8.7 PowerPlant done; next WarFactory, Pantsir pos, rest, one per session; bld.py) 4 vehicles 1/session 5 weapon sounds 6 aircraft 7 infantry (decide: rig or keep reskins). Every model: _D, wreck, debris, shadow check; user review every 2-3 models.
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
F12 Own models (R8, D2 changed by user 2026-11-23: own models instead of reskins): Gemini ortho refs (side/top/front/rear + burnt) -> Tools/Russia/models/<unit>/config.json pixel landmarks -> `uv run Tools/Russia/models/contours.py <dir>` -> `uv run .../atlas.py <dir>` -> `blender -b --factory-startup --python .../build.py -- <dir>` -> `python3 -I .../make.py <dir> <retail W3D dir: avcrusader.W3D, NVBtMstr.W3D from W3DZH.big>` -> Art/W3D + Art/Textures. INI by hand below `;; RUSSIA MODELS` in RussiaReforged.ini. ReplaceModule must name the tag after Balance/Fixes Reforged (e.g. ModuleTag_01_Reforged), check log for 'was not found'. Budget ~3k tris (EA tanks 250-450). Atlas 1024 (user 2026-11-23, repo size). Buildings: `uv run Tools/Russia/models/bld.py <dir with avcrusader.W3D>` (boxes/posts + procedural 512 atlas, anim via w3d.build(anim=)), preview `blender -b --factory-startup --python .../bld.py -- preview`; in-game picture: Scenarios/russia_zoopark.txt header (stage dev overlay: `bash GeneralsMD/Code/Tools/stage-overlay.sh GeneralsMD/Code/Data "" build-mac/overlay-dev --dev`, pass app Overlay + overlay-dev as -overlay; scenario health skips structures -> scratch INI overlay for _D/_E). Projectiles: `uv run Tools/Russia/models/proj.py <dir with avcrusader.W3D>` (primitives, no refs), preview `blender -b --factory-startup --python .../proj.py -- preview`; objects under `; Projectiles` in RUSSIA MODELS, ProjectileObject set in gen.py WEAPONS.
F11 Disk tight (~19 GB free). Run dirs in $TMPDIR, delete after.

## DATA (start values; R1 refines. src=reskin source; cost; req)
BUILDINGS: CommandCenter Штаб src ChinaCommandCenter 2000 | PowerPlant Газотурбинная электростанция ChinaPowerPlant 900 req CC | Barracks Казармы ChinaBarracks 500 req PP | SupplyCenter Склад снабжения ChinaSupplyCenter 1500 req PP | WarFactory Завод бронетехники ChinaWarFactory 2000 req Supply | Airfield Аэродром ChinaAirfield 1200 req WF | Voenkomat Военкомат ChinaPropagandaCenter 1000 req Barracks (free Reservist/60s max5) | ControlCenter Центр управления AmericaStrategyCenter 2500 req WF (tech) | Strongpoint Опорный пункт ChinaBunker 500 req Barracks | PantsirPos Позиция "Панцирь" ChinaGattlingCannon 1200 req WF (AA + point defense) | BukM3 ЗРК "Бук-М3" AmericaPatriotBattery 1400 req CtrlC (air only, long) | Zoopark РЛС "Зоопарк-1М" ChinaSpeakerTower 800 req WF (counter-battery) | Oreshnik Комплекс "Орешник" ChinaNuclearMissileLauncher 5000 req CtrlC
INFANTRY: MotorRifle Мотострелок AmericaInfantryRanger 225 | RPG Гранатомётчик ChinaInfantryTankHunter 300 | Verba ПЗРК "Верба" AmericaInfantryMissileDefender 300 air only | Sniper Снайпер СВ-98 AmericaInfantryPathfinder 600 req CtrlC | Kornet ПТРК "Корнет" ChinaInfantryTankHunter+own weapon 700 deploy-to-fire long range | FPVOperator Оператор FPV ChinaInfantryTankHunter+own weapon 500 slow interceptable drone projectile | Engineer Инженер ChinaInfantryHacker body 400 capture/demine/repair | GRU Спецназ ГРУ ChinaInfantryBlackLotus 1500 req CtrlC max1 stealth-standing, demo | Reservist Резервист ChinaInfantryRedguard(single) 0 Voenkomat only
VEHICLES: IMR3M ИМР-3М ChinaVehicleDozer 1000 | Kamaz КамАЗ ChinaVehicleSupplyTruck 600 req Supply | TigrM "Тигр-М" AmericaVehicleHumvee 600 | BTR82A БТР-82А ChinaVehicleTroopCrawler 900 transport5 | BMP3 БМП-3 AmericaTankCrusader body 1100 req CtrlC transport3 | T72B3M Т-72Б3М ChinaTankBattleMaster 800 | T90M Т-90М AmericaTankCrusader 1000 req CtrlC | T14 Т-14 "Армата" ChinaTankOverlord 2200 req CtrlC max3 APS | BMPT БМПТ ChinaTankGattling 1100 anti-inf | Pantsir ЗРПК "Панцирь-С1" AmericaTankAvenger 1000 AA+PD | TorM2 ЗРК "Тор-М2" AmericaTankAvenger 1300 req CtrlC AA longer, no ground | TOS1A ТОС-1А ChinaVehicleInfernoCannon 1300 req CtrlC short thermobaric | MstaS "Мста-С" ChinaVehicleNukeLauncher 1200 long arty needs spotting | TornadoG "Торнадо-Г" AmericaVehicleTomahawk 1300 req CtrlC area salvo | Krasukha РЭБ "Красуха" ChinaTankECM 900 req CtrlC no weapon, jams missiles/drones | Lancet Пусковая "Ланцет" ChinaVehicleListeningOutpost body 1200 req Airfield loitering munition, needs vision
AIR: Orlan "Орлан-10" ChinaJetMIG body 400 recon vision 450 no weapon | Ka52 Ка-52 AmericaVehicleComanche 1500 | Mi8 Ми-8АМТШ AmericaVehicleChinook 1200 transport8 | Su25 Су-25СМ3 ChinaJetMIG 1300 | Su35 Су-35С AmericaJetRaptor 1500 req CtrlC anti-air | Su34 Су-34 AmericaJetAurora 2200 req CtrlC standoff FAB
UPGRADES: Tax Налог @CC 1500 delivery +10-15% | OilGas Нефтегазовый комплекс @CtrlC 2000 derricks +50% | Ratnik @Barracks 1000 inf +25% hp | Thermal Тепловизоры @WF 1500 veh +25% vision | Relikt @WF 1500 T72/T90 +10% hp (R5.0) | Cages Решётчатые экраны (renamed 2026-11-23: only Russia has kamikaze drones) @WF 800 tanks/BTR/BMP half INFANTRY_MISSILE (RPG, inf missiles, FPV/Lancet), BMPT quarter | Mobres Мобилизационный резерв @Voenkomat 1500 reservist/40s | PantsirMod @CtrlC 1200 PD rate up | GuidedFAB @Airfield 1500 Su34 range up
SCIENCE: R1 (1pt each, unlocks): TOS2 "Тосочка" unit (faster/longer TOS) ~China NukeCannon unlock | Veterans: MotorRifle spawns veteran (R5.0: RPG dropped) ~Redguard training | OrlanRecon power 30s drone orbit ~US spy drone
 R3 (powers, pts per level): Cyber x3 steal 500/1000/1500 + disable buildings 15s radius grows ~CashHack+EMP | FAB x3 Su34 drops 2/4/6 glide bombs ~carpet bomb | TornadoS x3 cluster rocket area ~artillery barrage | VDV x3 paradrop MotorRifle+Kornet ~US paradrop | Reservists x1 5 reservists at Voenkomat ~GLA ambush | EWSuppress x1 10s drones/missiles off in radius ~EMP soft
 R5: Kinzhal hypersonic single-building strike ~US FAE bomb
 TALENTS 6-10 (A|B): 6 reservist/40s | Tax +10% ; 7 T72/T90 +20% hp | arty +15% range ; 8 Pantsir/Tor intercept more | Buk +25% radius ; 9 FPV/Lancet +25% dmg | Orlan/radar +25% vision ; 10 Armata limit 3->5 | Oreshnik reload -60s
 SUPER: Oreshnik 6 impacts spread (Scud Storm-like), not interceptable, no contamination, 5000, reload 300s, counts in superweapon limit.
IDENTITY: strong = layered AA, heavy arty/thermobaric, EW, drones; weak = speed -10% vs China, low armor vision, blind arty without Orlan/radar, weak early inf, late expensive air.
BALANCE TARGETS (user 2026-11-22: max 10 games per opponent general, iterate fast): win 45-55% overall vs all 12 vanilla factions/generals (Hard vs Hard, 10 games each = 120, sides swapped 5/5); per-general 3-7 of 10 ok, outside -> look; THEN confirm at 100 games per general (1200 total, ~9h) once 10-game rounds look stable; control series China same seeds; income/min 90-110% of China (reservist=225); each unique unit/power used by bot in >=50% matches; duel/siege surviving-money share 0.4-0.6.

## TASKS
[x] R0 done: engine recon, hooks F12, stub faction, series.py (141 matches/h), module verdicts F13. GATE0 passed.
[x] R1 done: roster.tsv 44 rows, analogs.tsv; range order checked. GATE1 passed.
[x] R2 done: 13 buildings + base units reskins, command sets, strings en+ru; 5 headless clean. GATE2 passed.
[x] R3 done: 31 units + mechanics (PD/APS, Krasukha jammer, Tax/OilGas/Voenkomat, 7 upgrades, sciences+8 powers, talents 6-10, Oreshnik) via Tools/Russia/gen.py; scenarios russia_powers/russia_oreshnik pass. GATE3 passed.

### R4 bot
[x] R4.0 Expand: Russia skirmish scripts (ScbTool or scb.py) on top of China's: build Pantsir on air threat, Orlan over arty, Lancet targeting, Voenkomat, upgrades, powers; trace like ~/Games/Generals ai-lab AI_LAB_TRACE.
[x] R4.9 30-match series: every unique unit/power used in >=50% matches. GATE4. (Oreshnik fire 14/30 carried to R5: dies to GLA early)

### R5 balance
[x] R5.0 Expand: unitmatrix/duel/siege with Russia, series vs USA/China/GLA + China control, iterate numbers. Changelog docs/russia/CHANGELOG.md with commands+numbers.
[x] R5.9 confirmation 50/30/16 per pair (user cut): vs USA/China in band except Tank 28%, GLA 4% vs controls 2-3%; overall 32% (GLA). GATE5 reported.

### R6 UI+sound (user 2026-11-23: no model changes). Pattern = Turkiye (F5): own HUD side via generators, own cameos/voices/Eva.
[x] R6 done: own HUD panel + picker insignia (R6.1-2); 20 icons + emblem as realistic photos (Higgsfield z_image, Tools/Russia/art, icons.py); 434 unit lines + 36 Eva in Russian (Qwen3-TTS local, voices.py, whisper gate). GATE6 user ok 2026-11-23. Eva in game checked 2026-11-23: Russia match, enemy tanks at base -> erbase/erlost/erbsto/erbcap opened (lsof), no China Eva files.

### R7 portraits (user 2026-11-23: build buttons and selection portraits show source models, e.g. T-90 = China tank)
[x] R7 done: 45 unit/building photos (Gemini Pro web via playwriter, 3 Google profiles; Higgsfield credits short) in Tools/Russia/art/cameo + PROMPTS.tsv; icons.py -> RUCameos.tga 2048 (240x192 portraits, 120x96 buttons) + RUCameos.ini; gen.py sets SelectPortrait/ButtonImage + build buttons; Mobres by hand. Grep: 0 Russia buttons/objects with source cameo. Windowed game: HQ/IMR-3M portraits, IMR button, dozer build panel all own.

### R8 own models (queue in STATE NEXT-NOTE)
[x] R8.4 T-72 upgrade parts: slat cages + Relikt blocks as hidden sub-objects, SubObjectsUpgrade shows them => headless match with both upgrades clean, sub-objects in W3D, preview renders with/without.
[x] R8.5 own projectiles (queue item 2): Tools/Russia/models/proj.py builds W3D from primitives (lathe, fins, boxes, rotor discs; swatch texture RUProj). Models: FPV quad, Lancet, Kornet ATGM, Tornado-G rocket, Buk 9M317, Tor 9M338. Objects = ObjectReskin of current vanilla projectile + own Draw (behaviour unchanged); gen.py sets ProjectileObject. Out of scope: Verba (tiny), Oreshnik/Kinzhal (power visuals), Orlan-10 -> aircraft item 6. => W3D roundtrip ok, previews look right, headless series with all 6 weapons fired, no INI/model errors.
[x] R8.6 buildings w/ animation (queue item 3), first = Zoopark radar: w3d.py writes ANIMATION chunk (Q channels per pivot); Tools/Russia/models/bld.py builds buildings from primitives + procedural 512 atlas (alive/_D damaged/_E rubble, bones Smoke01/02 Flame01 Spark01). Zoopark: pad, cabin, generator, pedestal, phased-array antenna rotating (loop). Draw ReplaceModule ModuleTag_01 (construction ModuleTag_02 kept), Geometry unchanged. => W3D roundtrip + anim frames parse, Blender preview, windowed game screenshot shows model (anim visible across 2 shots), headless match clean. Next buildings one per session: PowerPlant (turbine fans), WarFactory (door), Pantsir position, rest.
[x] R8.7 PowerPlant own model (gas turbine plant): bld.py powerplant(), turbine hall + stacks + air-cooler fans turning (anim), _D/_E; Draw ReplaceModule ModuleTag_01 (scaffold 02-04 kept), POWER_PLANT_UPGRADED (Overcharge) spins fans faster + sparks. => W3D roundtrip, Blender preview, windowed scenario shot, headless match clean.
[ ] R8.7b proj.py UVs: same V flip as bld.py had (swatch_uv row y -> v = y/128, game reads v bottom-up like T-72 export) -> projectile colours likely shifted a row; fix like bld.ruv, rebuild 6 projectiles, windowed check. Then next building WarFactory.


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
R3.7 | talents in same task | split to R3.7b (own effects, ~10 blocks) | -
R3.7 | TOS2 at WF | WF full (12) -> SupplyCenter; src Nuke_ChinaVehicleInfernoCannon, req SCIENCE_RussiaTOS2 (gen.py Science prereq)
R3.7 | powers own visuals | dev stand-ins: FAB=China carpet bomber 2/4/6 bombs, Kinzhal=SupW cruise missile, TornadoS=China barrage OCLs, Orlan=US spy drone, VDV=US cargo plane
R3.7 | AI fire-when-ready aims at a spot; Cyber (object power) did nothing and spammed 887x/6 matches | CashHackSpecialPower: script-fired at location hacks nearest enemy structure within 300
R3.7 | 7 science points by rank 5 | bot sets reach Kinzhal; EWSuppress (set1 8th) never bought -> R4 if >=50% use needed
R3.7b | T14 max3 in roster | never set in INI -> MaxSimultaneousOfType 3 now; 10A needs per-player cap -> ThingTemplate MaxSimultaneousUpgrade = <science> <n> (Player::canBuildMoreOfType)
R3.7b | 6B Tax talent | truck UpgradedBoost was first-wins -> sums owned boosts (Tax 50 + talent 30)
R3.7b | 10B Oreshnik reload | power does not exist yet -> R3.8 keys it on SCIENCE_RussiaTalent10B
R3.8 | silo MissileLauncherBuildingUpdate kept SuperweaponNeutronMissile -> crash on fire | ModuleTag_09 replaced with Oreshnik template
R3.8 | bot never builds Oreshnik (Russia builds 0 defenses, superweapon 0 in 6x72000 frames) | checked by scenario russia_oreshnik (needs -overlay with Scenarios/) -> bot build order R4
R4.0 | China scripts enough via reskins | bot fielded only what China teams name (27/62 unique items); no Control Center ever (build list had ChinaInternetCenter) | Tools/ScbTool/russia.py: own player SkirmishRussia (stand-in by playerFaction), teams with Russia units, Control Center/Buk/upgrade scripts; build list CtrlC; usage tool Tools/Russia/usage.py
R4.0 | MstaS buildable at WF | inherited SCIENCE_NukeLauncher prereq (China science) | gen.py writes empty Prerequisites when roster req is empty (20 objects)
R4.0 | Buk ok | Patriot AssistedTargetingUpdate used missing SECONDARY slot -> crash once bot built Buk | RemoveModule ModuleTag_07
R4.0 | Mobres bought once | ReplaceObjectUpgrade dropped AI build-list entry -> rebuild+rebuy loop (29x/match) | engine: ReplaceObjectUpgrade hands build-list entry to replacement
R4.0 | all powers >=50% | 7 science points (ranks 1-5) for 9 picks (Orlan, TOS2, 6 powers, Kinzhal); set picked by AI role, set2 ~10/12 | TornadoS+EWSuppress only in set1 -> ask user at GATE4 (points or metric)
R4.9 | Mobres bought by scripts | Upgrade_RussiaMobres was OBJECT; AIPlayer::buildUpgrade skips OBJECT upgrades | Type=PLAYER, button PLAYER_UPGRADE -> 25/30
R6.1 | Russia HUD on China terraced build | pagoda eaves read Chinese | machined build (America layout, scheme+MappedImages copied from America), olive steel+brass; generators run on mac with WINDIR=dir holding Fonts/arialbd.ttf, launcher emblem.svg absent -> Logo pasted from America sheet
R6.3 | smoke seed 2 | -randommap 2 2 0 never starts the match (frames climb, 0 AI groups) also China-USA | outside Russia; told user
R4.9 | Oreshnik fires >=50% | built 25/30, fires 12/30; vs GLA Russia dies before first charge | balance, R5
R5.0 | GLA bot beats every base faction (China 0-10, USA 0-8-2) | user chose own anti-GLA scripts; done: Buk off vs GLA, engine enemy-miss cache fix, air-only defenses out of AI defense ring; GLA still 0-10 -> 3-7 vs GLA unreachable without breaking others, report user |
R5.0 | old note: Russia loses to GLA by own weakness | China control also 0-10 vs GLA same seeds; Russia trades 0.59 vs China's 0.49 | GLA fix = stronger own Russia scripts (not opponents'), ask user; vs China 10-0 too strong, suspect AA wall (CHANGELOG)
R8.1 | ReplaceModule ModuleTag_01 on T72 | BalanceReforged renamed Battlemaster draw to ModuleTag_01_Reforged, death to ModuleTag_12_Reforged + 2 AddModules | replace those tags; own hull object RussiaVehicleT72DeadHull + OCL_RussiaT72Toss/Wreck
R8.1 | 5022 tris (Battlemaster 265) | contour_eps 8 -> 3162, same look; LOD only if user sees lag
R8.7 | bld.py UVs right (Zoopark looked ok in shots) | ruv wrote v = y/A, W3D v is bottom-up (T-72 export uses Blender v) -> every atlas region read from the mirrored row: pad showed olive panels, red test fill landed on cooler top | ruv v = 1 - y/A, preview reads v as is; Zoopark W3D rebuilt (textures unchanged); proj.py likely same -> R8.7b
## LOG (date ID result commit)
2026-11-22 R0-R2: build ok, headless 33x RT, series 141/h; skeleton clean, China wins 5/5 vs skeleton.
2026-11-22 R3: full roster+mechanics; powers fire (Cyber 13 FAB 18 Kinzhal 25 Orlan 77 ... EWSuppress 0); Oreshnik fires; talent effects and bot Oreshnik/EWSuppress/defenses NOT verified -> R4.
2026-11-22 GATE3 passed (user: делай).
2026-11-22 R4.0 own SkirmishRussia scripts + 3 data/engine fixes; 12 matches vs China/USA/GLA seeds1-2 swap: unique items <50% 35/62 -> 4/62 (Su34 5, Mobres 3 before loop fix, EWSuppress 2, TornadoS 2); W Russia 5 China 1 GLA 4 none 2.
2026-11-22 R4.9 u6 30 matches: below 50% 3/62 (EWSuppress 9, TornadoS 10, Oreshnik fire 12); W vs China 6-3-1, USA 5-3-2, GLA 1-9; GATE4 open
2026-11-22 GATE4 user: free rank-1 sciences. u7 30 matches: below 50% 1/62 (Oreshnik fire 14); EWSuppress 28 TornadoS 27; W vs China 10-0, USA 6-1-3, GLA 1-9.
2026-11-22 R5.0 baseline 30 matches: Russia-GLA 1-9, China-GLA 0-10, Russia-China 10-0; income 92-108% of China; asked user.
2026-11-22 R5.0 nerf T72 800, TOS2 1800, Veterans MotorRifle only; 20/pair: vs China 15-3-2 (was 18-0-2), vs USA 10-3-7; USA-China 3-3-14; GLA unchanged 0-10.
2026-11-22 R5.0 powers reload up, 1 Voenkomat, Relikt 10%: vs China 11-5-4/20; 12 generals x10 35-55-30; vs GLA Russia 3-33-4, China 1-38-1, USA 0-31-9.
2026-11-23 R5.9 648 matches: Russia 169-207-144, vs GLA 5/120 (USA 2/64, China 1/64); usage 61/62 (Oreshnik fire 5/24).
2026-11-23 R6 done: HUD, picker, icons (redo x2 by user feedback: glyphs->photos, 5 action shots->static close-ups), voices+Eva Qwen3-TTS; headless Russia-China seed1 clean.
2026-11-23 R7 portraits: 45 Gemini photos (T14 redone: no painted markings), atlas+wiring, in-game check HQ/dozer panels.
2026-11-23 R8.1 own T-72B3M (RUT72): 3162 tris, alive/damaged/wreck/turret, treads+wheels+pitch; headless Russia-China clean; user tested in game: ok.
2026-11-23 R8.4 T-72 parts: CAGES01/02 (slats hull sides+rear, turret basket) RELIKT01/02 (skirts, glacis, turret roof+front), +1884 tris only when bought; hidden in default state, SubObjectsUpgrade x2; 3 headless Russia-China rmg clean, bot bought Cages 3/3 Relikt 2/3; headless draws nothing -> look checked only in Blender preview.
2026-11-24 R8.5 proj.py: RUFPV 412 tris, RULANCET 292, RUKORNET 212, RUGRAD 248, RUBUKM 256, RUTORM 236; RUProj.tga 128 swatches + RUProjRotor.tga alpha (shader from TRKARGU.ROTORS); FPV/Lancet lost smoke exhaust; 6 headless Russia vs USA/China rmg clean, all 6 launchers built 5-6/6, Lancet/FPV projectiles seen in AI DEFLOSS; headless draws nothing -> look checked only in Blender preview.
2026-11-24 R8.6 bld.py + w3d anim: RUZOOPARK 218 tris (pad, cabin, generator, mast, phased array on ANTENNA01 turning 8 s / 12 s damaged), _E array torn off lying on ground; 3 headless Russia-China rmg clean, Zoopark built in all 3; windowed scenario shots: frames 200/240 array turned, _D/_E via scratch INI overlay ok.
2026-11-24 R8.6 user: Zoopark ok, but red rings. Rings = inherited China PropagandaTower pulse; unpowered tower showed none in a recorded run. PulseFX None (heal kept), video: no rings, powered array turns, unpowered stands.
2026-11-23 R8.2 tooltip audit vs INI: Cages renamed + text, Relikt 20%->10% text, Veterans RPG removed from text; rest match.
2026-11-24 R8.7 RUPOWER 684 tris (hall, 2 stacks, filters, 2 transformers, cooler with FAN01-03 1.5 s/turn, 3 s damaged, x2 Overcharge), _E hall caved, stack down, 1 fan; turned 180 so stacks stand behind in the usual view; pad 5 deep. Windowed shots N/S: textures right after UV fix, fans turn (frames 200/205); 2 headless Russia-China rmg clean, PP built; _D/_E seen only in Blender preview.
