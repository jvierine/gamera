#!/usr/bin/env python3
"""Render requested GAMERA density and REMIX electrodynamics frame sets."""

from __future__ import annotations

import argparse
from multiprocessing import Pool
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
from astropy.time import Time

from kaipy.gamera.magsphere import GamsphPipe
from kaipy.remix.remix import remix


BOUNDS = [-40.0, 20.0, -30.0, 30.0]
_GSPH = None
_DENSITY_DIR = None


def init_density(directory: str, runid: str, output: str) -> None:
    """Initialize one process-local GAMERA reader."""
    global _GSPH, _DENSITY_DIR
    _GSPH = GamsphPipe(directory, runid, doFast=False)
    _DENSITY_DIR = Path(output)


def render_density(step: int) -> str:
    """Render density in SM XY/XZ and magnetic topology in the XZ plane."""
    gsph = _GSPH
    output = _DENSITY_DIR / f"density-planes.{step:04d}.png"
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.4), constrained_layout=True)
    mesh = None

    for ax, do_eq, label in (
        (axes[0], True, "SM equatorial plane (X-Y)"),
        (axes[1], False, "SM noon-midnight plane (X-Z)"),
    ):
        density = gsph.EggSlice("D", step, doEq=do_eq, doVerb=False)
        mesh = ax.pcolormesh(
            gsph.xxi,
            gsph.yyi,
            np.clip(density, 0.05, None),
            shading="auto",
            cmap="viridis",
            norm=LogNorm(vmin=0.05, vmax=50.0),
        )

        if do_eq:
            bz = gsph.bScl * gsph.EggSlice("Bz", step, doEq=True, doVerb=False)
            ax.contour(gsph.xxc, gsph.yyc, bz, levels=[0.0], colors="magenta", linewidths=0.8)
            ax.text(0.02, 0.02, "magenta: Bz = 0", color="magenta", transform=ax.transAxes)
        else:
            bx = gsph.bScl * gsph.EggSlice("Bx", step, doEq=False, doVerb=False)
            bz = gsph.bScl * gsph.EggSlice("Bz", step, doEq=False, doVerb=False)
            x, y, u, v, magnitude = gsph.doStream(bx, bz, BOUNDS, dx=0.4)
            valid = np.isfinite(magnitude) & (magnitude > 0.0)
            u = np.where(valid, u, 0.0)
            v = np.where(valid, v, 0.0)
            ax.streamplot(
                x,
                y,
                u,
                v,
                color="white",
                density=0.75,
                linewidth=0.55,
                arrowsize=0.55,
            )
        earth = plt.Circle((0.0, 0.0), 1.0, facecolor="white", edgecolor="black", zorder=10)
        ax.add_patch(earth)
        ax.set(xlim=BOUNDS[:2], ylim=BOUNDS[2:], xlabel="SM-X [Re]", title=label)
        ax.set_ylabel("SM-Y [Re]" if do_eq else "SM-Z [Re]")
        ax.set_aspect("equal")

    fig.colorbar(mesh, ax=axes, label="Plasma density [#/cc]", shrink=0.82)
    gsph.AddTime(step, axes[0], xy=[0.025, 0.90], fs="large")
    fig.suptitle("GAMERA plasma density with meridional magnetic-field lines")
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return str(output)


def render_ionosphere(task: tuple[str, int, Path]) -> tuple[str, str, str]:
    """Render north potential and north/south FAC with potential contours."""
    mix_file, step, output_root = task
    with h5py.File(mix_file, "r") as handle:
        mjd = float(handle[f"Step#{step}"].attrs["MJD"])
    timestamp = Time(mjd, format="mjd").iso

    products = []
    for hemisphere in ("NORTH", "SOUTH"):
        ion = remix(mix_file, step)
        ion.init_vars(hemisphere)
        potential = ion.variables["potential"]["data"]
        cpcp = float(np.nanmax(potential) - np.nanmin(potential))

        if hemisphere == "NORTH":
            fig = plt.figure(figsize=(8.4, 7.4))
            ion.plot("potential")
            fig.suptitle(
                f"Northern ionospheric convection potential | CPCP = {cpcp:.1f} kV\n"
                f"{timestamp} UTC"
            )
            path = output_root / "north-convection" / f"north-convection.{step:04d}.png"
            fig.savefig(path, dpi=160)
            plt.close(fig)
            products.append(str(path))

        fig = plt.figure(figsize=(8.4, 7.4))
        ion.plot("current")
        fig.suptitle(
            f"{hemisphere.title()} FAC with convection-potential contours | "
            f"CPCP = {cpcp:.1f} kV\n{timestamp} UTC"
        )
        slug = f"fac-{hemisphere.lower()}"
        path = output_root / slug / f"{slug}.{step:04d}.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        products.append(str(path))

    return tuple(products)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--runid", default="hello_earth_hour")
    parser.add_argument("--ncpus", type=int, default=16)
    return parser.parse_args()


def main() -> None:
    global _GSPH, _DENSITY_DIR
    args = parse_args()
    output_root = args.directory / "requested-frames"
    for name in ("density-planes", "north-convection", "fac-north", "fac-south"):
        (output_root / name).mkdir(parents=True, exist_ok=True)

    probe = GamsphPipe(str(args.directory), args.runid, doFast=False)
    density_steps = list(range(probe.s0, probe.sFin + 1))
    with Pool(
        processes=args.ncpus,
        initializer=init_density,
        initargs=(str(args.directory), args.runid, str(output_root / "density-planes")),
    ) as pool:
        for path in pool.imap_unordered(render_density, density_steps):
            print(path, flush=True)

    mix_file = args.directory / f"{args.runid}.mix.h5"
    with h5py.File(mix_file, "r") as handle:
        mix_steps = sorted(
            int(name.removeprefix("Step#"))
            for name in handle.keys()
            if name.startswith("Step#")
        )
    tasks = [(str(mix_file), step, output_root) for step in mix_steps]
    with Pool(processes=args.ncpus) as pool:
        for paths in pool.imap_unordered(render_ionosphere, tasks):
            print("\n".join(paths), flush=True)


if __name__ == "__main__":
    main()
