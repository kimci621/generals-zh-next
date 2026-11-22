"""Give Russia (docs/russia) its own skirmish player, SkirmishRussia, built from SkirmishChina.

Without it Russia stood in on China's scripts (BaseSide China) and fielded only what China's teams
name: units on American or general-variant sources (Verba, Tigr-M, Pantsir, Ka-52, Su-34...) were
never trained, and nothing put up the Control Center the late roster waits on.

This copies SkirmishChina's script list and teams to a new player SkirmishRussia, whose side dict
names FactionRussia, so SidesList::prepareForMP_or_Skirmish takes it as the stand-in for a map
without a Russia player. In the copy:
  - teams and the scripts naming them are renamed "China ..." -> "Russia ...";
  - some teams get Russia units by name (TEAM_UNITS); every other China name reaches the Russia
    reskin the usual way (ThingFactory findSideReskin);
  - China's upgrade purchases are switched off and RUSSIA_SCRIPTS buy Russia's, put up the
    Control Center and the Buk-M3 batteries; China's power names point at Russia's powers.
The other players get empty side dicts, so their stand-in lookup is unchanged.

usage: russia.py <in.scb> <out.scb>

The master is the retail file through opening.py H 1 4 5 6, infantry_drop.py, ai_bonus.py,
sell_off.py, then this. Run on a file that already has SkirmishRussia, it rebuilds it.
"""
import copy
import sys

import scbtool

SOURCE, PLAYER, FACTION = "SkirmishChina", "SkirmishRussia", "FactionRussia"
INT, SIDE, COMPARISON, OBJECT_TYPE, SPECIAL_POWER, UPGRADE = 0, 11, 6, 15, 30, 32
GE, LT = 3, 0
ACTIVE = 4

# team -> {China unit in it: Russia unit}; by tier: early teams keep units with no Control Center
TEAM_UNITS = {
    "China Alert Aircraft Combat Zone": {"ChinaTankGattling": "RussiaVehiclePantsir"},
    "China Air Defender 1": {"ChinaInfantryTankHunter": "RussiaInfantryVerba"},
    "China Air Defender 2": {"ChinaTankGattling": "RussiaVehiclePantsir"},
    "China CT - Air 1": {"ChinaInfantryTankHunter": "RussiaInfantryVerba"},
    "China CT - Air 2": {"ChinaTankGattling": "RussiaVehiclePantsir", "ChinaInfantryTankHunter": "RussiaInfantryVerba"},
    "China H 2W Base Guards": {"ChinaTankGattling": "RussiaVehiclePantsir"},
    "China H 1ST Wave Rush": {"ChinaInfantryTankHunter": "RussiaInfantryFPV"},
    "China Alert Invasion Tank": {"ChinaInfantryTankHunter": "RussiaInfantryFPV"},
    "China H 1ST Wave Supply Hunters": {"ChinaTankGattling": "RussiaVehicleTigrM"},
    "China H 2ND Wave Fast Attack": {"ChinaTankGattling": "RussiaVehicleTigrM"},
    "China CT - Tank 1": {"ChinaInfantryTankHunter": "RussiaInfantryKornet"},
    "China CT - Tank 2": {"ChinaInfantryTankHunter": "RussiaInfantryKornet"},
    "China H 3RD Wave Tanks C": {"ChinaTankBattleMaster": "RussiaTankT90M"},
    "China H 4TH Wave Tanks B": {"ChinaTankBattleMaster": "RussiaTankT90M"},
    "China H 5TH Wave Tanks C": {"ChinaTankBattleMaster": "RussiaTankT90M"},
    "China CT - Infantry 2": {"ChinaTankDragon": "RussiaVehicleBMP3"},
    "China H 5TH Wave Tanks B": {"ChinaTankDragon": "RussiaVehicleBMP3"},
    "China H 3RD Wave Air": {"ChinaJetMIG": "RussiaJetSu34"},
    "China H 5W Helix Attackers": {"ChinaVehicleHelix": "RussiaHeliKa52"},
    "China CT - Base Def 1": {"ChinaVehicleInfernoCannon": "RussiaVehicleTOS2"},
    "China H 3W Guard Combat Zone": {"ChinaJetMIG": "RussiaDroneOrlan"},
    "China H 4TH Wave Air B": {"ChinaJetMIG": "RussiaJetSu35"},
    "China H 4W Guard Combat Zone": {"ChinaJetMIG": "RussiaJetSu35"},
    "China H 5W Guard Combat Zone": {"ChinaJetMIG": "RussiaJetSu34"},
    "China H 4TH Wave Artillery B": {"ChinaVehicleNukeLauncher": "RussiaVehicleTornadoG"},
    "China H 5TH Wave Artillery C": {"ChinaVehicleNukeLauncher": "RussiaVehicleTornadoG"},
    "China H 5TH Wave Artillery B": {"ChinaVehicleNukeLauncher": "RussiaVehicleTOS1A"},
    "China H 5TH Wave Lotus": {"ChinaInfantryBlackLotus": "RussiaInfantrySniper"},
}
POWERS = {"SuperweaponNeutronMissile": "SuperweaponRussiaOreshnik", "SuperweaponArtilleryBarrage": "SuperweaponRussiaTornadoS",
          "SuperweaponChinaCarpetBomb": "SuperweaponRussiaFAB", "SuperweaponEMPPulse": "SuperweaponRussiaEWSuppress",
          "SuperweaponClusterMines": "SuperweaponRussiaKinzhal"}
