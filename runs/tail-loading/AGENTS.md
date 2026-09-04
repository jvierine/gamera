# Tail-loading campaign operating notes

- Read `README.md` and `campaign.json` before changing or running anything.
- Large data belong in `/nfs/urdr/scratch/juha/gamera/tail-loading-pulses`.
- Never run concurrently with the hello-Earth 24-hour run.
- Use 25 MPI ranks x 5 OpenMP threads. Compiler builds remain limited to
  `make -j 50`; runtime parallelism is separate.
- Run the shared four-hour northward baseline once. Preserve its complete
  `00000` restart set; every duration case must branch from exactly that set.
- Run the 10-second case as a resource and end-to-end pilot before the rest.
- Preserve one-second wind cadence, two-second coupling, and five-second
  output unless the scientific design and all comparisons are revised.
- Treat synthetic indices as model proxies and retain the suffix `*` or words
  such as "-like" until their station/calibration pipelines are validated.
- Ideal-MHD reconnection is numerical and grid-dependent. Do not publish a
  threshold without resolution and cadence convergence checks.
- Log commands, commits, status, storage, failures, and scientific caveats in
  `/home/j/src/run.md` on `avaruus`.
- Do not open upstream pull requests, issues, or discussions. Pushing a branch
  directly to the user's fork `github.com/jvierine/gamera` is allowed.
