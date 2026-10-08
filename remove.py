#!/usr/bin/env python3
"""Remove images from PrepImages that nothing uses any more.

    python3 remove.py <reason> <path> [<path> ...]

    path    repo path (images/...) or public URL (https://sfprep.fqrs.co.in/images/...)

The caller checks that no question still points at the files. Same lock as upload.py.
Prints one JSON object per path: {"path", "removed"}.
"""
import fcntl
import json
import pathlib
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent
BASE_URL = "https://sfprep.fqrs.co.in"


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    reason, paths = argv[0], [p.removeprefix(BASE_URL + "/") for p in argv[1:]]
    if any(not p.startswith("images/") or ".." in p for p in paths):
        sys.exit("only paths under images/ can be removed")

    with open(REPO / ".git" / "upload.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        git("pull", "-q", "--rebase", "--autostash", "origin", "main")
        results = []
        for p in paths:
            gone = (REPO / p).exists()
            if gone:
                git("rm", "-q", "--", p)
            results.append({"path": p, "removed": gone})
        removed = [r["path"] for r in results if r["removed"]]
        if removed:
            git("commit", "-q", "-m", f"Remove {len(removed)} unused image(s): {reason}")
            for attempt in range(5):
                try:
                    git("push", "-q", "origin", "main")
                    break
                except subprocess.CalledProcessError:
                    if attempt == 4:
                        raise
                    time.sleep(2 + attempt * 2)
                    git("pull", "-q", "--rebase", "--autostash", "origin", "main")

    for r in results:
        print(json.dumps(r))


if __name__ == "__main__":
    main(sys.argv[1:])