# (upgrade, building that sells it, credits to hold first; 0: the purchase queue saves for it)
UPGRADES = [("Upgrade_RussiaTax", "RussiaCommandCenter", 2500), ("Upgrade_RussiaOilGas", "RussiaControlCenter", 2000),
            ("Upgrade_RussiaThermal", "RussiaControlCenter", 3000), ("Upgrade_RussiaRelikt", "RussiaControlCenter", 3000),
            ("Upgrade_RussiaCages", "RussiaControlCenter", 2000), ("Upgrade_RussiaPantsirMod", "RussiaControlCenter", 2500),
            ("Upgrade_RussiaMobres", "RussiaVoenkomat", 0), ("Upgrade_RussiaGuidedFAB", "RussiaAirfield", 2500)]


def param(kind, value):
    return [kind, value, 0.0, ""] if isinstance(value, int) else [kind, 0, 0.0, value]


def call(kinds, name, *params):
    chunk_name = "Condition" if name in ("PLAYER_HAS_OBJECT_COMPARISON", "PLAYER_HAS_CREDITS") else "ScriptAction"
    return scbtool.Chunk(chunk_name, 4 if chunk_name == "Condition" else 2, [kinds[name], name, list(params)], [])


def has(kinds, obj, comparison, count):
    return call(kinds, "PLAYER_HAS_OBJECT_COMPARISON", param(SIDE, "<This Player>"), param(COMPARISON, comparison),
                param(INT, count), param(OBJECT_TYPE, obj))


def script(name, delay, conditions, actions):
    # fields: name, comment, condition comment, action comment, active, once, easy, normal, hard, subroutine, delay
    orc = scbtool.Chunk("OrCondition", 1, [], conditions)
    return scbtool.Chunk("Script", 2, [name, "", "", "", 1, 0, 0, 1, 1, 0, delay], [orc] + actions)


def russia_scripts(kinds):
    out = [script("Russia Build Control Center", 15,
                  [has(kinds, "RussiaWarFactory", GE, 1), has(kinds, "RussiaControlCenter", LT, 1)],
                  [call(kinds, "SKIRMISH_BUILD_BUILDING", param(OBJECT_TYPE, "RussiaControlCenter"))]),
           script("Russia Build Buk", 30,
                  [has(kinds, "RussiaControlCenter", GE, 1), has(kinds, "RussiaBukM3", LT, 2)],
                  [call(kinds, "SKIRMISH_BUILD_STRUCTURE_FRONT", param(OBJECT_TYPE, "RussiaBukM3"))])]
    for upgrade, building, credits in UPGRADES:
        credit = call(kinds, "PLAYER_HAS_CREDITS", param(INT, credits), param(COMPARISON, 1), param(SIDE, "<This Player>"))
        out.append(script("Russia " + upgrade, 20, [has(kinds, building, GE, 1), credit],
                          [call(kinds, "AI_PLAYER_BUILD_UPGRADE", param(SIDE, "<This Player>"), param(UPGRADE, upgrade))]))
    return scbtool.Chunk("ScriptGroup", 2, ["Russia Additions", 1, 0], out)


