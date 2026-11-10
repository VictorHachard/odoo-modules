"""Print the test matrix as a GitHub Actions output: one entry per module.

Reading the manifests here means a new module is tested the day it is added,
with no list to keep in step.
"""
import ast
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

include = []
for manifest_path in sorted(ROOT.glob("*/__manifest__.py")):
    manifest = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("installable", True):
        include.append({"module": manifest_path.parent.name})

line = "matrix=" + json.dumps({"include": include})
print(line)
if os.environ.get("GITHUB_OUTPUT"):
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(line + "\n")
