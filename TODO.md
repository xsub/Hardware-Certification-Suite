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