def walk(chunk):
    yield chunk
    for child in chunk.children:
        yield from walk(child)


def main():
    source, target = sys.argv[1], sys.argv[2]
    table, chunks = scbtool.load(source)
    players = next(c for c in chunks if c.name == "ScriptsPlayers")
    lists = next(c for c in chunks if c.name == "PlayerScriptsList")
    teams = next(c for c in chunks if c.name == "ScriptTeams")
    names = [p for p, _ in players.fields[1]]
    if PLAYER in names:  # rebuild: drop the old copy first
        i = names.index(PLAYER)
        del players.fields[1][i], lists.children[i], names[i]
        teams.fields = [t for t in teams.fields if dict((k, v) for k, _, v in t).get("teamOwner") != PLAYER]
    assert len(names) == len(lists.children), (len(names), len(lists.children))
    china = lists.children[names.index(SOURCE)]

    kinds = {}
    for c in walk(lists):
        if c.name in ("Condition", "ScriptAction"):
            kinds.setdefault(c.fields[1], c.fields[0])

    rename = {}
    new_teams = []
    for t in teams.fields:
        d = {k: v for k, _, v in t}
        if d.get("teamOwner") != SOURCE:
            continue
        old = d["teamName"]
        new = "team" + PLAYER if old == "team" + SOURCE else "Russia" + old[len("China"):] if old.startswith("China") else "Russia " + old
        rename[old] = new
        units = TEAM_UNITS.get(old, {})
        nt = []
        for k, kind, v in t:
            if k == "teamName":
                v = new
            elif k == "teamOwner":
                v = PLAYER
            elif k.startswith("teamUnitType") and v in units:
                v = units.pop(v)
            nt.append([k, kind, v])
        assert not units, (old, units)
        new_teams.append(nt)
    assert len(new_teams) == 116, len(new_teams)
    missing = set(TEAM_UNITS) - set(rename)
    assert not missing, missing

    russia = copy.deepcopy(china)
    off = 0
    for c in walk(russia):
        if c.name == "Script" and any(a.name == "ScriptAction" and a.fields[1] == "AI_PLAYER_BUILD_UPGRADE" and
                                      any(p[3].startswith(("Upgrade_China", "Upgrade_Nationalism")) for p in a.fields[2])
                                      for a in c.children):
            c.fields[ACTIVE] = 0
            off += 1
        if c.name in ("Condition", "ScriptAction", "ScriptActionFalse"):
            for p in c.fields[2]:
                if p[0] == 3 and p[3] in rename:  # TEAM
                    p[3] = rename[p[3]]
                elif p[0] == SPECIAL_POWER and p[3] in POWERS:
                    p[3] = POWERS[p[3]]
    assert off == 11, off
    russia.children.append(russia_scripts(kinds))

    players.fields[0] = 1
    for entry in players.fields[1]:
        entry[1] = entry[1] or []
    players.fields[1].append([PLAYER, [["playerName", scbtool.DICT_ASCII, PLAYER],
                                       ["playerFaction", scbtool.DICT_ASCII, FACTION],
                                       ["playerIsHuman", scbtool.DICT_BOOL, 0]]])
    lists.children.append(russia)
    teams.fields += new_teams
    scbtool.save(target, table, chunks)
    print(f"{PLAYER}: {len(new_teams)} teams, {len(TEAM_UNITS)} with Russia units, {off} China upgrades off")


if __name__ == "__main__":
    main()
