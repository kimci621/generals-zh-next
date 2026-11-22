#!/usr/bin/env python3
"""Доля матчей, где бот России использовал каждую уникальную вещь (цель R4.9: >=50%).

  python3 Tools/Russia/usage.py <папка логов от series.py --keeplogs>

Юнит/здание = HEADLESS HISTORY BUILD, апгрейд = AI UPGRADE queues / AI QUEUE buys (покупки скриптов), сила = AI POWER fires.
"""
import glob, os, re, sys

# что игрок строит/покупает сам; служебные объекты (импульсы, маркеры, боеголовки, резервисты) не считаем
UNITS = ("Airfield Barracks BukM3 CommandCenter ControlCenter Oreshnik PantsirPos PowerPlant Strongpoint SupplyCenter "
         "Voenkomat WarFactory Zoopark HeliKa52 HeliMi8 InfantryEngineer InfantryFPV InfantryGRU InfantryKornet "
         "InfantryMotorRifle InfantryRPG InfantrySniper InfantryVerba JetSu25 JetSu34 JetSu35 TankBMPT TankT14 TankT72B3M "
         "TankT90M VehicleBMP3 VehicleBTR82A VehicleIMR3M VehicleKamaz VehicleKrasukha VehicleLancet VehicleMstaS "
         "VehiclePantsir VehicleTigrM VehicleTorM2 VehicleTornadoG VehicleTOS1A VehicleTOS2 DroneOrlan").split()
UPGRADES = "Cages GuidedFAB Mobres OilGas PantsirMod Ratnik Relikt Tax Thermal".split()
POWERS = "Cyber EWSuppress FAB Kinzhal Oreshnik OrlanRecon Reservists TornadoS VDV".split()
ITEMS = ["Russia" + u for u in UNITS] + ["Upgrade_Russia" + u for u in UPGRADES] + ["SuperweaponRussia" + p for p in POWERS]

BUILD = re.compile(r"HEADLESS HISTORY BUILD (\d+) \d+ (\S+)")
UPG = re.compile(r"AI (?:UPGRADE|QUEUE) frame \d+ player (\d+) (?:queues|buys) '(\S+)'")
POW = re.compile(r"AI POWER frame \d+ player (\d+) fires '(\S+)'")


def used(path):
    seen, rus = {}, None
    for line in open(path, errors="replace"):
        for rx in (BUILD, UPG, POW):
            m = rx.search(line)
            if m:
                seen.setdefault(m.group(1), set()).add(m.group(2))
    for pl, s in seen.items():
        if "RussiaCommandCenter" in s:
            rus = s
    rus = rus or set()
    if "RussiaVoenkomatMobres" in rus:  # Mobres = ReplaceObjectUpgrade, the new Voenkomat shows the purchase
        rus.add("Upgrade_RussiaMobres")
    return rus


def main():
    logs = sorted(glob.glob(os.path.join(sys.argv[1], "*.log")))
    if not logs:
        sys.exit("нет логов")
    sets = [used(p) for p in logs]
    low = 0
    for it in ITEMS:
        n = sum(it in s for s in sets)
        mark = "" if 2 * n >= len(sets) else "  <50%"
        low += bool(mark)
        print(f"{n:3d}/{len(sets)} {it}{mark}")
    print(f"ниже 50%: {low} из {len(ITEMS)}")


if __name__ == "__main__":
    main()
