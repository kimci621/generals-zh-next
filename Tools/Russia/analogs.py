#!/usr/bin/env python3
"""Статы аналогов (src из docs/russia/AGENT_PLAN.md DATA) -> TSV.

Ванильные INI из INIZH.big (распаковать bigx.py в <vanilla>), поверх - правки Reforged
(BalanceReforged.ini, FixesReforged.ini; блоки Object/Weapon/Locomotor с тем же именем
перекрывают поля). Берётся первое значение поля в блоке: первый ArmorSet, первый WeaponSet.

  python3 Tools/Russia/analogs.py <vanilla_dir> > $TMPDIR/analogs.tsv
"""
import glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "../../GeneralsMD/Code/Data/INI")
SRC = """ChinaCommandCenter ChinaPowerPlant ChinaBarracks ChinaSupplyCenter ChinaWarFactory ChinaAirfield
ChinaPropagandaCenter AmericaStrategyCenter ChinaBunker ChinaGattlingCannon AmericaPatriotBattery
ChinaSpeakerTower ChinaNuclearMissileLauncher AmericaInfantryRanger ChinaInfantryTankHunter
AmericaInfantryMissileDefender AmericaInfantryPathfinder ChinaInfantryHacker ChinaInfantryBlackLotus
ChinaInfantryRedguard ChinaVehicleDozer ChinaVehicleSupplyTruck AmericaVehicleHumvee
ChinaVehicleTroopCrawler AmericaTankCrusader ChinaTankBattleMaster ChinaTankOverlord ChinaTankGattling
AmericaTankAvenger ChinaVehicleInfernoCannon ChinaVehicleNukeLauncher AmericaVehicleTomahawk ChinaTankECM
ChinaVehicleListeningOutpost ChinaJetMIG AmericaVehicleComanche AmericaVehicleChinook AmericaJetRaptor
AmericaJetAurora""".split()
FIELDS = ["BuildCost", "BuildTime", "MaxHealth", "VisionRange", "ShroudClearingRange", "Armor", "Locomotor", "Weapon"]


def blocks(path, kind):
    """{name: [lines]} для блоков '<kind> name' ... 'End' в колонке 0."""
    out, cur, name = {}, None, None
    for raw in open(path, encoding="latin-1"):
        line = raw.split(";")[0].rstrip()
        m = re.match(rf"^{kind}\s+(\S+)", line)
        if m:
            name, cur = m.group(1), []
            continue
        if cur is not None:
            if re.match(r"^End\b", line, re.I):
                out.setdefault(name, []).extend(cur)
                cur = None
            else:
                cur.append(line.strip())
    return out


def first(lines, key):
    for l in lines:
        m = re.match(rf"{key}\s*=\s*(.+)", l, re.I)
        if m:
            return m.group(1).split()
    return None


def load(kind, vanilla_files):
    merged = {}
    files = vanilla_files + [os.path.join(DATA, f) for f in ("BalanceReforged.ini", "FixesReforged.ini")]
    for f in files:
        for n, ls in blocks(f, kind).items():
            merged[n] = ls + merged.get(n, []) if f.startswith(DATA) else merged.get(n, []) + ls
    return merged


def main():
    v = os.path.join(sys.argv[1], "Data/INI")
    objs = load("Object", glob.glob(os.path.join(v, "Object/*.ini")))
    weps = load("Weapon", [os.path.join(v, "Weapon.ini")])
    locs = load("Locomotor", [os.path.join(v, "Locomotor.ini")])
    print("\t".join(["src", "cost", "time", "hp", "vision", "armor", "speed", "weapon", "dmg", "radius", "range", "delay_ms", "clip", "reload_ms"]))
    for s in SRC:
        o = objs.get(s)
        if not o:
            print(s + "\tMISSING")
            continue
        g = lambda k, i=0: (first(o, k) or ["-"])[i]
        armor = g("Armor")
        loco = first(o, "Locomotor")
        speed = (first(locs.get(loco[1], []), "Speed") or ["-"])[0] if loco and len(loco) > 1 else "-"
        wl = first(o, "Weapon")
        wname = wl[1] if wl and len(wl) > 1 and wl[0].upper() == "PRIMARY" else "-"
        w = weps.get(wname, [])
        wf = lambda k: (first(w, k) or ["-"])[0]
        print("\t".join([s, g("BuildCost"), g("BuildTime"), g("MaxHealth"), g("VisionRange"), armor, speed, wname,
                         wf("PrimaryDamage"), wf("PrimaryDamageRadius"), wf("AttackRange"), wf("DelayBetweenShots"),
                         wf("ClipSize"), wf("ClipReloadTime")]))


if __name__ == "__main__":
    main()
