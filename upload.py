#!/usr/bin/env python3
"""Upload images to PrepImages and print their public URLs (https://sfprep.fqrs.co.in/...).

    python3 upload.py <folder> <file> [<file> ...] [--wait]

    folder  where the images go under images/, e.g. books/ncert-3-maths-mela/ch01
    --wait  block until every URL is live on GitHub Pages (usually under a minute)

File names get a content hash, so uploading the same image again returns the same URL.
Safe to run from many agents at once: uploads are serialised with a lock and pushed with retries.
Prints one JSON object per file: {"file", "path", "url", "new"}.
"""
import fcntl
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent
BASE_URL = "https://sfprep.fqrs.co.in"
MAX_BYTES = 3 * 1024 * 1024
SIGNATURES = [(b"\x89PNG", "png"), (b"\xff\xd8\xff", "jpg"), (b"GIF8", "gif")]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def kind(data):
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return next((ext for sig, ext in SIGNATURES if data.startswith(sig)), None)


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout


def main(argv):
    wait = "--wait" in argv
    args = [a for a in argv if a != "--wait"]
    if len(args) < 2:
        sys.exit(__doc__)
    folder = "/".join(slug(p) for p in args[0].split("/") if slug(p))
    files = [pathlib.Path(f) for f in args[1:]]

    with open(REPO / ".git" / "upload.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        git("pull", "-q", "--rebase", "--autostash", "origin", "main")
        results, added = [], []
        for f in files:
            data = f.read_bytes()
            ext = kind(data)
            if ext is None or len(data) > MAX_BYTES:
                sys.exit(f"{f}: not a PNG/JPEG/WebP/GIF under 3 MB")
            name = f"{slug(f.stem)}-{hashlib.sha256(data).hexdigest()[:10]}.{ext}"
            rel = f"images/{folder}/{name}"
            dest = REPO / rel
            new = not dest.exists()
            if new:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, dest)
                added.append(rel)
            results.append({"file": str(f), "path": rel, "url": f"{BASE_URL}/{rel}", "new": new})

        if added:
            git("add", *added)
            git("commit", "-q", "-m", f"Add {len(added)} image(s) to images/{folder}")
            for attempt in range(5):
                try:
                    git("push", "-q", "origin", "main")
                    break
                except subprocess.CalledProcessError:
                    if attempt == 4:
                        raise
                    time.sleep(2 + attempt * 2)
                    git("pull", "-q", "--rebase", "--autostash", "origin", "main")

    if wait:
        for r in results:
            for _ in range(60):
                try:
                    req = urllib.request.Request(r["url"], method="HEAD", headers={"User-Agent": "Mozilla/5.0 PrepImages-upload"})
                    with urllib.request.urlopen(req, timeout=10) as res:
                        if res.status == 200:
                            break
                except Exception:
                    pass
                time.sleep(5)
            else:
                r["live"] = False

    for r in results:
        print(json.dumps(r))


if __name__ == "__main__":
    main(sys.argv[1:])
