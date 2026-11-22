#!/usr/bin/env python3
"""Серия headless-матчей ИИ против ИИ -> CSV.

Пример:
  python3 Tools/Russia/series.py --seeds 1-6 --maps rmg --pairs FactionRussia:FactionChina \
      --swap --parallel 6 --maxframes 54000 --out $TMPDIR/s.csv

--maps: rmg (случайная карта из seed) или имена карт через запятую ("Tournament Desert").
--swap: каждую пару играть и в обратных слотах.
Победитель: слот со статусом WON из строк HEADLESS PLAYER; по лимиту кадров - "none".
"""
import argparse, csv, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

APP = os.path.expanduser("~/Games/Generals-Reforged/build-mac/Zero Hour Reforged.app/Contents/MacOS/generals")
ROOT = os.path.expanduser("~/Games/Generals/GeneralsZH")
LOGS = os.path.expanduser("~/Library/Application Support/Command and Conquer Generals Zero Hour Data/Logs")
RESULT = re.compile(r"HEADLESS RESULT: (.+?) on frame (\d+) .*?([\d.]+)x real time")
PLAYER = re.compile(r"HEADLESS PLAYER \d+ '.*?': (\w+) \| score (\d+) .*?\| slot (-?\d+)")


def seeds(spec):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += range(int(a), int(b or a) + 1)
    return out


def run(job, maxframes, timeout):
    seed, mp, sides, tag = job
    prefix = f"ser_{tag}_"
    log = os.path.join(LOGS, prefix + "DebugLogFile.txt")
    if os.path.exists(log):
        os.remove(log)
    cmd = [APP, "-root", ROOT, "-headless", "-quickstart", "-noshellmap", "-observer", "-multiInstance"]
    cmd += ["-randommap", str(seed), "2", "0"] if mp == "rmg" else ["-map", f'"Maps\\{mp}\\{mp}.map"']
    cmd += ["-autoskirmish", "2", "-aidiff", "hard", "-seed", str(seed), "-maxframes", str(maxframes), "-logPrefix", prefix]
    for slot, side in enumerate(sides):
        cmd += ["-side", str(slot), side]
    t0 = time.time()
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
        status = "ok"
    except subprocess.TimeoutExpired:
        status = "timeout"
    wall = time.time() - t0
    why, frames, xrt, winner, scores = "noresult", 0, 0.0, "none", {}
    if os.path.exists(log):
        with open(log, errors="replace") as f:
            for line in f:
                m = RESULT.search(line)
                if m:
                    why, frames, xrt = m.group(1), int(m.group(2)), float(m.group(3))
                m = PLAYER.search(line)
                if m:
                    slot = int(m.group(3))
                    scores[slot] = int(m.group(2))
                    if m.group(1) == "WON":
                        winner = sides[slot]
        os.remove(log)
    if status == "ok" and why == "noresult":
        status = "crash"
    return dict(seed=seed, map=mp, side0=sides[0], side1=sides[1], winner=winner, why=why, frames=frames,
                xrt=xrt, wall=round(wall, 1), score0=scores.get(0, ""), score1=scores.get(1, ""), status=status)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="1-3")
    ap.add_argument("--maps", default="rmg")
    ap.add_argument("--pairs", default="FactionRussia:FactionChina")
    ap.add_argument("--swap", action="store_true")
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--maxframes", type=int, default=54000)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    jobs = []
    for pair in a.pairs.split(","):
        x, y = pair.split(":")
        orders = [(x, y), (y, x)] if a.swap else [(x, y)]
        for mp in a.maps.split(","):
            for s in seeds(a.seeds):
                for sides in orders:
                    jobs.append((s, mp, sides, f"{len(jobs)}_{os.getpid()}"))
    t0 = time.time()
    with ThreadPoolExecutor(a.parallel) as ex:
        rows = list(ex.map(lambda j: run(j, a.maxframes, a.timeout), jobs))
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    hours = (time.time() - t0) / 3600
    bad = sum(r["status"] != "ok" for r in rows)
    print(f"{len(rows)} matches, {bad} bad, {len(rows) / hours:.0f} matches/hour -> {a.out}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
