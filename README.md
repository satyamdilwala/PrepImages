# PrepImages

Public images used by SF Prep (prep.fqrs.co.in) questions and notes, served by GitHub Pages at
**https://sfprep.fqrs.co.in** (see `CNAME`). A file at `images/x/y.webp` is live at
`https://sfprep.fqrs.co.in/images/x/y.webp` about a minute after it is pushed.

- `images/branding/` — SF Prep logos
- `images/books/<bookId>/<chapter>/` — question figures

## Rules for every image

- **WebP only.** Every image in this repo is a lossless `.webp`.
- **At most 800 px wide.** Students read on phones, tablets and laptops; 800 px is sharp on all
  of them and keeps pages light. Narrower images keep their own size and are never enlarged.
- **One file per picture.** The same image is never stored twice. `upload.py` finds an identical
  image anywhere in the repo and returns its URL instead of adding a copy, even for another
  question or folder. A file can therefore be shared by many questions: delete one only after
  checking that no question shows it.
- **Always add images with `upload.py`.** It converts any PNG/JPEG/GIF/WebP to an 800 px-max
  lossless WebP itself, so pass the original file. Do not commit image files by hand or through
  the GitHub web UI: that skips the conversion.

## Upload

```sh
python3 -m pip install Pillow    # once
python3 upload.py books/ncert-3-maths-mela/ch01 crop1.png crop2.png --wait
```

Prints one JSON line per file with the public `url` (always `.webp`) and the stored `width` and
`height`. Put the `url` in the question (`<img src="URL" alt="..." style="max-width:100%">`). Names
carry a content hash, so re-uploading the same image gives the same URL. Many agents can run it at once.
