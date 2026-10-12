# Installing RISE components

This repository can be installed as the Python distribution `rise`. The RDM
source package remains importable as `rdm`. FSD is an external package used by
the satellite notebook; the `satellite` extra installs it from its separate
Git repository.

## Install from a local checkout

From the repository root, in the Conda environment you want to use:

```bash
pip install -e ".[rdm,satellite]"
```

The extras can also be installed separately:

```bash
pip install -e ".[rdm]"        # RDM module and its dependencies
pip install -e ".[satellite]"  # FSD and the demo model's dependencies
```

Editable installation means changes to the checked-out RDM source are visible
without reinstalling. Use `pip install ".[rdm,satellite]"` without `-e` for a
regular installation.

Check the imports with:

```bash
python -c "import rdm, fsd; print('RISE RDM and FSD are available')"
```

The RDM notebook can still be run from `rdm/notebooks/`; its existing relative
paths point to the sample data and source tree in this checkout. The satellite
notebooks are under `notebooks/` and still require Azure configuration,
registered Azure ML environments, and access to the storage paths in their
configuration. Installing the package does not configure those services.

## Package layout

`pyproject.toml` names the installable distribution `rise` and discovers the
existing package from `rdm/src/rdm`. Therefore the current import remains
`import rdm`; the distribution name and Python import name do not have to match.
The notebook files and sample datasets are repository assets, not installed
Python modules.
