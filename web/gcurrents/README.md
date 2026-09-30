# GAMERA + REMIX current viewer

`gcurrents` is the numerical counterpart to the schematic viewer at
`https://juha.no/currents/`. It displays frozen GAMERA current streamlines,
optional sampled vectors, and REMIX FAC from the completed 24-hour `hello_earth_24h`
MAGE run on Avaruus.

The authoritative compact data product is `gcurrents.h5`. Browser `.bin` files
and `manifest.json` are transports generated from the same arrays. They are not
separate scientific products.

Generate on Avaruus, where the source HDF5 files reside:

```bash
/home/juha/venvs/gcurrents/bin/python export_gcurrents.py \
  --source /nfs/urdr/scratch/juha/gamera/hello-earth-24h/output \
  --output /nfs/urdr/scratch/juha/gamera/hello-earth-24h/gcurrents-export
```

The default 15-minute browser cadence retains 97 frames from model time 0 to
24 hours. GAMERA current density is stored in nA/m². REMIX field-aligned
current is stored in µA/m² with positive sign outward from the ionosphere,
matching Kaipy's plotting convention. ReMIX's dataset named “Latitude” is
polar colatitude; the exporter maps it explicitly to the north/south sphere.

The input OMNI record has a plasma-data gap from 2016-08-09 09:44 to 12:02 UTC
and an IMF gap from 09:46 to 11:59 UTC. Kaipy linearly interpolated both gaps.
This limitation must remain visible in any interpretation of the run.

Serve this directory at `/gcurrents/`. It imports the vendored Three.js build
from sibling route `/currents/vendor/`.
# Frozen current paths

The viewer has ten frozen snapshots with equally spaced target times from
02:00 to 24:00 model time, excluding the first two hours as burn-in. Saved
one-minute outputs are chosen nearest each target (within 30 seconds).
Each snapshot's REMIX FAC comes from exactly the same saved model step as J.
Eight spatially distributed paths per seed family are displayed. The gear
opens a collapsed panel containing only current-family checkboxes and the
snapshot slider. A passive legend occupies the bottom left. Curves have no
click/selection action. The old arrow-cloud, path isolation, and metrics
controls are removed. Data provenance remains on `about.html`.

`export_snapshots.py` reads every cell centre in the selected volume from the
24 MPI rank files (no strides), writing `snapshots.h5`. `trace_snapshots.py`
uses linear Delaunay interpolation and RK4 with ds=0.12 RE, retaining positions
and J in `current_paths.h5`; JSON files are browser transports. Run both with
the base conda Python environment. Three-dimensional J streamlines are not
magnetic field lines and are not time trajectories of individual particles.
Their endpoints and seed groups are explicit. The interpolation is not
divergence-preserving and does not prove exact current closure. No path is
invented between the MHD cutoff at 2.2 RE and the REMIX ionosphere.

Seed families include dayside (up to 20), tail (40), westward J in the ring
region (32), R1-like (32) and R2-like (32). Spatial sectors are interleaved
so low display counts include both flanks and hemispheres. R1/R2-like denotes
the conventional radial-current sense at the seed, within stated latitude
windows on the MHD shell; it is not a unique system decomposition. Ring-region
paths use GAMERA J and do not separately reconstruct RAIJU particle currents.

Regenerate the ten-snapshot product using `export_snapshots.py --source
/path/to/output --output snapshots.h5`, then `trace_snapshots.py --source
snapshots.h5 --output . --workers 4`. The latter runs independent snapshots
in worker processes and serializes the combined HDF5 in the parent process.

The ten-snapshot export was endpoint-validated with
`validate_snapshot_paths.py .`: invalid terminal samples outside the
interpolation domain were trimmed, without connecting across any internal
gap. The integrator now checks the accepted RK4 endpoint directly, and JSON
serialization rejects non-finite numbers.
