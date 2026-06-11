# TODO

## Phoronix on AlmaLinux 10

- [x] Handle stale Phoronix Fedora dependency names on AlmaLinux 10:
  `python-scikit-learn` is provided as `python3-scikit-learn`, and
  `SDL_sound-devel` is not available in the enabled AlmaLinux 10.2, CRB, and
  EPEL repositories on the validation host.
- [x] Confirm `openscad` is available from EPEL on the AlmaLinux 10.2
  validation host once the Phoronix role enables the required repositories.
- [ ] Revisit this compatibility patch when Phoronix/EPEL updates its Fedora
  dependency metadata or when `SDL_sound-devel` becomes available for EL10.

## Branded PDF report (future)

- [ ] Optionally align the PDF styling more closely with the AlmaLinux Hardware
  Certification SIG page
  (https://almalinux.org/certification/hardware-certification/). The brand
  foundation (Science Blue / Atlantis / Candlelight palette, Montserrat, logo)
  already matches; remaining options:
  - Option A (light touch): deepen the cover masthead to the page's navy
    (`#0f4266`) and add the program tagline ("Compatibility you can trust for
    performance, reliability, and stability") to the cover.
  - Option B (fuller): navy/cyan section headers echoing the page's coloured
    panels.
  Keep the report print-formal; do not copy the page's purple/cyan marketing
  panels.
- [x] Give the Phoronix role an explicit `HCS_RESULT` / `HCS_UNSUPPORTED` marker
  so an insufficient-disk-space outcome reads clearly in the report instead of
  the generic "recap reported ignored tasks". (Done: insufficient space and
  undefined EL releases both emit `HCS_UNSUPPORTED` with the details.)

## AI benchmarking (future work)

The `ai_llm` test (llama.cpp `llama-bench`, CPU/GPU) covers AI inference
throughput. Two further AI-benchmark approaches are deferred:

- [ ] **Extend the `phoronix` test with the `pts/machine-learning` profiles**
  (e.g. `pts/numpy`, `pts/onnx`, `pts/ncnn`, `pts/openvino`,
  `pts/tensorflow-lite`, `pts/llama-cpp`). Lowest effort — reuses the existing
  Phoronix integration and its PDF/JSON reporting — but these profiles pull
  heavy build/runtime dependencies and large datasets, so gate them behind the
  existing disk-space check (and likely a separate, opt-in profile/test id so a
  normal Phoronix run stays lean). Validate the EL10 dependency names like the
  current Phoronix profiles required.
- [ ] **Wire MLPerf Inference (MLCommons) as an authoritative tier**, driven by
  the `mlcflow` automation (MLPerf Inference v6.0, April 2026). This is the
  industry-standard, vendor-neutral metric and aligns with the Certification SIG
  review framing, but it is heavy: large models/datasets, long runs, and network
  setup. Best modelled as an optional datacenter/extreme-tier test rather than a
  default, with graceful `HCS_UNSUPPORTED` when prerequisites or accelerators are
  absent. References: https://mlcommons.org/working-groups/benchmarks/inference/
  and https://github.com/mlcommons/inference.
