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
```

The smoke case advances 11.5 seconds of model time. It uses 9 MPI processes
(one VOLTRON coordinator and eight GAMERA ranks) and four OpenMP threads per
process, for 36 cores. `run-hour.sh` uses the same layout for a one-hour model
experiment. Generated HDF5 inputs and all simulation output are intentionally
excluded from Git.

See the repository-level `AGENTS.md` for pinned revisions, hashes from the
validated run, build details, and scientific-use cautions.
