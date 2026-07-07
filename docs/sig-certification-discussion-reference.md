# Hardware Certification Suite Fork Work: SIG/Certification Discussion Reference

This is a pre-PR discussion reference for the AlmaLinux Certification SIG. It is
intended to separate small compatibility/correctness fixes from broader runner,
reporting, and optional benchmark proposals so the SIG can decide which pieces,
if any, fit the upstream Hardware Certification Suite and certification process.

## Baseline And Range

- Official upstream repository: `AlmaLinux/Hardware-Certification-Suite`.
- Official `main` was verified as identical to [`62d2882`](https://github.com/xsub/Hardware-Certification-Suite/commit/62d2882) (`basic CI workflow`)
  on 2026-06-23.
- Implementation range discussed here: [`62d2882`](https://github.com/xsub/Hardware-Certification-Suite/commit/62d2882)..[`dc80d4c`](https://github.com/xsub/Hardware-Certification-Suite/commit/dc80d4c).
- Fork-authored implementation commits in that range: 86.
- Upstream context before the fork-authored range:
  - [`2b8bbf1`](https://github.com/xsub/Hardware-Certification-Suite/commit/2b8bbf1) install phoronix-test-suite from epel
  - [`0fc1c73`](https://github.com/xsub/Hardware-Certification-Suite/commit/0fc1c73) add support for almalinux 10
  - [`62d2882`](https://github.com/xsub/Hardware-Certification-Suite/commit/62d2882) basic CI workflow

The practical suggestion is not to open one large pull request. The small fixes
can be reviewed as candidate patches, while runner/reporting/benchmarking work
should first be discussed as proposals.

Commit subjects listed below are historical Git subjects from the fork. The
area descriptions and suggested squash groups use the more conservative wording
intended for SIG discussion.

## Discussion Areas

### A. Fix Existing Tests On Stock AlmaLinux 9/10

Candidate fixes:

- Make the existing required tests run cleanly on ordinary AlmaLinux 9/10
  installs: use packages and repositories available on AlmaLinux, handle CRB /
  PowerTools differences, and avoid stale Fedora dependency names in Phoronix.
- Treat hardware-dependent gaps as `unsupported` instead of `passed` or generic
  failure. Examples: no KVM support, no safe RAID target, no separate network
  SUT, no usable SMBIOS data, and containerized hardware detection.
- Avoid damaging or surprising the SUT: do not write fio data over mounted or
  formatted RAID arrays; do not restart libvirt on systems already running VMs;
  remove only packages HCS installed.
- Make local and remote runs truthful: infer Ansible connection from inventory
  / runner input, not from `SSH_CONNECTION` in the operator environment.
- Add functional CI that actually executes the fast HCS path on AlmaLinux 9/10
  containers instead of relying only on syntax checks and dry runs.

SIG questions:

- Which tests are required for the certification decision, and which should be
  reported as required-but-unexercised when unsupported or filtered out?
- Should containerized `hw_detection` be an explicit unsupported outcome rather
  than a failure?
- Should Python 3.9 on AlmaLinux 9 be a supported runner floor, or should the
  documented bootstrap path require a newer Python from the operator?

### B. Runner / UX / Artifact Improvements

Proposal:

- Add a Python/Rich `hcs` runner as a proposed guided control layer over the
  existing Ansible tests.
- Keep direct Ansible execution available. The runner could become a guided
  evidence-collection path if the SIG agrees that this improves the process.
- Provide profiles, named presets, repeat passes, local defaults, `--host`,
  `--version`, live progress, graceful interruption, and step timeouts.
- Store every run in one durable sandbox under `/var/tmp` with stable names for
  console logs, per-step result JSON, `run.summary.json`, `run.report.txt`, and
  optional `run.report.pdf`.
- Add a draft `certification` preset that distinguishes required automated
  tests, optional automated tests, and manual USB/PXE checks for SIG review.
- Record controller identity and inventory in the artifacts so a reviewer can
  see what was exercised and what merely orchestrated the run.

SIG questions:

- Should the upstream suite adopt the runner as one guided operator path?
- Should the built-in `certification` preset live in the suite, or should SIG
  policy remain external and configure the runner?
- Which artifact names and directory layout should be considered stable?

### C. Reporting And Result-Contract Improvements

Candidate fixes / proposal:

- Use explicit test result markers such as `HCS_RESULT` and `HCS_UNSUPPORTED`
  instead of inferring certification outcomes from Ansible recap formatting.
- Keep status names honest across all outputs: `passed`, `failed`,
  `unsupported`, `skipped`, `not_run`, `interrupted`, and `dry_run`.
- Surface required tests that were not exercised, instead of allowing a partial
  run to look like a complete certification pass.
- Warn when runner config contains unknown keys, when required tests are
  disabled, when durations are clamped by profile caps, or when reports may be
  overwritten.
- Add an optional AlmaLinux-styled PDF rendering as review-friendly output,
  while keeping JSON and text reports as the contract-friendly artifacts.

SIG questions:

- Which status taxonomy should be shared across reports and review tooling?
- Should "required but unsupported" affect the overall certification verdict,
  or should it be review input only?
- Should the PDF report be considered an accepted submission artifact, or only
  a convenience rendering of the JSON/text contract?
- Should JSON schemas be introduced before any result contract is accepted?

### D. Optional Extended Tests: GPU Burn And AI Inference

Proposal:

- Keep `gpu_burn` optional and accelerator-specific. It can provide useful
  burn-in evidence for NVIDIA systems, but it should not block ordinary systems
  without supported GPUs.
- Prefer AlmaLinux-native NVIDIA driver guidance where possible; keep automatic
  driver or snap installation behind explicit operator control.
- Add `ai_llm` as an optional llama.cpp / `llama-bench` inference benchmark for
  CPU and GPU paths. It records prompt-processing and token-generation
  throughput and treats missing model/toolchain prerequisites as unsupported.
- Pin gpu-burn and llama.cpp sources and record the built commit in evidence so
  benchmark provenance is visible.

SIG questions:

- Do GPU burn-in and AI inference benchmarks belong in certification scope, or
  should they be an extended readiness / benchmark pack?
- If included, should they be opt-in, tied to a datacenter/accelerator profile,
  or kept entirely outside any SIG-approved certification preset?
- What model, dataset, source pin, checksum, and licensing requirements are
  acceptable for reviewable AI benchmark evidence?

## Proposed Commit Split

This split is meant for human review and future discussion. It is not a demand
that every group become one pull request.

### 1. SIG Framing, Certification Positioning, And Repo Hygiene

Area: cross-cutting framing for SIG discussion, not the `hcs` runner proposal.

Description:

This group explains the fork's direction, frames the work around the AlmaLinux
Hardware Certification process, records audit notes, and removes local/private
wording. It should stay separate from the `hcs` runner enhancement because it is
mostly discussion material and README positioning.

Short changelog:

- Add and evolve the development plan, changelog, critical-fix triage, and
  roadmap.
- Rework README structure around AlmaLinux hardware certification and SIG
  review rather than fork-local experimentation.
- Keep general certification positioning separate from runner-specific UX,
  screenshots, and artifact-flow docs.
- Remove local editor/private-machine wording and ignore local Claude settings.

Suggested squash before PR:

- Squash the roadmap/changelog/audit commits into one discussion-document
  update, or keep them out of a code PR and use them as SIG issue material.
- Squash the README positioning and repo-hygiene commits into one small
  documentation cleanup if the SIG wants that in-tree.

Commits:

- [`c67ed81`](https://github.com/xsub/Hardware-Certification-Suite/commit/c67ed81) Add xsub development plan
- [`a85b719`](https://github.com/xsub/Hardware-Certification-Suite/commit/a85b719) Rewrite README structure
- [`fe5f532`](https://github.com/xsub/Hardware-Certification-Suite/commit/fe5f532) Align README with certification program
- [`6ca9cc9`](https://github.com/xsub/Hardware-Certification-Suite/commit/6ca9cc9) Remove CI badges from feature list
- [`79e2669`](https://github.com/xsub/Hardware-Certification-Suite/commit/79e2669) Document fork development changelog
- [`3abab3d`](https://github.com/xsub/Hardware-Certification-Suite/commit/3abab3d) Anonymize README runner host details
- [`51ca912`](https://github.com/xsub/Hardware-Certification-Suite/commit/51ca912) Remove VPS wording from docs
- [`d962c61`](https://github.com/xsub/Hardware-Certification-Suite/commit/d962c61) Restructure README for product-first onboarding
- [`94bffd8`](https://github.com/xsub/Hardware-Certification-Suite/commit/94bffd8) Move runner details out of README
- [`43f2125`](https://github.com/xsub/Hardware-Certification-Suite/commit/43f2125) Refine README feature table headings
- [`1d6805e`](https://github.com/xsub/Hardware-Certification-Suite/commit/1d6805e) Trim README feature table
- [`9e79e1d`](https://github.com/xsub/Hardware-Certification-Suite/commit/9e79e1d) Rename development plan document
- [`7536106`](https://github.com/xsub/Hardware-Certification-Suite/commit/7536106) Update development plan roadmap
- [`0691896`](https://github.com/xsub/Hardware-Certification-Suite/commit/0691896) Add CRITICAL.md triage and fixes
- [`56a9d68`](https://github.com/xsub/Hardware-Certification-Suite/commit/56a9d68) Document commit convention and VPS validation in CRITICAL.md
- [`6e120f6`](https://github.com/xsub/Hardware-Certification-Suite/commit/6e120f6) Update README.md
- [`0996c72`](https://github.com/xsub/Hardware-Certification-Suite/commit/0996c72) Restructure README around the AlmaLinux Hardware Certification program
- [`ea28bc7`](https://github.com/xsub/Hardware-Certification-Suite/commit/ea28bc7) Add ansible-core and Certification SIG badges to the README
- [`17aa899`](https://github.com/xsub/Hardware-Certification-Suite/commit/17aa899) Ignore local Claude Code settings (.claude/)
- [`f8d4009`](https://github.com/xsub/Hardware-Certification-Suite/commit/f8d4009) Split README badges into two rows
- [`0a8410c`](https://github.com/xsub/Hardware-Certification-Suite/commit/0a8410c) Document the audit fixes: statuses, step timeout, RAID safety, checksums
- [`fe50dd7`](https://github.com/xsub/Hardware-Certification-Suite/commit/fe50dd7) Document the second wave: unexercised-required reporting, warnings, pins

### 2. Stock AlmaLinux Test Compatibility And Correctness

Area: fixes that make existing tests work cleanly on stock AlmaLinux 9/10.

Description:

This group makes existing test roles safer and more truthful on ordinary
AlmaLinux systems. It focuses on packages, repositories, hardware absence,
cleanup, and avoiding false passes.

Short changelog:

- Handle AlmaLinux 10 Phoronix dependency names and large-host/LTP behavior.
- Make containers, KVM, network, Phoronix, LTP, RAID, cllimits, and hardware
  detection report realistic outcomes.
- Restore network/firewall state, use NetworkManager-friendly link control, and
  follow the Ansible connection user.
- Protect RAID devices by default and require an explicit destructive opt-in.
- Remove exactly the packages a test installed; do not uninstall pre-existing
  SUT packages.
- Treat empty hardware reports and untested cllimits steps as non-passing.

Commits:

- [`a2b1362`](https://github.com/xsub/Hardware-Certification-Suite/commit/a2b1362) Handle EL10 Phoronix dependency names
- [`8dc209d`](https://github.com/xsub/Hardware-Certification-Suite/commit/8dc209d) Fix certification tests on stock AlmaLinux
- [`ea720df`](https://github.com/xsub/Hardware-Certification-Suite/commit/ea720df) Harden LTP and Phoronix roles for EL10 and large hosts
- [`b2d33aa`](https://github.com/xsub/Hardware-Certification-Suite/commit/b2d33aa) Harden test roles: result contract, honest unsupported, scoped cleanup
- [`6db7b1c`](https://github.com/xsub/Hardware-Certification-Suite/commit/6db7b1c) Detect network-test remoteness from the Ansible connection, not SSH_CONNECTION
- [`74c4357`](https://github.com/xsub/Hardware-Certification-Suite/commit/74c4357) Make the RAID test safe by default and fix multi-array fio targets
- [`b86acb8`](https://github.com/xsub/Hardware-Certification-Suite/commit/b86acb8) Remove only the packages each test actually installed
- [`6955a8a`](https://github.com/xsub/Hardware-Certification-Suite/commit/6955a8a) Phoronix: explicit unsupported markers, pipefail, and exact cleanup
- [`7ec6ae8`](https://github.com/xsub/Hardware-Certification-Suite/commit/7ec6ae8) cllimits: never report an untested step as passed
- [`001c36c`](https://github.com/xsub/Hardware-Certification-Suite/commit/001c36c) hw_detection: stop passing with an empty hardware report
- [`5f621b9`](https://github.com/xsub/Hardware-Certification-Suite/commit/5f621b9) Network test: preserve firewall state, follow the Ansible user, NM-compatible link control
- [`e539d8a`](https://github.com/xsub/Hardware-Certification-Suite/commit/e539d8a) cpu/ltp leftovers and evidence directory permissions
- [`7a40494`](https://github.com/xsub/Hardware-Certification-Suite/commit/7a40494) hw_detection: report unsupported in containers instead of failing

### 3. HCS Runner Proposal: UX, Presets, And Artifact Model

Area: runner / UX / artifact improvements that need explicit SIG acceptance.

Description:

This group introduces the `hcs` runner and the repeatable evidence model around
it. It is the largest opinionated enhancement: it changes the suite from "run
Ansible directly" toward "use a guided runner to produce reviewable artifacts."
That makes it a proposal for the certification process, not just a code cleanup.

Short changelog:

- Add the Rich runner, profiles, local defaults, run plans, progress output,
  repeated passes, graceful stop behavior, and CLI packaging.
- Move work data out of `/root` and into per-run sandboxes, defaulting to
  durable `/var/tmp`.
- Auto-load runner config and add named presets with per-test profile/duration
  controls.
- Add a draft certification preset with required, optional, and manual test
  scope.
- Add system identity output and runner UX throttling for verbose suites.
- Add `--host`, `--version`, and connection inference for local versus remote
  SUT runs.
- Add operator-facing runner docs, examples, screenshots, and sandbox artifact
  explanations.

Suggested squash before PR:

- If the SIG wants to evaluate the runner direction, squash this into one runner
  proposal PR: `Add hcs runner with sandboxed certification artifacts`.
- If one PR is still too large, split into two reviewable PRs:
  - runner core, sandbox, execution, status handling, and connection inference
  - draft preset UX, identity header, and operator docs
- Keep this separate from stock-test fixes so the SIG can accept correctness
  fixes even if the runner proposal needs more discussion.

Logical squash subgroups and commits:

Runner core and sandboxed artifacts:

- [`bd424c8`](https://github.com/xsub/Hardware-Certification-Suite/commit/bd424c8) Move certification work data out of root
- [`1fa44a3`](https://github.com/xsub/Hardware-Certification-Suite/commit/1fa44a3) Add Rich certification runner
- [`85889a3`](https://github.com/xsub/Hardware-Certification-Suite/commit/85889a3) Sandbox certification run artifacts
- [`fe6f86c`](https://github.com/xsub/Hardware-Certification-Suite/commit/fe6f86c) Merge branch 'feature/rich-runner'
- [`6193f41`](https://github.com/xsub/Hardware-Certification-Suite/commit/6193f41) Load runner config by default
- [`83ea7fa`](https://github.com/xsub/Hardware-Certification-Suite/commit/83ea7fa) Harden runner result detection and graceful stop
- [`acaee79`](https://github.com/xsub/Hardware-Certification-Suite/commit/acaee79) Default run sandbox to /var/tmp
- [`3c006c6`](https://github.com/xsub/Hardware-Certification-Suite/commit/3c006c6) Throttle live progress UI on verbose suites
- [`4b6c32f`](https://github.com/xsub/Hardware-Certification-Suite/commit/4b6c32f) Infer Ansible connection from inventory; add --host/--version; package as hcs

Presets and certification-run UX:

- [`1083bca`](https://github.com/xsub/Hardware-Certification-Suite/commit/1083bca) Add runner presets and GPU Burn snap support
- [`c47b282`](https://github.com/xsub/Hardware-Certification-Suite/commit/c47b282) Add certification policy preset
- [`1f61d36`](https://github.com/xsub/Hardware-Certification-Suite/commit/1f61d36) Add runner configuration text screenshots
- [`f157610`](https://github.com/xsub/Hardware-Certification-Suite/commit/f157610) Clarify README quick start boundaries

Runner identity and operator documentation:

- [`9d11b37`](https://github.com/xsub/Hardware-Certification-Suite/commit/9d11b37) Add built-in system identity header
- [`e70e5c0`](https://github.com/xsub/Hardware-Certification-Suite/commit/e70e5c0) Add check run README screenshot
- [`a8007d9`](https://github.com/xsub/Hardware-Certification-Suite/commit/a8007d9) Clarify sandbox log collection
- [`f371729`](https://github.com/xsub/Hardware-Certification-Suite/commit/f371729) Update README runner screenshot
- [`d03a3d3`](https://github.com/xsub/Hardware-Certification-Suite/commit/d03a3d3) Document runner and Ansible test commands
- [`d689f2d`](https://github.com/xsub/Hardware-Certification-Suite/commit/d689f2d) Move runner output near README intro
- [`f9f0eb8`](https://github.com/xsub/Hardware-Certification-Suite/commit/f9f0eb8) Add distro identity logo and GPU roadmap

### 4. Reporting, Result Contract, And Review Artifacts

Area: reporting and result-contract improvements.

Description:

This group makes reports harder to misread. It adds an AlmaLinux-styled PDF
rendering, keeps text and JSON outputs, and tightens runner status semantics so
partial, unsupported, interrupted, or dry-run results do not look like full
passes.

Short changelog:

- Add optional `run.report.pdf` with AlmaLinux assets and sample preview.
- Keep PDF generation best-effort so missing reportlab or report text issues do
  not hide the run result.
- Make the runner record truthful statuses across console, text, JSON, and PDF.
- Surface required tests that were not exercised.
- Warn on unknown config keys, disabled required tests, duration clamping, and
  report overwrites.

Commits:

- [`e527ed2`](https://github.com/xsub/Hardware-Certification-Suite/commit/e527ed2) Add a branded PDF certification report
- [`6839d26`](https://github.com/xsub/Hardware-Certification-Suite/commit/6839d26) Show the sample report as an inline PNG preview in the README
- [`78485a3`](https://github.com/xsub/Hardware-Certification-Suite/commit/78485a3) Move the sample report preview below the SIG-review note in the README
- [`b197365`](https://github.com/xsub/Hardware-Certification-Suite/commit/b197365) Note future PDF report styling options (SIG-page alignment)
- [`2736b15`](https://github.com/xsub/Hardware-Certification-Suite/commit/2736b15) Fix report_pdf NameError when reportlab is absent
- [`bb065b8`](https://github.com/xsub/Hardware-Certification-Suite/commit/bb065b8) Harden the runner and make report statuses truthful
- [`ec6ce29`](https://github.com/xsub/Hardware-Certification-Suite/commit/ec6ce29) Surface unexercised required tests; warn on config typos and clamped durations

### 5. Optional GPU And AI Test Packs

Area: optional extended tests such as gpu-burn and AI inference benchmarking.

Description:

This group adds accelerator-oriented tests that are useful for some hardware
reviews but are broader than the current baseline certification checklist. These
should be framed explicitly as optional proposals.

Short changelog:

- Add optional NVIDIA `gpu_burn` with unsupported reporting when prerequisites
  are absent.
- Document AlmaLinux-native NVIDIA driver preparation.
- Add optional `ai_llm` based on llama.cpp `llama-bench`, with CPU/GPU backend
  selection and JSON throughput evidence.
- Pin gpu-burn and llama.cpp source commits and record built commits in result
  artifacts.

Commits:

- [`8f9075f`](https://github.com/xsub/Hardware-Certification-Suite/commit/8f9075f) Add optional GPU Burn test
- [`c363fd9`](https://github.com/xsub/Hardware-Certification-Suite/commit/c363fd9) Add AlmaLinux NVIDIA setup guidance
- [`fecc9ad`](https://github.com/xsub/Hardware-Certification-Suite/commit/fecc9ad) Add an AI inference benchmark test (ai_llm, llama.cpp)
- [`226cf6d`](https://github.com/xsub/Hardware-Certification-Suite/commit/226cf6d) Pin llama.cpp and gpu-burn sources; record the built commit as evidence

### 6. CI, Packaging, And Platform Validation

Area: supports stock AlmaLinux 9/10 fixes and runner adoption.

Description:

This group makes the fork easier to validate continuously. It covers CI syntax
checks, functional AlmaLinux container runs, Python 3.9 support for AlmaLinux 9,
and package/console-script coverage.

Short changelog:

- Fix CI validators for AlmaLinux images.
- Add AlmaLinux 9/10 functional CI runs that execute the fast runner path.
- Lower runner compatibility to Python 3.9 for AlmaLinux 9 platform Python.
- Package the runner and test the `hcs` console script in CI.
- Keep CI/Python badges and Python setup notes with the validation work rather
  than with the runner proposal itself.
- Assert that containerized `hw_detection` produces the intended unsupported
  outcome.

Suggested squash before PR:

- Squash CI workflow additions, Python floor/package coverage, badges, and
  compatibility notes into one platform-validation PR.
- If the runner proposal is not accepted yet, keep only generic Ansible/YAML CI
  pieces and defer `hcs` console-script checks until the runner PR exists.

Commits:

- [`8f9ef01`](https://github.com/xsub/Hardware-Certification-Suite/commit/8f9ef01) Add GitHub Actions badges
- [`7f810b7`](https://github.com/xsub/Hardware-Certification-Suite/commit/7f810b7) Add Python and Ansible workflow badges
- [`10ce922`](https://github.com/xsub/Hardware-Certification-Suite/commit/10ce922) Document Python runner minimum version
- [`f839847`](https://github.com/xsub/Hardware-Certification-Suite/commit/f839847) Document AlmaLinux 10 Python setup
- [`19c44bf`](https://github.com/xsub/Hardware-Certification-Suite/commit/19c44bf) Label Python badge with minimum version
- [`c0f18fd`](https://github.com/xsub/Hardware-Certification-Suite/commit/c0f18fd) Fix AlmaLinux 8 CI YAML validator
- [`d0c97a4`](https://github.com/xsub/Hardware-Certification-Suite/commit/d0c97a4) Add AlmaLinux 9/10 functional CI run
- [`06d7899`](https://github.com/xsub/Hardware-Certification-Suite/commit/06d7899) Add AlmaLinux 10 validation badge and Compatibility section
- [`b372699`](https://github.com/xsub/Hardware-Certification-Suite/commit/b372699) Run on Python 3.9 so HCS works on AlmaLinux 9 platform Python
- [`743a201`](https://github.com/xsub/Hardware-Certification-Suite/commit/743a201) Release 0.2.0: cover packaging and Python 3.9/3.10 in CI, refresh README
- [`b63c174`](https://github.com/xsub/Hardware-Certification-Suite/commit/b63c174) CI: assert the container outcome hw_detection now actually produces

### 7. Reference, Roadmap, And Submission-Readiness Hardening

Area: pre-PR discussion support and result/submission guardrails.

Description:

This group was added after the initial reference split. It does not change the
basic discussion areas above; it makes the proposal easier to evaluate by
clarifying roadmap status, formalizing result/submission contracts, adding
privacy/preflight checks, and tightening optional accelerator evidence
guardrails.

Short changelog:

- Add the SIG discussion reference and conservative roadmap framing.
- Add result-contract fields, packaged JSON schemas, and submission manifest
  validation.
- Add artifact privacy audit, SUT/controller identity separation, explicit
  network endpoints, and `hcs preflight`.
- Keep GPU/AI evidence optional and add stricter submit-worthy AI provenance
  checks.
- Add unit and CI coverage for the new contract/manifest paths.

Suggested squash before PR:

- Keep the discussion reference and roadmap as SIG issue/discussion material.
- If the result/submission contract direction is accepted, squash the contract,
  manifest, privacy, SUT identity, preflight, and CI coverage into one or two
  reviewable implementation PRs.
- Keep accelerator/AI guardrails attached to the optional GPU/AI proposal, not
  to core certification fixes.

Commits:

- [`4e93d3c`](https://github.com/xsub/Hardware-Certification-Suite/commit/4e93d3c) Add SIG certification discussion reference
- [`e21ab17`](https://github.com/xsub/Hardware-Certification-Suite/commit/e21ab17) Clarify certification roadmap framing
- [`63be978`](https://github.com/xsub/Hardware-Certification-Suite/commit/63be978) Add run result contract schemas
- [`7805ccc`](https://github.com/xsub/Hardware-Certification-Suite/commit/7805ccc) Add submission manifest validation
- [`6bec9e6`](https://github.com/xsub/Hardware-Certification-Suite/commit/6bec9e6) Add artifact privacy audit
- [`3944ebc`](https://github.com/xsub/Hardware-Certification-Suite/commit/3944ebc) Separate SUT identity and network endpoints
- [`2c8caf6`](https://github.com/xsub/Hardware-Certification-Suite/commit/2c8caf6) Add runner preflight checks
- [`dde867c`](https://github.com/xsub/Hardware-Certification-Suite/commit/dde867c) Add accelerator evidence guardrails
- [`dc80d4c`](https://github.com/xsub/Hardware-Certification-Suite/commit/dc80d4c) Add CI contract validation coverage

## Suggested Squash / PR Shape

To keep review manageable, the history should be rewritten into fewer topical
commits before any PRs are opened. A reasonable target shape:

1. Documentation-only SIG framing / README positioning, or keep this as an
   issue/discussion instead of a PR.
2. Existing-test correctness for stock AlmaLinux 9/10.
3. `hcs` runner proposal, only after the SIG agrees the runner belongs in the
   upstream suite. Split into runner core and preset/docs only if one PR is too
   large.
4. Result contract and reporting artifacts.
5. Submission manifest, privacy audit, SUT identity, and preflight guardrails.
6. Optional GPU/AI test packs, probably as separate opt-in proposal PRs.
7. CI/platform validation, either as its own PR or attached to the feature PRs
   whose behavior it verifies.
