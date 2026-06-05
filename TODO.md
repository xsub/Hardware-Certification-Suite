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
- [ ] Give the Phoronix role an explicit `HCS_RESULT` / `HCS_UNSUPPORTED` marker
  so an insufficient-disk-space outcome reads clearly in the report instead of
  the generic "recap reported ignored tasks".
