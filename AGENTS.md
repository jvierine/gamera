# GAMERA/MAGE on `avaruus`

This is the JHU/APL Kaiju repository installed for user `j` on
`avaruus.uit.no`. GAMERA is the global MHD solver inside MAGE.

## Installation record

- Host: `avaruus`, Ubuntu 26.04.1 LTS, x86-64, 256 logical CPUs, about
  1.1 TiB RAM.
- Upstream: <https://github.com/JHUAPL/kaiju>
- Branch/revision: `master` at
  `3382b1f2fd39419e5a43d4c7bc5427029d48291a` (MAGE 1.25 development line).
- `master` was selected because MAGE 1.0 does not compile cleanly with the
  host's GNU Fortran 15 and uses third-party RCM material. Current master has
  the upstream compiler fix and open RAIJU replacement. Upstream labels master
  bleeding edge, so revalidate before scientific use.
- Serial executable: `build_serial/bin/voltron.x`.
- Hybrid executable: `build_mpi/bin/voltron_mpi.x`.
- Toolchain: GNU Fortran 15.2, OpenMP, Ubuntu OpenMPI 5.0.10, serial HDF5
  1.14.6. MPI ranks write separate HDF5 outputs, so parallel HDF5 is not used.
- Python environment: `.venv`.
- Kaipy source: `~/src/kaipy`, revision
  `0028c69c52a91ff378a5798708daaba4cdfb5790` (version 1.1.4).
- The initial MAGE 1.0 attempt is preserved at
  `~/src/gamera-mage1-attempt-20260904`.
- Build and preprocessing logs are in `logs/`.

## Kaipy compatibility patch

NumPy 2 rejects Kaipy's implicit assignment of one-element arrays into scalar
OMNI data slots. The patch
`patches/kaipy-numpy2-scalar-conversion.patch` explicitly extracts those nine
scalar values with `np.asarray(...).item()`. Apply it and create the project
Python environment with:

```bash
cd ~/src/gamera
./setup-kaipy-avaruus.sh
```

This is needed to regenerate `bcwind.h5` with Python 3.14/NumPy 2.5 and does
not alter the coordinate transformation itself.

## Environment and builds

For interactive use:

```bash
source ~/src/gamera/scripts/setupEnvironment.sh
source ~/src/gamera/.venv/bin/activate
export PATH="$KAIJUHOME/build_mpi/bin:$KAIJUHOME/build_serial/bin:$PATH"
export OMP_STACKSIZE=128M
```

Rebuild both variants, with at most 50 compiler jobs:

```bash
cd ~/src/gamera
./build-avaruus.sh
```

The helper uses the necessary Ubuntu HDF5 module include path and builds only
the relevant `voltron.x` targets. Do not omit that include path.

## Hello Earth example

The self-contained example is `runs/hello-earth/`:

- `lfmD.h5`: Kaipy Double-resolution global magnetosphere grid; inner edge
  2 Earth radii, dayside edge about 28 Earth radii, tail about 301 Earth radii.
- `bcwind.h5`: observed one-minute OMNI solar wind for 2016-08-09 09:00-11:00
  UTC, fetched from NASA CDAWeb and transformed to GAMERA format by Kaipy.
- `raijuconfig.h5`: RAIJU species, energy channels, and wave-loss data.
- `hello-earth-smoke.xml`: 11.5 seconds of model time for integration testing.
- `hello-earth-hour.xml`: one hour of model time with 60-second output cadence
  for a density animation.

The model advances ideal MHD with GAMERA, drives its outer boundary with the
solar wind, couples to REMIX ionospheric electrodynamics, and uses RAIJU for
the inner magnetosphere. GAMERA solves conservative mass, momentum, total
energy, and induction equations with `div(B)=0`, using finite volumes and
constrained transport.

Run and verify the smoke case:

```bash
cd ~/src/gamera/runs/hello-earth
./run-smoke.sh
```

Start the longer case only when intended:

```bash
./start-hour.sh
```

The smoke script uses 9 MPI ranks times 4 OpenMP threads (36 CPU threads): one
VOLTRON coordinator plus 8 GAMERA ranks in a 2 x 4 x 1 decomposition. The hour
script uses 25 ranks times 5 threads (125 CPU threads): one coordinator plus 24
GAMERA ranks in a 3 x 8 x 1 decomposition. Ring averaging requires the
periodic `k` direction to remain untiled. Leave each script's `MPI_RANKS`
default unchanged. Outputs go to `output/smoke/` and `output/hour/`. Recheck
with:

```bash
./verify-output.sh output/smoke hello_earth_smoke
```

The validated smoke output contains 38 readable HDF5 files and the official
Kaipy quicklook `output/smoke/qkmsphpic.png`. Regenerate that plot from the
output directory with `msphpic -id hello_earth_smoke`.

After the hour run completes, generate density frames and an MP4 with
`./make-density-animation.sh`. It uses Kaipy's `msphpic -den -vid` renderer and
FFmpeg; set `PLOT_CPUS` or `FRAME_RATE` to override their defaults of 16 and
10, respectively.

Run `./make-coupling-animations.sh` for two additional products:
`hello-earth-fac-convection-north.mp4` and
`hello-earth-fac-convection-south.mp4` (REMIX FAC with potential contours and
related ionospheric quantities), plus `hello-earth-raiju.mp4` (RAIJU pressure,
density, entropy, and field-volume diagnostics).

Run `PLOT_CPUS=32 ./make-requested-animations.sh` for the presentation-focused
set: `hello-earth-density-planes.mp4`,
`hello-earth-north-convection.mp4`, `hello-earth-fac-north.mp4`, and
`hello-earth-fac-south.mp4`. The renderer is smoke-tested. It plots density in
SM `x-y` and `x-z`, traces the time-dependent meridional magnetic field in
`x-z`, reports northern CPCP on each convection frame, and overlays potential
contours on both FAC hemispheres.

## Recreating inputs

The helper refuses to overwrite existing inputs:

```bash
cd ~/src/gamera/runs/hello-earth
./prepare-inputs.sh
```

## Recorded SHA-256 values

```text
build_serial/bin/voltron.x  192f360c50eacde975cccaec9b1c8b174171f037e67b2bfbd3b8208c8f0d2f8c
build_mpi/bin/voltron_mpi.x 4427c929d524aee9df162e3821997b74047e4a855303af0f10c4fe65c9d00fd1
lfmD.h5                     afdbfb7eecd835e75aee250f9dc2a7a1133121f2c26ae97d6cfa547649d4aa4b
bcwind.h5                   39d578312a5f62726aac65495c9db4b9f6d7131a597e51ace49b17a699f5d4ab
raijuconfig.h5              1029bb610be965fc83c5d2875b59b671dfc866a98dd7fafd22e917330ee4d586
```

Recompute after rebuilding or regenerating inputs. A passing smoke run proves
software integration, not scientific validity. Follow the upstream rules of
the road and contact the developers before publication or presentation.

## References

- Kaiju/MAGE: <https://github.com/JHUAPL/kaiju>
- Kaipy: <https://github.com/JHUAPL/kaipy>
- GAMERA algorithm: Zhang et al. (2019), DOI `10.3847/1538-4365/ab3a4c`
- Global magnetosphere application: Sorathia et al. (2020), DOI
  `10.1029/2020GL088227`
