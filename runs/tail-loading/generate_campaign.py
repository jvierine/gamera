#!/usr/bin/env python3
"""Generate synthetic solar-wind inputs and XML decks for the pulse campaign."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET

import h5py
import numpy as np

MP = 1.67262192369e-27
KB = 1.380649e-23
MU0 = 4.0e-7 * math.pi


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        cfg = json.load(stream)
    durations = cfg["pulse_durations_s"]
    if durations != sorted(set(durations)) or any(x <= 0 for x in durations):
        raise ValueError("pulse_durations_s must be unique, positive, and sorted")
    if cfg["cadence_s"]["wind"] > min(durations) / 5:
        raise ValueError("wind cadence must supply at least five samples in the shortest pulse")
    return cfg


def case_id(duration: int) -> str:
    return f"tail_pulse_{duration:05d}s"


def wind_arrays(cfg: dict, duration: int) -> dict[str, np.ndarray | float]:
    sw = cfg["solar_wind"]
    cadence = int(cfg["cadence_s"]["wind"])
    recovery = int(cfg["recovery_s"])
    # One quiet sample before t=0 makes the discontinuity unambiguous to interpolation.
    times = np.arange(-cadence, duration + recovery + 2 * cadence, cadence, dtype=np.float64)
    bz = np.full(times.shape, sw["northward_bz_nT"], dtype=np.float64)
    if duration > 0:
        # Inclusive endpoints give exactly `duration` seconds at full -Bz;
        # adjacent one-second samples define finite one-second ramps.
        bz[(times >= 0) & (times <= duration)] = sw["pulse_bz_nT"]

    epoch = dt.datetime.fromisoformat(cfg["epoch_utc"].replace("Z", "+00:00"))
    mjd0 = epoch.timestamp() / 86400.0 + 40587.0
    uts = np.array(
        [(epoch + dt.timedelta(seconds=float(t))).strftime("%Y-%m-%d %H:%M:%S") for t in times],
        dtype=h5py.string_dtype("utf-8"),
    )
    n = float(sw["density_cm3"])
    temp = float(sw["temperature_K"])
    vx = float(sw["vx_km_s"]) * 1000.0
    vy = float(sw["vy_km_s"]) * 1000.0
    vz = float(sw["vz_km_s"]) * 1000.0
    bx = float(sw["bx_nT"])
    by = float(sw["by_nT"])
    bmag_t = np.sqrt(bx * bx + by * by + bz * bz) * 1.0e-9
    rho = n * 1.0e6 * MP
    cs = math.sqrt((5.0 / 3.0) * KB * temp / MP)
    va = bmag_t / math.sqrt(MU0 * rho)
    vmag = math.sqrt(vx * vx + vy * vy + vz * vz)

    full = lambda value: np.full(times.shape, value, dtype=np.float64)
    return {
        "T": times,
        "UT": uts,
        "MJD": mjd0 + times / 86400.0,
        "D": full(n),
        "Temp": full(temp),
        "Vx": full(vx),
        "Vy": full(vy),
        "Vz": full(vz),
        "Bx": full(bx),
        "By": full(by),
        "Bz": bz,
        "tilt": full(float(sw["dipole_tilt_rad"])),
        "ae": full(0.0),
        "al": full(0.0),
        "au": full(0.0),
        "symh": full(0.0),
        "Kp": full(1.0),
        "f10.7": full(100.0),
        "Interped": np.zeros(times.shape, dtype=np.int64),
        "Va": va,
        "Cs": full(cs),
        "Magnetosonic Mach": vmag / np.sqrt(cs * cs + va * va),
        # Approximate subsolar bow-shock location; wind.F90 treats these as optional.
        "xBS": full(14.5),
        "yBS": full(0.0),
        "zBS": full(0.0),
        "Bx0": 0.0,
        "ByC": 0.0,
        "BzC": 0.0,
    }


def write_wind(path: Path, arrays: dict) -> None:
    with h5py.File(path, "w") as out:
        for name, values in arrays.items():
            out.create_dataset(name, data=values)


def add(parent: ET.Element, name: str, **attrs: object) -> ET.Element:
    return ET.SubElement(parent, name, {key: str(value) for key, value in attrs.items()})


def xml_tree(cfg: dict, runid: str, tfin: float, restart: bool, spinup: bool) -> ET.ElementTree:
    c = cfg["cadence_s"]
    root = ET.Element("Kaiju")
    volt = add(root, "VOLTRON")
    add(volt, "time", tFin=f"{tfin:.2f}")
    add(volt, "spinup", doSpin="T" if spinup else "F", tSpin=f"{cfg['northward_spinup_s']:.1f}", tIO="0.0")
    add(volt, "output", dtOut=f"{c['output']:.1f}", dtCon=f"{c['console']:.1f}")
    add(volt, "coupling", dtCouple=f"{c['coupling']:.1f}", imType="RAIJU", doQkSquish="T", qkSquishStride="2", doAsyncCoupling="F")
    add(volt, "restart", dtRes=f"{c['restart']:.1f}")
    add(volt, "imag", doInit="T")
    add(volt, "ebsquish", epsSquish="0.05")
    add(volt, "threading", NumTh=str(cfg["openmp_threads"]))

    gam = add(root, "Gamera")
    add(gam, "sim", runid=runid, doH5g="T", H5Grid="lfmD.h5", icType="user", pdmb="1.0", rmeth="7UP")
    add(gam, "floors", dFloor="1.0e-4", pFloor="1.0e-6")
    add(gam, "timestep", doCPR="T", limCPR="0.25")
    add(gam, "restart", doRes="T" if restart else "F", resID="tail_baseline", nRes="0")
    add(gam, "physics", doMHD="T", doBoris="T", Ca="10.0")
    add(gam, "ring", gid="lfm", doRing="T")
    add(gam, "ringknobs", doVClean="T")
    add(gam, "wind", tsfile="bcwind.h5")
    add(gam, "source", doSource="T", doWolfLim="T", doBounceDT="T", nBounce="1.0")
    add(gam, "iPdir", N="3", bcPeriodic="F")
    add(gam, "jPdir", N="8", bcPeriodic="F")
    add(gam, "kPdir", N="1", bcPeriodic="T")
    add(gam, "threading", NumTh=str(cfg["openmp_threads"]))
    add(gam, "coupling", blockHalo="T")

    chimp = add(root, "CHIMP")
    add(chimp, "units", uid="EARTHCODE")
    add(chimp, "fields", grType="LFM")
    add(chimp, "domain", dtype="MAGE")
    add(chimp, "tracer", epsds="0.05")
    remix = add(root, "REMIX")
    add(remix, "conductance", doStarlight="T", doRamp="F")
    add(remix, "precipitation", aurora_model_type="LINMRG", alpha="0.2", beta="0.4", doAuroralSmooth="F")
    raiju = add(root, "RAIJU")
    add(raiju, "output", loudConsole="T", doFat="F", doLossExtras="F", doDebug="F", writeGhosts="F")
    add(raiju, "grid", gType="SHGRID", ThetaL="15", ThetaU="50")
    add(raiju, "domain", tail_buffer="15.0", sun_buffer="15.0", tail_active="12.0", sun_active="12.0")
    add(raiju, "sim", pdmb="0.75")
    add(raiju, "config", fname="raijuconfig.h5")
    add(raiju, "plasmasphere", doPsphere="T", doExcessMap="T")
    add(raiju, "losses", doLosses="T", doCX="T", doSS="T", doCC="T")
    add(raiju, "cpl", nFluidsIn="1", startupTscl="7200.0", vaFracThresh="0.60", bminThresh="5.0", Pstd="5.0", normAngThresh="180.0")
    add(raiju, "fluidIn1", imhd="0", flav="2", excessToPsph="T")
    ET.indent(root, space="  ")
    return ET.ElementTree(root)


def calcdb_tree(runid: str, tfin: int, cadence: int) -> ET.ElementTree:
    root = ET.Element("Kaiju")
    chimp = add(root, "Chimp")
    add(chimp, "sim", runid=runid)
    add(chimp, "time", T0="0.0", dt=f"{cadence:.1f}", tFin=f"{tfin:.1f}")
    add(chimp, "fields", ebfile=runid, grType="LFM", doJ="T", isMPI="true")
    add(chimp, "parallel", Ri="3", Rj="8", Rk="1")
    add(chimp, "grid", Nlat="180", Nlon="360", Nz="1")
    ET.indent(root, space="  ")
    return ET.ElementTree(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("campaign.json"))
    parser.add_argument("--root", type=Path, help="override data_root (useful for validation)")
    parser.add_argument("--force", action="store_true", help="replace generated wind/XML files only")
    args = parser.parse_args()
    cfg = load_config(args.config)
    root = args.root or Path(cfg["data_root"])
    root.mkdir(parents=True, exist_ok=True)

    baseline = root / "baseline"
    baseline.mkdir(exist_ok=True)
    base_wind = baseline / "bcwind.h5"
    base_xml = baseline / "tail-baseline.xml"
    for path in (base_wind, base_xml):
        if path.exists() and not args.force:
            raise FileExistsError(f"refusing to overwrite {path}; use --force for generated inputs")
    write_wind(base_wind, wind_arrays(cfg, 0))
    xml_tree(cfg, "tail_baseline", 0.25, restart=False, spinup=True).write(base_xml, encoding="utf-8", xml_declaration=True)

    manifest = []
    if cfg.get("include_unpulsed_control", True):
        cid = "tail_control"
        case = root / "cases" / cid
        case.mkdir(parents=True, exist_ok=True)
        paths = (case / "bcwind.h5", case / f"{cid}.xml", case / f"{cid}-calcdb.xml")
        for path in paths:
            if path.exists() and not args.force:
                raise FileExistsError(f"refusing to overwrite {path}; use --force for generated inputs")
        write_wind(paths[0], wind_arrays(cfg, 0))
        xml_tree(cfg, cid, cfg["recovery_s"] + 0.25, restart=True, spinup=False).write(paths[1], encoding="utf-8", xml_declaration=True)
        calcdb_tree(cid, cfg["recovery_s"], cfg["cadence_s"]["output"]).write(paths[2], encoding="utf-8", xml_declaration=True)
        manifest.append({"case": cid, "pulse_duration_s": 0, "model_duration_s": cfg["recovery_s"], "kind": "control"})
    for duration in cfg["pulse_durations_s"]:
        cid = case_id(duration)
        case = root / "cases" / cid
        case.mkdir(parents=True, exist_ok=True)
        wind = case / "bcwind.h5"
        xml = case / f"{cid}.xml"
        calcdb = case / f"{cid}-calcdb.xml"
        for path in (wind, xml, calcdb):
            if path.exists() and not args.force:
                raise FileExistsError(f"refusing to overwrite {path}; use --force for generated inputs")
        write_wind(wind, wind_arrays(cfg, duration))
        xml_tree(cfg, cid, duration + cfg["recovery_s"] + 0.25, restart=True, spinup=False).write(xml, encoding="utf-8", xml_declaration=True)
        calcdb_tree(cid, duration + cfg["recovery_s"], cfg["cadence_s"]["output"]).write(calcdb, encoding="utf-8", xml_declaration=True)
        manifest.append({"case": cid, "pulse_duration_s": duration, "model_duration_s": duration + cfg["recovery_s"], "kind": "pulse"})
    with (root / "manifest.json").open("w", encoding="utf-8") as stream:
        json.dump({"config": cfg, "cases": manifest}, stream, indent=2)
        stream.write("\n")
    print(f"Generated baseline and {len(manifest)} branches in {root}")


if __name__ == "__main__":
    main()
