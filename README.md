## Installation

RISE (Rapid Intelligence System for the Environment) is installable as a single Python package named `rise`. Installing it with the `rdm` and `satellite` extras gives you two components:

| Component | Where it comes from | How you import it |
|-----------|--------------------|-------------------|
| **RDM** (Reference Data Management) | Bundled in this repository (`rdm/`) and installed with RISE | `import rdm` |
| **FSD** (Fetch Satellite Data) | A module hosted at [github.com/nikhilsrajan/fsd](https://github.com/nikhilsrajan/fsd) and installed automatically with RISE (pinned to `v0.1.0`). | See the [FSD repository](https://github.com/nikhilsrajan/fsd) |

Because FSD is installed from its GitHub repository, **Git must be installed** on the machine and it needs internet access during installation.

> ⚠️ **Python 3.11 or newer is required.** FSD v0.1.0 does not install on Python 3.10 or older; pip stops with `Package 'fsd' requires a different Python`.

> ⚠️ **Do not run `pip install rise` on its own.** An unrelated package named `rise` exists on PyPI, and pip would install that instead. Always install from the GitHub URL or from a cloned copy of this repository, as shown below.

### Before you start

Create and activate a fresh environment with **Python 3.11 or newer**. Don't reuse an older environment that runs Python 3.10.

```bash
conda create -n rise python=3.11
conda activate rise
```

### Option A: Install directly from GitHub

Use this if you only want to *use* RISE and don't plan to edit the code. No clone is needed.

```bash
pip install "rise[rdm,satellite] @ git+https://github.com/nasaharvest/rise.git"
```

### Option B: Clone and install in editable mode

Use this if you want to develop or modify RISE. Changes you make to the code take effect without reinstalling.

```bash
git clone https://github.com/nasaharvest/rise.git
cd rise
pip install -e ".[rdm,satellite]"
```

### Verify the installation

```bash
python -c "import rdm; print('RDM installed')"
```

### Troubleshooting

- **Geospatial libraries fail to build** (GDAL, rasterio, geopandas; most common on Windows): install them from conda-forge first, then rerun the pip command.
  ```bash
  conda install -c conda-forge geopandas rasterio
  ```
- **`ERROR: Package 'fsd' requires a different Python: 3.10.x not in '>=3.11'`:** your environment's Python is too old. Create a new one with `conda create -n rise python=3.11`, activate it, and install again. Check your version with `python --version`.
- **Errors mentioning `git` while installing FSD:** make sure Git is installed and available on your `PATH`.

### Not covered by the install

Azure credentials and the Azure ML image setup are **separate manual steps** and are not handled by `pip install`.
