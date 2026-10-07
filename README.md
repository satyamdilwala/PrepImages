# PrepImages

Public images used by SF Prep (prep.fqrs.co.in) questions and notes, served by GitHub Pages at
**https://sfprep.fqrs.co.in** (see `CNAME`). A file at `images/x/y.png` is live at
`https://sfprep.fqrs.co.in/images/x/y.png` about a minute after it is pushed.

- `images/branding/` — SF Prep logos
- `images/books/<bookId>/<chapter>/` — question figures

## Upload

```sh
python3 upload.py books/ncert-3-maths-mela/ch01 crop1.png crop2.png --wait
```

Prints one JSON line per file with the public `url` to put in the question
(`<img src="URL" alt="..." style="max-width:100%">`). Names carry a content hash, so re-uploading
the same image gives the same URL. Many agents can run it at once.
