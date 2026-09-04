#!/usr/bin/env python3
"""Extract first-pass ionospheric and ring-current response diagnostics."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import h5py
import numpy as np

KEV_TO_J = 1.602176634e-16


def steps(handle: h5py.File):
    groups = [handle[name] for name in handle if name.startswith("Step#")]
    return sorted(groups, key=lambda group: float(group.attrs["time"]))


def cell_areas(group: h5py.Group, hemisphere: str, radius: float) -> np.ndarray:
    # ReMIX calls this latitude, but its range is polar colatitude. Rows are
    # latitudinal cell boundaries; longitude has 360 equal-width cells.
    theta_edges = np.mean(group[f"Latitude (Apex) {hemisphere}"][...], axis=1)
    bands = radius * radius * np.abs(np.cos(theta_edges[:-1]) - np.cos(theta_edges[1:]))
    return np.repeat((bands * (2.0 * np.pi / 360.0))[:, None], 360, axis=1)


def auroral_power(group: h5py.Group, hemisphere: str, area: np.ndarray) -> float:
    number = group[f"MHD number flux {hemisphere}"][...]
    energy = group[f"MHD average energy {hemisphere}"][...]
    mhd_wm2 = number * energy * 1.0e4 * KEV_TO_J
    # Inner-magnetosphere energy flux is supplied directly in erg cm^-2 s^-1.
    im_wm2 = group[f"IM Energy flux {hemisphere}"][...] * 1.0e-3
    return float(np.nansum((mhd_wm2 + im_wm2) * area))


def nearest_volt_attrs(groups: list[h5py.Group], time: float) -> dict:
    group = min(groups, key=lambda item: abs(float(item.attrs["time"]) - time))
    if abs(float(group.attrs["time"]) - time) > 2.6:
        return {}
    return group.attrs


def process_case(case: Path, runid: str) -> list[dict]:
    mix_path = case / f"{runid}.mix.h5"
    volt_path = case / f"{runid}.volt.h5"
    if not mix_path.is_file() or not volt_path.is_file():
        raise FileNotFoundError(f"missing {mix_path.name} or {volt_path.name} in {case}")
    rows = []
    db_path = case / f"{runid}.deltab.h5"
    db = h5py.File(db_path) if db_path.is_file() else None
    with h5py.File(mix_path) as mix, h5py.File(volt_path) as volt:
        mix_steps = steps(mix)
        volt_steps = steps(volt)
        radius = float(mix.attrs["Ri_m"])
        for group in mix_steps:
            time = float(group.attrs["time"])
            row = {
                "case": runid,
                "time_s": time,
                "mjd": float(group.attrs["MJD"]),
                "cpcp_n_kV": float(group.attrs["nCPCP"]),
                "cpcp_s_kV": float(group.attrs["sCPCP"]),
            }
            for hemi, short in (("NORTH", "n"), ("SOUTH", "s")):
                area = cell_areas(group, hemi, radius)
                fac = group[f"Field-aligned current {hemi}"][...] * 1.0e-6
                row[f"fac_{short}_peak_abs_uA_m2"] = float(np.nanmax(np.abs(fac))) * 1.0e6
                row[f"fac_{short}_positive_MA"] = float(np.nansum(np.maximum(fac, 0.0) * area)) / 1.0e6
                row[f"fac_{short}_negative_MA"] = float(np.nansum(np.minimum(fac, 0.0) * area)) / 1.0e6
                row[f"auroral_power_{short}_GW"] = auroral_power(group, hemi, area) / 1.0e9
            attrs = nearest_volt_attrs(volt_steps, time)
            for source, target in (
                ("DPSDst", "dps_dst_nT"),
                ("BSDst", "biot_savart_dst_nT"),
                ("BSSMR00", "smr00_nT"),
                ("BSSMR06", "smr06_nT"),
                ("BSSMR12", "smr12_nT"),
                ("BSSMR18", "smr18_nT"),
            ):
                row[target] = float(attrs[source]) if source in attrs else float("nan")
            db_attrs = nearest_volt_attrs(steps(db), time) if db is not None else {}
            for source, target in (("SML", "sml_nT"), ("SMU", "smu_nT"), ("SME", "sme_nT"), ("SMR", "smr_nT")):
                row[target] = float(db_attrs[source]) if source in db_attrs else float("nan")
            rows.append(row)
    if db is not None:
        db.close()
    return rows


def summarize(rows: list[dict], pulse_duration: int) -> dict:
    post = [row for row in rows if row["time_s"] >= 0]
    baseline = min(rows, key=lambda row: abs(row["time_s"]))
    summary = {"case": rows[0]["case"], "pulse_duration_s": pulse_duration}
    for key in ("cpcp_n_kV", "cpcp_s_kV", "fac_n_peak_abs_uA_m2", "fac_s_peak_abs_uA_m2", "auroral_power_n_GW", "auroral_power_s_GW"):
        values = np.asarray([row[key] for row in post])
        peak_index = int(np.nanargmax(values))
        summary[f"peak_{key}"] = float(values[peak_index])
        summary[f"peak_time_{key}_s"] = float(post[peak_index]["time_s"])
        summary[f"delta_peak_{key}"] = float(values[peak_index] - baseline[key])
    for key in ("dps_dst_nT", "biot_savart_dst_nT", "sml_nT", "smr_nT"):
        values = np.asarray([row[key] for row in post])
        if np.isfinite(values).any():
            index = int(np.nanargmin(values))
            summary[f"minimum_{key}"] = float(values[index])
            summary[f"minimum_time_{key}_s"] = float(post[index]["time_s"])
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/nfs/urdr/scratch/juha/gamera/tail-loading-pulses"))
    args = parser.parse_args()
    manifest = json.loads((args.root / "manifest.json").read_text(encoding="utf-8"))
    analysis = args.root / "analysis"
    analysis.mkdir(exist_ok=True)
    summaries = []
    for item in manifest["cases"]:
        runid = item["case"]
        case = args.root / "cases" / runid
        if not (case / "COMPLETED").is_file():
            continue
        rows = process_case(case, runid)
        with (analysis / f"{runid}.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        summaries.append(summarize(rows, int(item["pulse_duration_s"])))
    (analysis / "response-summary.json").write_text(json.dumps(summaries, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Analyzed {len(summaries)} completed cases into {analysis}")


if __name__ == "__main__":
    main()
