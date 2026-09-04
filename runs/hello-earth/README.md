# Hello Earth

This small MAGE configuration exercises GAMERA's solar-wind interaction with
Earth's dipole, REMIX ionospheric electrodynamics, and the RAIJU inner
magnetosphere. It uses observed one-minute OMNI conditions from
2016-08-09 09:00--11:00 UTC.

From the repository root on avaruus:

```bash
./build-avaruus.sh
./setup-kaipy-avaruus.sh
cd runs/hello-earth
./prepare-inputs.sh
./run-smoke.sh
./start-hour.sh
```

The smoke case advances 11.5 seconds of model time. It uses 9 MPI processes
(one VOLTRON coordinator and eight GAMERA ranks) and four OpenMP threads per
process, for 36 cores. The hour case uses 25 MPI processes (one coordinator and
24 GAMERA ranks in a 3 x 8 x 1 decomposition) with five threads each, for 125
CPU threads. Generated HDF5 inputs and all simulation output are intentionally
excluded from Git.

The hour case writes plasma state every 60 seconds of model time. After it
finishes, render density frames in parallel and encode an MP4 with:

```bash
./make-density-animation.sh
```

The coupled diagnostics are separate animations: `mixpic` shows northern and
southern field-aligned current with ionospheric-potential contours (plus
conductance, Joule heating, and precipitation), while `raijupic` shows RAIJU
inner-magnetosphere pressure and density:

```bash
./make-coupling-animations.sh
```

The purpose-built requested products are generated together with:

```bash
PLOT_CPUS=32 ./make-requested-animations.sh
```

This creates dual-plane (`x-y` and `x-z`) density with evolving meridional
magnetic-field lines, northern convection potential with the cross-polar-cap
potential in every frame, and dedicated northern/southern FAC maps with
convection-potential contours. The equatorial density panel uses a `Bz=0`
contour rather than misleading in-plane magnetic traces: terrestrial field
lines generally leave the equatorial plane.

See the repository-level `AGENTS.md` for pinned revisions, hashes from the
validated run, build details, and scientific-use cautions.
