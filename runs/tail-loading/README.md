# Tail-loading pulse-duration campaign

This campaign asks how long a purely southward IMF interval must persist to
produce a measurable magnetotail/substorm response. It uses one common,
four-hour northward-IMF coupled state and branches ten otherwise identical
runs with southward pulses of 10, 30, 60, 120, 240, 600, 1200, 1800, 3600,
and 7200 seconds. An unpulsed control is included. Each branch then runs at
northward IMF for four hours.

This is a numerical response-function experiment, not a realistic event
reconstruction. A response to a 10-second upstream pulse should not be
assumed: magnetosheath propagation, deformation, and numerical resolution can
filter it before it reaches the magnetopause.

## Prior work and novelty boundary

The components of this experiment have substantial precedent, but the exact
duration sweep was not found in the literature check performed 2026-09-04:

- Pham et al. (2016), DOI `10.1002/2015JA021982`, ran the closest reverse
  experiment: four hours of southward IMF followed by one 20-minute northward
  pulse, sweeping pulse amplitude rather than duration. The modeled
  ionospheric response began roughly 5--6 minutes after the bow shock and had
  roughly one-hour hysteresis.
- Samsonov et al. (2024), DOI `10.1029/2023JA032378`, compared global-MHD
  responses to a step from +5 to -5 nT at constant solar-wind conditions; it
  did not sweep pulse duration.
- Li et al. (2013), DOI `10.1002/jgra.50399`, analyzed 379 observed growth
  phases and found stronger solar-wind coupling led to earlier and more
  intense AL responses; the mean growth phase was about 70 minutes.
- Tanskanen et al. (2005), DOI `10.1029/2004JA010561`, examined prolonged
  southward IMF and the transition among loading-unloading cycles and steady
  magnetospheric convection.
- Klimas et al. (2005), DOI `10.1029/2005GL022916`, warned that global ideal-MHD
  models can favor a directly driven quasi-steady state instead of realistic
  loading-unloading hysteresis.

Therefore the exact GAMERA/MAGE duration scan appears scientifically useful,
but this README does **not** claim exhaustive novelty. A formal publication
would require a systematic literature review and consultation with the MAGE
developers.

## Controlled inputs

`campaign.json` is the authoritative design. The baseline and branches use:

- number density 5 cm^-3, temperature 100,000 K;
- velocity (-400, 0, 0) km/s;
- IMF Bx=By=0, Bz=+5 nT except during a Bz=-5 nT pulse;
- zero dipole tilt, F10.7=100, and one-second wind samples;
- 24 GAMERA ranks plus one VOLTRON coordinator, each with five OpenMP threads;
- two-second model coupling and five-second science output.

The one-second wind cadence represents the shortest pulse with ten full-value
intervals (11 endpoints) and one-second edge ramps.
The five-second full output is deliberately aggressive and is expected to
consume approximately 1.5--2 TB for the campaign. Confirm this estimate with
the first short branch before committing to every case.

## Prepare and run

Do not run this campaign concurrently with the 24-hour hello-Earth run. The
launch scripts enforce that guard. All large data remain under
`/nfs/urdr/scratch/juha/gamera/tail-loading-pulses`.

```bash
cd ~/src/gamera/runs/tail-loading
./prepare-campaign.sh
./run-baseline.sh
./run-case.sh control            # numerical-drift control
./run-case.sh 10                 # pilot and storage-rate check
./run-campaign.sh                # resumes, skips completed cases
./status.sh
```

The baseline runs from t=-14,400 s to t=0 at +5 nT and creates coupled restart
set `tail_baseline*.Res.00000.h5`. Each branch symlinks that immutable set and
starts its pulse at t=0. The runner refuses to overwrite existing results.

## Required diagnostics

The five-second GAMERA, REMIX, VOLTRON, and RAIJU outputs preserve the fields
needed for the following analysis:

1. **Input transmission:** determine pulse arrival, duration, and attenuation
   at the bow shock and magnetopause. Report responses against magnetopause
   arrival, not merely t=0 at the upstream boundary.
2. **Dayside and tail reconnection:** track open/closed topology, polar-cap
   area/flux, tail X-line position, earthward/tailward flow reversal, and
   reconnection electric field. In ideal MHD reconnection is numerical and
   resolution-dependent, so repeat threshold cases on another grid before
   physical interpretation.
3. **Tail loading/unloading:** lobe magnetic energy and flux, cross-tail
   current, plasma-sheet thickness and pressure, dipolarization, earthward
   bursty flows, and Poynting/enthalpy flux.
4. **Ionosphere:** northern/southern CPCP, peak and hemispherically integrated
   FAC, Region-1/Region-2/local-time sectors, Joule heating, and precipitating
   auroral power.
5. **Inner magnetosphere:** RAIJU pressure/energy and Dessler-Parker-Sckopke
   `DPSDst`, together with VOLTRON's Biot-Savart `BSDst` estimate.
6. **Ground response:** build/run `calcdb.x` to obtain SML, SMU, SME, SMR and
   current-system-separated ground perturbations. Use these as synthetic
   AL/AU/AE and SYM-H/Dst-like outputs.

`analyze-response.py` performs the first-pass extraction of CPCP, FAC peak and
integrated currents, auroral power, `DPSDst`, `BSDst`, and four SMR sectors:

```bash
~/src/gamera/.venv/bin/python analyze-response.py
./run-calcdb.sh 10
```

For every measure compare baseline, onset delay, peak perturbation, time
integral, and recovery time against pulse duration. Look for a transmission
threshold, a loading threshold, saturation, and regime changes near the
observational 30--90 minute growth-phase range.

## Index terminology

Do not label raw model quantities as official geomagnetic indices.

- `SML/SMU/SME` from model ground perturbations are AL/AU/AE-like.
- `SMR`/`BSDst` and RAIJU `DPSDst` are SYM-H/Dst-like and ring-current proxies.
- A defensible `Kp*` needs virtual mid-latitude stations, quiet-curve removal,
  local K ranges, Niemegk conversion, and a rolling three-hour window. Pulses
  shorter than three hours can still alter the resulting windowed value.
- A defensible `PCN*`/`PCS*` needs virtual polar stations, quiet-day removal,
  station-specific optimum directions, and empirical calibration. CPCP and
  the upstream merging electric field are useful additional drivers, not PC.

The ground-index approach follows Haiducek et al. (2017), DOI
`10.1002/2017SW001695`; the PC caveat follows Stauning (2013), DOI
`10.1002/jgra.50462`. Implement and validate those calibrated postprocessors
before reporting Kp* or PC* results.

## Analysis gates

- First run only the 10-second pilot and measure output volume and wall time.
- Confirm the discontinuity actually reaches the dayside boundary at the
  intended duration; otherwise treat magnetosheath filtering as the result.
- Use the unpulsed +5 nT control branch through the full recovery interval to
  subtract numerical drift.
- Threshold cases require resolution and cadence convergence tests.
- A passing run establishes software integration, not scientific validity.

No upstream pull request, issue, or discussion may be opened from this work.
Direct commits to `github.com/jvierine/gamera` are allowed.
