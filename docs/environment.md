# Reference — environment variables

## How to use it

A user-level file holds what is **durable** — stable for you across runs and mostly across
projects — outside every project tree, so it can never be committed by accident (spec 54):

```bash
fsd init                         # interactive; writes ~/.config/fsd/config.toml
fsd init --blank                 # or: write it empty and fill it in yourself (spec 55 D4)
```

| in the file | why |
|---|---|
| `subscription_id`, `resource_group`, `workspace`, `cluster`, `uami_client_id` | **required** — the platform coordinates. A platform admin hands all five over together and every AML call needs them |
| `model_registry`, `image_registry` | **optional** — where the registries live. Named rather than chosen per run, and models and images both outlive the runs that made them (spec 55 D2) |

```python
import fsd
cfg = fsd.config.load()          # explicit -- fsd's own code never reads this on its own
```

`fsd config` prints the resolved value of each key and which of the three sources it came from --
useful the moment a stale shell export silently outranks the file.
