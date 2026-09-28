#!/usr/bin/env python3
"""Export a compact GAMERA/REMIX current product for the browser viewer.

The authoritative output is HDF5.  Float32 ``.bin`` files are a browser
transport generated from the same arrays; they are not independent data.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re

import h5py
import numpy as np


RANK_RE = re.compile(
    r"_(?P<ri>\d{4})_(?P<rj>\d{4})_(?P<rk>\d{4})_"
    r"(?P<i>\d{4})_(?P<j>\d{4})_(?P<k>\d{4})\.gam\.h5$"
)


def rank_files(source: Path, runid: str) -> list[tuple[Path, tuple[int, int, int], tuple[int, int, int]]]:
    found = []
    for path in sorted(source.glob(f"{runid}_*.gam.h5")):
        match = RANK_RE.search(path.name)
        if match:
            found.append(
                (
                    path,
                    tuple(int(match.group(key)) for key in ("ri", "rj", "rk")),
                    tuple(int(match.group(key)) for key in ("i", "j", "k")),
                )
            )
    if not found:
        raise FileNotFoundError(f"no MPI GAMERA files for {runid!r} in {source}")
    decompositions = {item[1] for item in found}
    if len(decompositions) != 1 or len(found) != np.prod(found[0][1]):
        raise ValueError(f"incomplete/inconsistent MPI decomposition: {decompositions}, {len(found)} files")
    return found


def cell_centres(corners: np.ndarray) -> np.ndarray:
    return sum(
        corners[a : corners.shape[0] - 1 + a, b : corners.shape[1] - 1 + b, c : corners.shape[2] - 1 + c]
        for a in (0, 1)
        for b in (0, 1)
        for c in (0, 1)
    ) / 8.0


def load_grid(files):
    with h5py.File(files[0][0], "r") as handle:
        local = tuple(np.asarray(handle[name]).shape[d] - 1 for d, name in enumerate(("X", "Y", "Z")))
    ranks = files[0][1]
    shape = tuple(local[d] * ranks[d] + 1 for d in range(3))
    xyz = [np.zeros(shape, dtype=np.float32) for _ in range(3)]
    for path, _, location in files:
        slices = tuple(slice(location[d] * local[d], (location[d] + 1) * local[d] + 1) for d in range(3))
        with h5py.File(path, "r") as handle:
            for target, name in zip(xyz, ("X", "Y", "Z")):
                target[slices] = handle[name][...]
    centres = np.stack([cell_centres(item) for item in xyz], axis=-1)
    return centres, local, ranks


def available_times(path: Path):
    with h5py.File(path, "r") as handle:
        rows = []
        for name in handle:
            if name.startswith("Step#"):
                group = handle[name]
                rows.append((int(name[5:]), float(group.attrs["time"]), float(group.attrs["MJD"])))
    return sorted(rows, key=lambda row: row[1])


def choose_steps(rows, cadence: float):
    usable = [row for row in rows if row[1] >= 0]
    targets = np.arange(0.0, usable[-1][1] + cadence / 2, cadence)
    chosen = []
    for target in targets:
        row = min(usable, key=lambda candidate: abs(candidate[1] - target))
        if not chosen or row[0] != chosen[-1][0]:
            chosen.append(row)
    if chosen[-1][0] != usable[-1][0]:
        chosen.append(usable[-1])
    return chosen


def stitch(files, local, ranks, step: int, variables: tuple[str, ...]):
    shape = tuple(local[d] * ranks[d] for d in range(3))
    result = {name: np.zeros(shape, dtype=np.float32) for name in variables}
    for path, _, location in files:
        slices = tuple(slice(location[d] * local[d], (location[d] + 1) * local[d]) for d in range(3))
        with h5py.File(path, "r") as handle:
            group = handle[f"Step#{step}"]
            for name in variables:
                result[name][slices] = group[name][...]
    return result


def mjd_iso(mjd: float) -> str:
    epoch = datetime(1858, 11, 17, tzinfo=timezone.utc)
    return (epoch + timedelta(days=mjd)).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_float32(path: Path, data: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.asarray(data, dtype="<f4").tofile(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--runid", default="hello_earth_24h")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cadence", type=float, default=900.0, help="browser-frame cadence in seconds")
    parser.add_argument("--stride", default="3,2,2", help="GAMERA i,j,k sampling strides")
    parser.add_argument("--fac-stride", default="2,4", help="REMIX colatitude,longitude sampling strides")
    args = parser.parse_args()

    strides = tuple(int(value) for value in args.stride.split(","))
    fac_strides = tuple(int(value) for value in args.fac_stride.split(","))
    if len(strides) != 3 or len(fac_strides) != 2:
        raise ValueError("stride must have 3 values and fac-stride 2 values")

    files = rank_files(args.source, args.runid)
    centres, local, ranks = load_grid(files)
    rows = available_times(files[0][0])
    selected = choose_steps(rows, args.cadence)

    ii, jj, kk = np.meshgrid(
        np.arange(0, centres.shape[0], strides[0]),
        np.arange(0, centres.shape[1], strides[1]),
        np.arange(0, centres.shape[2], strides[2]),
        indexing="ij",
    )
    sample_index = (ii.ravel(), jj.ravel(), kk.ravel())
    positions = centres[sample_index]
    radius = np.linalg.norm(positions, axis=1)
    keep = (
        (positions[:, 0] >= -42)
        & (positions[:, 0] <= 18)
        & (np.abs(positions[:, 1]) <= 28)
        & (np.abs(positions[:, 2]) <= 28)
        & (radius >= 2.2)
    )
    sample_index = tuple(axis[keep] for axis in sample_index)
    positions = positions[keep].astype(np.float32)

    mix_path = args.source / f"{args.runid}.mix.h5"
    with h5py.File(mix_path, "r") as mix:
        probe = mix[f"Step#{selected[0][0]}"]
        # Apex arrays contain radial grid edges and cell-longitude centers.
        lat_n = probe["Latitude (Apex) NORTH"][...]
        lon_n = probe["Longitude (Apex) NORTH"][...]
        lat_s = probe["Latitude (Apex) SOUTH"][...]
        lon_s = probe["Longitude (Apex) SOUTH"][...]
        lat_n = 0.5 * (lat_n[:-1] + lat_n[1:])
        lon_n = 0.5 * (lon_n[:-1] + lon_n[1:])
        lat_s = 0.5 * (lat_s[:-1] + lat_s[1:])
        lon_s = 0.5 * (lon_s[:-1] + lon_s[1:])
        fs0, fs1 = fac_strides
        fac_slice = (slice(None, None, fs0), slice(None, None, fs1))
        fac_positions = []
        # ReMIX calls this coordinate "Latitude", but it is polar
        # colatitude (0 at the magnetic pole).  Map it explicitly rather than
        # treating it as ordinary geographic latitude.
        for hemisphere, (lat, lon) in zip((1.0, -1.0), ((lat_n[fac_slice], lon_n[fac_slice]), (lat_s[fac_slice], lon_s[fac_slice]))):
            fac_positions.append(
                1.055
                * np.stack(
                    [np.sin(lat) * np.cos(lon), np.sin(lat) * np.sin(lon), hemisphere * np.cos(lat)], axis=-1
                ).reshape(-1, 3)
            )
        fac_positions = np.concatenate(fac_positions).astype(np.float32)

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "frames").mkdir(exist_ok=True)
    write_float32(args.output / "positions.bin", positions)
    write_float32(args.output / "fac-positions.bin", fac_positions)

    h5_path = args.output / "gcurrents.h5"
    manifest_frames = []
    all_current = []
    all_fac = []
    with h5py.File(mix_path, "r") as mix:
        for iframe, (step, model_time, mjd) in enumerate(selected):
            values = stitch(files, local, ranks, step, ("Jx", "Jy", "Jz"))
            current = np.stack([values[name][sample_index] for name in ("Jx", "Jy", "Jz")], axis=-1)
            group = mix[f"Step#{step}"]
            # Kaipy's common convention is positive current away from Earth.
            north = -group["Field-aligned current NORTH"][...][fac_slice].ravel()
            south = group["Field-aligned current SOUTH"][...][fac_slice].ravel()
            fac = np.concatenate([north, south]).astype(np.float32)
            current = current.astype(np.float32)
            all_current.append(current)
            all_fac.append(fac)
            current_file = f"frames/current-{iframe:04d}.bin"
            fac_file = f"frames/fac-{iframe:04d}.bin"
            write_float32(args.output / current_file, current)
            write_float32(args.output / fac_file, fac)
            magnitude = np.linalg.norm(current, axis=1)
            manifest_frames.append(
                {
                    "step": step,
                    "model_time_s": round(model_time, 3),
                    "utc": mjd_iso(mjd),
                    "current": current_file,
                    "fac": fac_file,
                    "current_p99_nA_m2": round(float(np.nanpercentile(magnitude, 99)), 5),
                    "fac_abs_p99_uA_m2": round(float(np.nanpercentile(np.abs(fac), 99)), 5),
                    "north_cpcp_kV": round(float(group.attrs["nCPCP"]), 3),
                    "south_cpcp_kV": round(float(group.attrs["sCPCP"]), 3),
                }
            )

    all_current = np.stack(all_current)
    all_fac = np.stack(all_fac)
    with h5py.File(h5_path, "w") as product:
        product.attrs.update(
            {
                "source_run": args.runid,
                "source_host": "avaruus.uit.no",
                "source_directory": str(args.source),
                "coordinates": "GAMERA SM Cartesian; REMIX Apex ionosphere",
                "generator": "export_gcurrents.py",
                "gamera_revision": "3382b1f2",
                "browser_cadence_s": args.cadence,
                "note": "OMNI plasma gap 2016-08-09 09:44--12:02 UTC and IMF gap 09:46--11:59 UTC were linearly interpolated by Kaipy.",
            }
        )
        product.create_dataset("positions", data=positions, compression="gzip").attrs["units"] = "Earth radii"
        product.create_dataset("current_density", data=all_current, compression="gzip").attrs["units"] = "nA/m^2"
        product.create_dataset("fac_positions", data=fac_positions, compression="gzip").attrs["units"] = "Earth radii"
        product.create_dataset("field_aligned_current", data=all_fac, compression="gzip").attrs["units"] = "uA/m^2; positive outward"
        product.create_dataset("step", data=np.asarray([row[0] for row in selected], dtype=np.int32))
        product.create_dataset("model_time", data=np.asarray([row[1] for row in selected])).attrs["units"] = "s"
        product.create_dataset("mjd", data=np.asarray([row[2] for row in selected])).attrs["units"] = "UTC MJD"

    manifest = {
        "title": "GAMERA + REMIX magnetosphere-ionosphere currents",
        "run": args.runid,
        "coordinates": "SM Cartesian, Earth radii",
        "current_units": "nA/m^2",
        "fac_units": "uA/m^2",
        "fac_sign": "positive outward from the ionosphere",
        "positions": "positions.bin",
        "fac_positions": "fac-positions.bin",
        "position_count": len(positions),
        "fac_position_count": len(fac_positions),
        "hemisphere_fac_count": len(fac_positions) // 2,
        "frame_count": len(manifest_frames),
        "source_revision": "JHUAPL/kaiju 3382b1f2",
        "source_product": "gcurrents.h5",
        "caveat": "OMNI plasma gap 2016-08-09 09:44–12:02 UTC and IMF gap 09:46–11:59 UTC were linearly interpolated by Kaipy.",
        "frames": manifest_frames,
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")) + "\n")
    print(f"wrote {len(manifest_frames)} frames, {len(positions)} MHD vectors, {len(fac_positions)} FAC samples")
    print(h5_path)


if __name__ == "__main__":
    main()
