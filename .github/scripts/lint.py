"""Fast checks that need no Odoo. Run from anywhere: python .github/scripts/lint.py

Checks every module of the repository:
- the manifest parses, has the HVG Solutions author/website, a short x.y.z
  version and a license the App Store accepts;
- every file listed in `data`, `demo` and `images` exists, and every asset
  glob matches at least one file;
- Python compiles, XML is well-formed.
"""
import ast
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
AUTHOR = "HVG Solutions"
WEBSITE = "https://hvg-solutions.com"
LICENSES = {"LGPL-3", "GPL-3", "AGPL-3", "OPL-1", "OEEL-1", "Other proprietary"}
SKIP_DIRS = {".git", "node_modules", "__pycache__"}

errors = []


def error(where, message):
    errors.append(f"{where}: {message}")


modules = sorted(p.parent for p in ROOT.glob("*/__manifest__.py"))
for module in modules:
    name = module.name
    try:
        manifest = ast.literal_eval((module / "__manifest__.py").read_text(encoding="utf-8"))
    except (ValueError, SyntaxError) as exc:
        error(name, f"manifest does not parse: {exc}")
        continue

    # Odoo prefixes a short version with the series; a hardcoded "19.0."
    # prefix makes the module uninstallable on the next series.
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(manifest.get("version", ""))):
        error(name, f"version must be x.y.z, got {manifest.get('version')!r}")
    if manifest.get("author") != AUTHOR:
        error(name, f"author must be {AUTHOR!r}, got {manifest.get('author')!r}")
    if manifest.get("website") != WEBSITE:
        error(name, f"website must be {WEBSITE!r}")
    if manifest.get("license") not in LICENSES:
        error(name, f"unknown license {manifest.get('license')!r}")
    if not manifest.get("installable", True):
        continue

    for key in ("data", "demo"):
        for rel in manifest.get(key, []):
            if not (module / rel).is_file():
                error(name, f"{key} file missing: {rel}")
    for rel in manifest.get("images", []):
        if not (module / rel).is_file():
            error(name, f"image missing: {rel}")

    for bundle, entries in manifest.get("assets", {}).items():
        for entry in entries:
            if isinstance(entry, (list, tuple)):
                directive, *paths = entry
                # ('include', 'web._assets_helpers') names a bundle, not a path.
                if directive == "include":
                    continue
                paths = paths[-1:]
            else:
                paths = [entry]
            for path in paths:
                if path.startswith(("http://", "https://", "/")):
                    continue
                addon, _, glob = path.partition("/")
                base = ROOT / addon
                if not base.is_dir():
                    # Another addon's asset (e.g. a 'remove' of a core file).
                    continue
                if not any(base.glob(glob)):
                    error(name, f"asset {bundle!r} matches nothing: {path}")

for path in ROOT.rglob("*"):
    if not path.is_file() or SKIP_DIRS.intersection(path.parts):
        continue
    rel = path.relative_to(ROOT)
    if path.suffix == ".py":
        try:
            compile(path.read_text(encoding="utf-8"), str(rel), "exec")
        except SyntaxError as exc:
            error(rel, str(exc))
    elif path.suffix == ".xml":
        try:
            ElementTree.parse(path)
        except ElementTree.ParseError as exc:
            error(rel, f"XML: {exc}")

print(f"{len(modules)} modules checked")
if errors:
    print("\n".join(errors))
    sys.exit(1)
print("lint: ok")
