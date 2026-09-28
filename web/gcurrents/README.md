# GAMERA + REMIX current viewer

`gcurrents` is the numerical counterpart to the schematic viewer at
`https://juha.no/currents/`. It displays sampled GAMERA volume-current vectors
and REMIX field-aligned current from the completed 24-hour `hello_earth_24h`
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
