# How RISE is organized

## Structure

- This repository, `nasaharvest/rise`, is the umbrella. It holds one extra per component (each pinned to an exact
  tag), the notebooks that use more than one component, these docs, and the `rise` command.
- Each component is its own repository, `nasaharvest/rise-<role>`, with its own CI, releases, issues, license and
  visibility.
- Components never import each other. They exchange files with a documented schema; for example, RDM's
  standardized field file is the label file `rise_eo.create_training_data` reads.
- A part becomes a new component only when its maintainer, release cadence or dependencies differ from every
  existing component. Otherwise it is a module inside an existing one.
- `requires-python` here is the highest minimum of the components (today `>=3.11`, from rise-eo).
- A deployed service, such as `ukrop`, is not a component: RISE links to it and never installs it.

Current state: RDM still lives in `rdm/` (moving to `nasaharvest/rise-rdm` later). rise-eo lives at
`github.com/nasaharvest/rise-eo`.

## Names

| What | Form | rise-eo |
|---|---|---|
| repository | `nasaharvest/rise-<role>` | `nasaharvest/rise-eo` |
| distribution (pip) | `rise-<role>` | `rise-eo` |
| import | `rise_<role>` | `rise_eo` |
| command | `rise-<role>` | `rise-eo` |
| config folder | `rise-<role>` | `~/.config/rise-eo` |
| environment variables | `RISE_<ROLE>_*` | `RISE_EO_*` |

No shared `rise.<role>` namespace: PyPI's unrelated `rise` package ships a top-level `rise` package, which breaks a
namespace package. No bare role names: `rdm` already exists on PyPI.

## The `rise` command

- `rise init` runs `rise-<role> init` for every installed component that ships a `rise-<role>` command, so such a
  command must accept `init`.
- `rise <role> …` runs `rise-<role> …`.
- No component installs a command called `rise`. Each component's own command works without the umbrella.

The code is in `src/rise_cli/`.

The umbrella's distribution is still named `rise`, the same name as the unrelated PyPI package, so never
`pip install rise` from PyPI (see the README).
