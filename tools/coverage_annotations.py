import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from coverage import Coverage
from coverage.misc import CoverageException


def sh(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def get_changed_py_files(base_ref: str, head_ref: str) -> List[Path]:
    # IMPORTANT: triple dots means "changes introduced by PR"
    out = sh(["git", "diff", "--name-only", f"{base_ref}...{head_ref}"])
    files: List[Path] = []

    for line in out.splitlines():
        p = Path(line)
        if p.suffix == ".py" and p.exists():
            files.append(p)

    return files


def collect_uncovered_lines(changed_files: List[Path]) -> List[Dict[str, Any]]:
    """
    Returns GitHub Check Run annotations: one per uncovered line, for changed files only.
    """
    cov = Coverage(data_file=".coverage")
    cov.load()

    annotations: List[Dict[str, Any]] = []

    for f in changed_files:
        try:
            analysis = cov.analysis2(str(f))
            # analysis2 returns: (filename, statements, excluded, missing, missing_formatted)
            missing = set(analysis[3])
        except CoverageException:
            continue

        for line_no in sorted(missing):
            annotations.append(
                {
                    "path": str(f).replace("\\", "/"),
                    "start_line": int(line_no),
                    "end_line": int(line_no),
                    "annotation_level": "notice",  # informational only (no gate)
                    "message": "Not covered by tests",
                    "title": "Coverage",
                }
            )

    return annotations


def main() -> None:
    base = os.environ.get("GITHUB_BASE_SHA")
    head = os.environ.get("GITHUB_SHA")

    if not base or not head:
        print(json.dumps({"annotations": [], "changed_files": []}))
        return

    changed = get_changed_py_files(base, head)
    annotations = collect_uncovered_lines(changed)

    # GitHub has annotation limits; keep it reasonable.
    max_annotations = 50
    annotations = annotations[:max_annotations]

    print(json.dumps({"annotations": annotations, "changed_files": [str(p) for p in changed]}))


if __name__ == "__main__":
    main()
