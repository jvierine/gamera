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
process, for 36 cores. `run-hour.sh` uses the same layout for a one-hour model
experiment. Generated HDF5 inputs and all simulation output are intentionally
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

See the repository-level `AGENTS.md` for pinned revisions, hashes from the
validated run, build details, and scientific-use cautions.
