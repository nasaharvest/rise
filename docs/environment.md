# Reference — environment variables

## How to use it

A user-level file holds what is **durable** — stable for you across runs and mostly across
projects — outside every project tree, so it can never be committed by accident:

```bash
rise init                        # runs `rise-eo init`: interactive; writes ~/.config/rise-eo/config.toml
rise init --blank                # or: write it empty and fill it in yourself
```

`rise-eo init` works the same without the umbrella.

| in the file | why |
|---|---|
| `subscription_id`, `resource_group`, `workspace`, `cluster`, `uami_client_id` | **required** — the platform coordinates. A platform admin hands all five over together and every AML call needs them |
| `model_registry`, `image_registry` | **optional** — where the registries live. Named rather than chosen per run, and models and images both outlive the runs that made them |

```python
import rise_eo
cfg = rise_eo.config.load()      # explicit -- rise-eo's own code never reads this on its own
```

`rise eo config` (or `rise-eo config`) prints the resolved value of each key and which of the three sources it came
from -- useful the moment a stale shell export silently outranks the file. Environment variables are named
`RISE_EO_*`.
