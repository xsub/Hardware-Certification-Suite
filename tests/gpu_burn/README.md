# GPU Burn

The `gpu_burn` test is an optional NVIDIA GPU stress test based on the open
source [GPU Burn](https://github.com/wilicc/gpu-burn) workload.

It runs only when the NVIDIA driver/runtime is already installed and
`nvidia-smi` can list GPUs. If NVIDIA support is not present, the test emits an
`HCS_UNSUPPORTED` marker and the runner records the step as unsupported instead
of treating the machine as failed.

Normal runner usage:

```bash
python -m hcs run --profile check --test gpu_burn --inventory 127.0.0.1, -c local
```

Direct Ansible usage:

```bash
ansible-playbook -c local -i 127.0.0.1, automated.yml --tags gpu_burn
```

Important variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `gpu_burn_duration` | `60` | GPU Burn duration in seconds. |
| `gpu_burn_memory` | `90%` | GPU memory target passed to `gpu_burn -m`. |
| `gpu_burn_devices` | empty | Optional GPU selection passed to `gpu_burn -i`. |
| `gpu_burn_use_doubles` | `false` | Enables GPU Burn double-precision mode. |
| `gpu_burn_use_tensor_cores` | `false` | Enables GPU Burn tensor-core mode. |
| `gpu_burn_build_from_source` | `true` | Clone/build GPU Burn when no binary exists. |
| `gpu_burn_binary` | `<cache>/gpu-burn/gpu_burn` | Existing or built GPU Burn binary. |
| `gpu_burn_source_url` | `https://github.com/wilicc/gpu-burn.git` | GPU Burn source repository. |
| `gpu_burn_telemetry_interval` | `5` | Seconds between `nvidia-smi` telemetry samples. |

The test writes the native GPU Burn log under the run scratch directory and
`nvidia-smi` telemetry plus a small JSON result under the run artifacts
directory.
