# Installing RISE components

This repository installs as the Python distribution `rise`. It provides the RDM package (`import rdm`) and the `rise`
command (`src/rise_cli/`). rise-eo is an external component used by the satellite notebooks; the
`satellite` extra installs it from its own Git repository, pinned to a tag. How the components fit together:
[components.md](components.md).

## Install from a local checkout

From the repository root, in the Conda environment you want to use (Python 3.11 or newer):

```bash
pip install -e ".[rdm,satellite]"
```

The extras can also be installed separately:

```bash
pip install -e ".[rdm]"        # RDM module and its dependencies
pip install -e ".[satellite]"  # rise-eo and the demo model's dependencies
```

Editable installation means changes to the checked-out RDM source and the `rise` command are visible without
reinstalling. Use `pip install ".[rdm,satellite]"` without `-e` for a regular installation.

Check the imports and the command with:

```bash
python -c "import rdm, rise_eo; print('RISE RDM and rise-eo are available')"
rise --help
```

The RDM notebook can still be run from `rdm/notebooks/`; its existing relative paths point to the sample data and
source tree in this checkout. The satellite notebooks are under `notebooks/` and still require Azure configuration
(`rise init`), registered Azure ML environments, and access to the storage paths in their configuration. Installing
the package does not configure those services.

## Package layout

`pyproject.toml` names the installable distribution `rise` and maps two packages explicitly: `rdm` from
`rdm/src/rdm` and `rise_cli` from `src/rise_cli`. Therefore the import remains `import rdm`; the distribution name
and Python import names do not have to match. The `rise` script runs `rise_cli:main`. The notebook files and sample
datasets are repository assets, not installed Python modules.

The `satellite` extra pins rise-eo to an exact tag (`rise-eo[…] @ git+https://github.com/nasaharvest/rise-eo@v0.3.0`).
To move to a new rise-eo release, change the tag here and in `requirements.txt`, and the `rise_eo=` reference in the
two `ImageDefinition`s in `notebooks/build_images.ipynb` and the e2e notebooks.
