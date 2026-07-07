# Hardware Certification Suite Roadmap

This roadmap tracks gaps that should be addressed before the forked work is
proposed as stable upstream behavior. It is intentionally conservative: items
below are meant to strengthen AlmaLinux certification evidence, reviewability,
and operator safety rather than broaden the scope for its own sake.

## Implementation Status

The implementation now covers the roadmap as vertical slices in this fork:

- Result-contract fields and packaged JSON schemas are present.
- Submission manifest generation and `hcs validate-run` are present.
- Privacy audit and manifest privacy labels are present.
- SUT identity is separated from controller identity, with explicit network
  endpoint support for remote runs.
- `hcs preflight` checks runner readiness before long runs.
- GPU/AI workloads remain optional, with submit-worthy AI guardrails for pinned
  and checksummed inputs.
- Unit tests and AlmaLinux container smoke checks cover the contract paths.

Remaining open points are SIG decisions: whether the runner belongs upstream,
which preset/policy shape should be accepted, and whether optional
accelerator/AI evidence belongs in any official certification profile.

## Near-Term: Certification Evidence Integrity

- Define the top-level run verdict contract before treating `run.summary.json`
  as a submission artifact. In particular, required tests that are
  `unsupported`, `skipped`, `not_run`, disabled, or filtered out should not be
  easy for automation to mistake for a certification-ready pass.
- Add a machine-readable field such as `certification_ready: false` or a
  distinct status such as `review_required` / `incomplete_required` when any
  required-scope test lacks a pass/fail verdict.
- Formalize JSON schemas for `config.requested.json`, per-step result JSON,
  `run.summary.json`, and any future submission manifest.
- Keep text and PDF reports as renderings of the structured result contract,
  not as the primary contract.

## Submission To AlmaLinux/certifications

- Define a submission manifest that maps runner artifacts to the structure
  expected by `AlmaLinux/certifications`.
- Specify which files are required, optional, or reviewer-convenience-only.
- Document the intended directory naming convention for public certification
  result submissions.
- Add validation tooling that checks a completed run directory before a user
  opens a pull request against `AlmaLinux/certifications`.

## Privacy And Public Evidence

- Define a redaction policy for public submissions. Hardware inventory can
  include serial numbers, MAC addresses, hostnames, IP addresses, DMI strings,
  storage identifiers, and other environment-specific details.
- Decide which raw artifacts must remain private, which should be redacted, and
  which are safe to publish unchanged.
- Add an artifact audit/preflight command that warns before publishing likely
  sensitive identifiers.

## SUT Identity And Remote Runs

- Separate controller identity from System Under Test identity in all reports.
  Controller facts are useful for debugging, but certification evidence must
  clearly identify the SUT.
- Treat `hw_detection` output as the canonical SUT identity source, especially
  for remote LTS/SUT runs.
- Make remote network-test endpoint configuration explicit. Avoid relying on
  `SSH_CONNECTION` as the only source of `lts_ip` and `sut_ip`; support
  operator-provided endpoints and validate them in preflight.

## Runner Proposal Maturity

- Keep the `hcs` runner framed as a proposed guided operator path until the
  Certification SIG accepts it.
- Keep direct Ansible usage documented and supported for low-level debugging
  and for users who need the current upstream workflow.
- Decide whether the draft `certification` preset belongs in the suite, in SIG
  policy configuration, or in examples only.
- Add an `hcs preflight` command before expanding the runner surface. It should
  check privileges, Ansible, disk space, network mode, required tools, artifact
  paths, and public-submission readiness.

## Optional Accelerator And AI Workloads

- Keep `gpu_burn` and `ai_llm` outside the core certification preset unless the
  SIG explicitly creates an accelerator/datacenter profile.
- Coordinate AI benchmarking scope with relevant AlmaLinux stakeholders before
  treating inference throughput as certification evidence.
- Require pinned sources and model checksums for any AI benchmark that may be
  submitted for review. A default network download without a required checksum
  is acceptable for experiments, but weak for public certification evidence.
- Clarify licensing, model provenance, artifact size, and offline/cache
  behavior before recommending AI benchmark submissions.

## CI And Validation

- Keep container CI described as smoke/contract coverage. It cannot validate
  DMI/SMBIOS, KVM hardware support, real network topology, RAID devices, GPUs,
  or long-running stability.
- Add targeted tests for result-contract edge cases: required unsupported,
  required filtered out by `--test`, interrupted runs, failed report rendering,
  and remote SUT identity.
- Add fixture-based validation for the public submission manifest once the
  manifest format exists.
