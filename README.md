# एकात्म मानववाद · Integral Humanism

A reading & listening website for *Integral Humanism* — the four lectures delivered by
Pandit Deendayal Upadhyaya in Bombay, 22–25 April 1965.

- **Read**: the full book as an animated page-flip reader (~170 pages, page-turn sound)
- **Listen**: audio deep-dives in English & Hindi (generated with Google NotebookLM)
- **The Author** & **The Core Philosophy** sections

## Structure
- `index.html` — the built site (static, self-contained + `fonts/` + `podcast/*.mp3`)
- `site_template.html` — source template; edit this, never `index.html`
- `build.py` — injects `book.json` into the template → `index.html`
- `parse_book.py` — parses the source PDF text into `book.json`
- `podcast/scripts/` — podcast episode scripts (4 chapters × EN/HI)
- `podcast/gen_smallest.py` — TTS generation pipeline (Smallest.ai lightning-v3.1)

Static site — no build step needed to serve; deploy the repo root.
