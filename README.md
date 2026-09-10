# शास्त्रम्

A MkDocs site for Sanskrit shastra texts, forked from the साहित्यशास्त्रम्
project. See `scripts/generate_indices.py`'s module docstring for the full
build pipeline, and its "Differences from sahitya" section for what
changed and why (the short version is below).

## Building

```
pip install mkdocs mkdocs-material pyyaml mkdocs-macros-plugin
python scripts/generate_indices.py   # regenerates docs/ + mkdocs.yml
mkdocs build --strict                # or: mkdocs serve, for local preview
```

`.github/workflows/deploy.yml` does this on every push to `main`: builds
the site, deploys it to GitHub Pages, AND zips `site/` as a separate
downloadable Actions artifact (`shastra-offline`) — see "Offline use"
below.

## Site structure

Two top-level cards, configured in `scripts/site_config.yaml`:

- **अद्वैतवेदान्तः** (`advaita/`) — grouped into `prakarana/`,
  `prasthanatraya/`, `siddhigrantha/`. This is also the one section
  carrying `topics/` (see below).
- **इतरशास्त्राणि** (`itarashastra/`) — grouped into `vyakarana/`,
  `tarka/`, `yoga/`.

Add a new card by adding an entry to `content_sections:` in
`site_config.yaml` — no code changes needed as long as the directory
follows the `<dir>/<group>/<slug>/<chapter>/*.md` convention (see that
file's own header comment, and `generate_indices.py`'s module docstring,
for the full layout spec).

## What's new here vs. sahitya

- **`<topic name="..." define="?">...</topic>`** replaces both sahitya's
  section-level `topics:` frontmatter and its `<paribhasha>` tag:
  - `<topic name="शमः">...</topic>` around any paragraph registers a
    link back to that *exact* paragraph on शमः's own topic page (under
    सन्दर्भाः) — click-through lands precisely where the tag is, not
    just at the top of the section.
  - `<topic name="शमः" define="true">...</topic>` does the same, AND
    additionally adds that paragraph to a परिभाषाः table at the top of
    शमः's page — for terms multiple texts define differently (see
    `advaita/topics/shama.md`, and the three `<topic>` occurrences
    across `advaita/prakarana/vivekachudamani/01/`,
    `advaita/prasthanatraya/gita/02/`, and
    `itarashastra/yoga/yogasutra/01/` that all point at it).
  - A topic can be a single `topics/<slug>.md` file, or a whole
    `topics/<slug>/` directory of several `.md` files (each with its own
    `order:`) concatenated into one page — see
    `advaita/topics/atma-vichara/` for a worked example.
- **`<notes>...</notes>`** is shorthand for
  `<div class="gloss" data-type="notes">...</div>` — no collapsible
  behavior yet (that's a deliberately deferred follow-up).
- **No chandas/alankara glossary** — these are shastra texts, not kavya;
  `data-chandas=`/`data-alankara=`, `topics/chandas.md`/`alankara.md`,
  and the शलोकसूची's meter/figure columns are all gone. The `<div
  class="shloka">`/gloss/vada/notes machinery (verse extraction, hideable
  commentary types, `default_class:`, etc.) is otherwise unchanged from
  sahitya — see `scripts/gloss_types.yaml`.
- **Two (or more) cards**, each with its own `text_groups:` — see
  `site_config.yaml` above.

## Offline use

`mkdocs.yml` is built with `use_directory_urls: false` (see
`build_mkdocs_static` in `generate_indices.py`), so every page is a
plain `foo.html` rather than a clean `foo/` URL — that means a
downloaded, unzipped copy of `site/` can be opened directly from a
phone's or tablet's file browser (double-click `index.html`) with no web
server and no internet connection; every internal link is a relative
file path. `navigation.instant` is off for the same reason (it needs a
real HTTP server to work).

To get that zip: open the repo's **Actions** tab → the latest (or a
manually triggered) "Deploy शास्त्रम् site" run → download the
**shastra-offline** artifact from the run's summary page, unzip it
anywhere, and open `index.html`.

A rough sense of scale: at the "a few `.md` files per chapter" density
mentioned when this was scoped (not one file per verse), a few thousand
source files is well within what a fully static site like this handles
fine even on a tablet — each page is small and independent, so per-page
load is unaffected by total site size. The one thing that *does* grow
with page count is the client-side search index MkDocs Material builds
(`plugins: - search`); if that ever gets sluggish once the corpus is
large, it's a config knob to revisit (e.g. narrowing what gets indexed),
not a structural rewrite.
