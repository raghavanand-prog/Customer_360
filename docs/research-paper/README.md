# Customer360 IEEE-style paper

- `Customer360_IEEE_Paper.md` — source of truth (Markdown).
- `Customer360_IEEE_Paper.pdf` — rendered two-column PDF (9 pages).
- `references.bib` — BibTeX for the 16 references, for anyone who wants to
  rebuild this in a LaTeX IEEEtran template instead.
- `paper.html` / `ieee.css` — intermediate HTML render and the print
  stylesheet used to produce the PDF.

## How the PDF was produced

No LaTeX distribution was available in the build environment, so the PDF
was produced via an HTML intermediate rather than `pandoc`'s native
LaTeX/IEEEtran path:

```bash
pandoc Customer360_IEEE_Paper.md -o paper.html --standalone \
    --mathjax=off --css=ieee.css

python3 -c "
from weasyprint import HTML
HTML('paper.html', base_url='.').write_pdf('Customer360_IEEE_Paper.pdf')
"
```

`ieee.css` approximates an IEEE conference two-column layout (Times,
~9.5pt body text, centred title/abstract spanning both columns, ruled
tables) but is **not** the official `IEEEtran.cls` LaTeX class. If a true
IEEEtran-formatted PDF is required, the fix is mechanical: feed
`Customer360_IEEE_Paper.md` and `references.bib` to `pandoc` with
`--template=ieee` (or a manually written IEEEtran `.tex` wrapper) on a
machine with `texlive` installed, e.g.:

```bash
pandoc Customer360_IEEE_Paper.md --bibliography=references.bib \
    --template=ieee.tex -o Customer360_IEEE_Paper.pdf
```
