#!/usr/bin/env python3
"""Upload images to PrepImages and print their public URLs (https://sfprep.fqrs.co.in/...).

    python3 upload.py <folder> <file> [<file> ...] [--wait]

    folder  where the images go under images/, e.g. books/ncert-3-maths-mela/ch01
    --wait  block until every URL is live on GitHub Pages (usually under a minute)

Every image is stored as lossless WebP, at most 800 px wide (wider images are scaled down,
narrower ones are left at their size). Any PNG/JPEG/GIF/WebP input is accepted and converted.
Needs Pillow: python3 -m pip install Pillow

File names get a content hash, so uploading the same image again returns the same URL.
Safe to run from many agents at once: uploads are serialised with a lock and pushed with retries.
Prints one JSON object per file: {"file", "path", "url", "new", "width", "height"}.
"""
import fcntl
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

try:
    from PIL import Image
except ImportError:
    sys.exit("upload.py needs Pillow to convert images to WebP: python3 -m pip install Pillow")

REPO = pathlib.Path(__file__).resolve().parent
BASE_URL = "https://sfprep.fqrs.co.in"
PAGES_ORIGIN = "https://satyamdilwala.github.io"
MAX_WIDTH = 800
MAX_INPUT_BYTES = 30 * 1024 * 1024
MAX_BYTES = 3 * 1024 * 1024


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def to_webp(f):
    """The image as lossless WebP, scaled down to MAX_WIDTH; exits on anything unusable."""
    if f.stat().st_size > MAX_INPUT_BYTES:
        sys.exit(f"{f}: larger than 30 MB")
    try:
        with Image.open(f) as im:
            if getattr(im, "n_frames", 1) > 1:
                sys.exit(f"{f}: animated images are not supported")
            im.load()
            alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
            im = im.convert("RGBA" if alpha else "RGB")
    except OSError:
        sys.exit(f"{f}: not an image Pillow can read")
    if im.width > MAX_WIDTH:
        im = im.resize((MAX_WIDTH, max(1, round(im.height * MAX_WIDTH / im.width))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", lossless=True, quality=100, method=5)
    data = buf.getvalue()
    if len(data) > MAX_BYTES:
        sys.exit(f"{f}: still over 3 MB as an {im.width}px WebP")
    return data, im.size


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout


def live(rel):
    req = urllib.request.Request(f"{PAGES_ORIGIN}/{rel}", method="HEAD",
                                 headers={"Host": BASE_URL.split("//")[1], "User-Agent": "Mozilla/5.0 PrepImages-upload"})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status == 200
    except Exception:
        return False


def main(argv):
    wait = "--wait" in argv
    args = [a for a in argv if a != "--wait"]
    if len(args) < 2:
        sys.exit(__doc__)
    folder = "/".join(slug(p) for p in args[0].split("/") if slug(p))
    files = [pathlib.Path(f) for f in args[1:]]
    blobs = []
    for f in files:  # convert every file before touching the repo, so a bad one leaves nothing half-done
        data, size = to_webp(f)
        blobs.append((f, data, size))

    with open(REPO / ".git" / "upload.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        git("pull", "-q", "--rebase", "--autostash", "origin", "main")
        results = []
        for f, data, (width, height) in blobs:
            name = f"{slug(f.stem)}-{hashlib.sha256(data).hexdigest()[:10]}.webp"
            rel = f"images/{folder}/{name}"
            dest = REPO / rel
            new = not dest.exists()
            if new:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            results.append({"file": str(f), "path": rel, "url": f"{BASE_URL}/{rel}", "new": new,
                            "width": width, "height": height})

        # also picks up files an interrupted run copied but never committed
        git("add", *{r["path"] for r in results})
        added = [p for p in git("diff", "--cached", "--name-only").splitlines() if p]
        if added:
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
        # Poll GitHub Pages directly: asking the public URL before the deploy finishes makes
        # Cloudflare cache the 404 for minutes.
        for r in results:
            r["live"] = any(live(r["path"]) or time.sleep(5) for _ in range(60))

    for r in results:
        print(json.dumps(r))


if __name__ == "__main__":
    main(sys.argv[1:])
