"""The `rise` command: `rise init` and `rise <role> ...` over the installed `rise-<role>` commands.

Not called `rise`: PyPI's unrelated `rise` package ships a top-level `rise` package.
"""

import importlib.metadata
import shutil
import subprocess
import sys

USAGE = "usage: rise init [args...] | rise <role> [args...]"


def components() -> list[str]:
    """The roles of the installed components that ship a `rise-<role>` command, sorted."""
    names = {ep.name for ep in importlib.metadata.entry_points(group="console_scripts")}
    return sorted(name.removeprefix("rise-") for name in names if name.startswith("rise-"))


def _run(role: str, args: list[str]) -> int:
    exe = shutil.which(f"rise-{role}")
    if exe is None:
        installed = ", ".join(components()) or "none"
        print(f"rise: no command `rise-{role}` (installed components: {installed})", file=sys.stderr)
        return 2
    return subprocess.call([exe, *args])


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in ("-h", "--help"):
        print(f"{USAGE}\n\ninstalled components: {', '.join(components()) or 'none'}")
        return 0
    if args[0] == "init":
        # Every component that installs a `rise-<role>` command accepts `init`.
        for role in components():
            rc = _run(role, ["init", *args[1:]])
            if rc:
                return rc
        return 0
    return _run(args[0], args[1:])


if __name__ == "__main__":
    sys.exit(main())
