#!/usr/bin/env python3
"""
generate_indices.py
====================

Pre-build generation script for the शास्त्रम् MkDocs site (a sibling of the
साहित्यशास्त्रम् project this script was forked from — see "Differences
from sahitya" below for what changed and why).

What it does, in order:

1.  Reads scripts/site_config.yaml, which declares the site's top-level
    content sections ("cards" — e.g. advaita vedanta texts, other
    shastras) purely as data — see that file's header comment for the
    schema. Adding a new section that follows the
    `<dir>/<group>/<slug>/...` convention needs no code changes here.
2.  Reads `meta.yaml`/`meta.yml` for every text under each configured
    section's text-group directories, and (optionally) for every
    individual chapter directory (`chapter_name`).
3.  Reads every topic page under the topics-carrying section's `topics/`
    folder. Every topic now lives inside a category directory —
    `topics/<category>/<slug>.md`, or `topics/<category>/<slug>/` for a
    multi-file topic (multiple `.md` files, each in its own `order:`
    frontmatter order, concatenated into one logical topic — see
    `discover_ref_pages`). `topics/<category>/meta.yaml` gives that
    category its own `title:` (and `order:`, and `expanded_by_default:`
    — see build_home_page/build_domain_index_page/build_topics_index_page,
    all three of which list topics grouped by category, collapsed behind
    a `<details>` for any category with `expanded_by_default: false`). A
    topic's own Devanagari `title:` (from its .md frontmatter, or its
    directory's meta.yaml) is the canonical key that `<topic
    name="...">` tags elsewhere point back to — unique across the whole
    site, not just within its category.
4.  Walks every chapter directory under each text and renders it per that
    chapter's own `chapter_display_style:` (meta.yaml; default
    `full_chapter`) — either concatenating its section files into a
    single generated chapter page (`full_chapter`), or generating a
    landing/TOC page plus one separate output page per section
    (`sections`; see `render_chapter_sections`). Either way, along the
    way it:
      - expands `<notes>...</notes>` shorthand into
        `<div class="gloss" data-type="notes">...</div>` before anything
        else touches the body (see `expand_notes_shorthand`);
      - scans for `<topic name="..." define="?" context="?">...</topic>`
        tags (see `process_topic_tags`). Every occurrence:
          - registers a back-reference on that topic's page (a link back
            to this exact paragraph, via a per-occurrence anchor) —
            listed under सन्दर्भाः, labeled with the tag's own inner text
            by default, or with `context="..."` instead when given (for
            occurrences where the paragraph itself doesn't make a good
            standalone link label — e.g. a broad "this whole
            discussion" reference rather than one quotable line);
          - adds a small forward jump-link right after itself, to that
            topic's own page — so a reader can jump text→topic and
            topic→text in either direction from wherever they are;
          - additionally, when `define="<term>"` is given, registers
            the wrapped text as a definition of THAT TERM (not
            necessarily the same string as the topic's own name — one
            topic page can collect definitions of several distinct
            related terms, e.g. topic "साधनचतुष्टयम्" collecting
            separate definitions of "शमः", "दमः", ... — see
            `build_topic_definitions_table`), collected onto the named
            topic's own page as a संज्ञा/परिभाषा/मूलम् definitions table
            (this is the mechanism sahitya's now-removed `<paribhasha>`
            tag used to provide as a separate global page);
      - extracts every `<div class="shloka" ...>` (with `data-type=`,
        optional `highlight="true"`) and builds a per-chapter Shloka
        Table (a plain list of verses — the meter/alankara columns that
        sahitya's version showed are gone; see "Differences" below).
        Extraction walks a real nesting-aware parse tree (see
        `parse_divs` below) rather than scanning with a flat regex, so it
        works correctly no matter how deeply a shloka sits inside
        wrapper divs.
5.  Writes the generated chapter pages, per-text landing pages (sorted by
    `order:` in meta.yaml, falling back to title), and topic pages
    (each with its auto-generated परिभाषाः table, if any `define="true"`
    occurrences were found, and सन्दर्भाः back-link list) into `docs/`
    (source files are never modified).
6.  Writes `docs/index.md` (home page, one card per content section).
7.  Writes `mkdocs.yml`, including an auto-generated `nav:` block.

This script is idempotent: it always starts by deleting only the generated
output directory contents for each configured section, `docs/assets/`
(a fresh mirror of `assets/` — see below), `docs/index.md`, and
`mkdocs.yml` — never the hand-maintained `docs/stylesheets/`,
`docs/javascripts/`, or any source directory.

Requires: PyYAML only. (sahitya's copy of this script also required
beautifulsoup4, for chandas/alankara glossary `<table>` parsing — that
mechanism doesn't exist here, so the dependency is gone too.)

Differences from sahitya (see shastra-init-request.md in the repo root
for the full discussion this came out of):
  - Two (or more) top-level "cards", each with its own `text_groups:` —
    no single implicit `shastra/texts/` path anymore; every section uses
    `text_groups:` explicitly (see site_config.yaml).
  - No chandas/alankara meter glossary: `data-chandas=`/`data-alankara=`
    shloka attributes, `topics/chandas.md`/`alankara.md`, and the
    छन्दः/अलङ्काराः columns on the Shloka Table are all gone. These texts
    aren't kavya — meter/figure tracking doesn't apply.
  - No section-level `topics:` frontmatter (the old "सम्बद्धाः विषयाः,
    fully-inferred-from-frontmatter" mechanism) and no `<paribhasha>` tag
    — both replaced by the single `<topic name="..." define="?"
    context="?">` tag (see process_topic_tags), which does both jobs
    (plain back-reference, and — with define="<term>" — a
    paribhasha-style definition entry) at exact-paragraph granularity,
    not just per-section, and also drops a forward jump-link to the
    topic's own page right where it's used.
  - Topics are organized into categories — `topics/<category>/<slug>.md`
    (or `topics/<category>/<slug>/` for a multi-file topic) — each
    category with its own `topics/<category>/meta.yaml` (title/order/
    expanded_by_default). Every page that lists topics shows this
    category grouping, collapsing a category behind a `<details>` when
    its `expanded_by_default: false`.
  - `<notes>...</notes>` is shorthand for
    `<div class="gloss" data-type="notes">...</div>` (see
    expand_notes_shorthand) — no collapsible/`<details>` behavior yet,
    that's left for a later pass.
  - mkdocs.yml is configured for offline/local browsing (clean URLs off,
    instant-loading off — see build_mkdocs_static) so a downloaded zip of
    `site/` can be opened directly from a phone/tablet's file browser
    with no web server; see .github/workflows/deploy.yml for the zip
    artifact this produces on every build.

Layout expected on disk:

    <section>/                 e.g. advaita/, itarashastra/
        meta.yaml               (optional, currently unused by the script
                                  itself — reserved for future section-level
                                  notes; section-level *display* config
                                  lives in site_config.yaml instead)
        <group>/                one directory per site_config.yaml text_groups: entry
            <slug>/
                meta.yaml        title, author, default_shloka_type, default_class, order, ...
                <chapter>/
                    meta.yaml    (optional) chapter_name
                    *.md         section files, concatenated in numeric order
        topics/                 (optional, only on the section with
                                  `topics: true` in site_config.yaml)
            <category>/
                meta.yaml         title, order, expanded_by_default (default true — see
                                  build_home_page/build_domain_index_page/
                                  build_topics_index_page)
                <slug>.md         a single-file topic, OR:
                <slug>/            a multi-file topic directory:
                    meta.yaml       title, order (this topic's position among others IN ITS CATEGORY)
                    *.md            concatenated in each file's own order: (fallback: filename)

    assets/                      (optional, repo root — NOT inside any
                                  section) — static assets (audio/*.mp3
                                  today, anything else later) referenced
                                  by an explicit link/embed from some
                                  page's content, e.g.
                                  `<audio src="../../assets/audio/foo.mp3">`.
                                  Mirrored verbatim into docs/assets/
                                  on every build (see copy_assets());
                                  never parsed as Markdown, never linked
                                  from nav or the home page on its own.
"""

from __future__ import annotations

import html
import posixpath
import re
import shutil
import sys
from itertools import groupby
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

SCRIPTS_DIR = Path(__file__).resolve().parent
SITE_CONFIG_PATH = SCRIPTS_DIR / "site_config.yaml"
GLOSS_TYPES_CONFIG_PATH = SCRIPTS_DIR / "gloss_types.yaml"

META_FILENAMES = ("meta.yaml", "meta.yml")

WARNINGS: list[str] = []


def warn(msg: str) -> None:
    WARNINGS.append(msg)
    print(f"WARNING: {msg}", file=sys.stderr)


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


SITE_CONFIG = load_yaml(SITE_CONFIG_PATH)
if not SITE_CONFIG.get("content_sections"):
    warn(f"{SITE_CONFIG_PATH} has no content_sections: — nothing will be built")

# UI strings shown by the generated site that aren't tied to any one
# section/text (those go through SectionConfig/Text instead) — see
# site_config.yaml's labels: block for the full list and what each
# defaults to. Every default below matches the literal string it used to
# be, so an existing site_config.yaml without one of these keys yet
# still builds identically.
_RAW_LABELS = SITE_CONFIG.get("labels", {}) or {}


def site_label(key: str, default: str) -> str:
    return str(_RAW_LABELS.get(key, "")).strip() or default


class TextGroup:
    """One directory of texts within a section, and the H2 heading it
    renders under on the home page card / section index page / nav (see
    SectionConfig.text_groups). Pure categorization — a text's group has
    no effect on how its content is processed, only where it lives on
    disk (<section>/<group.dir_name>/<slug>/...) and which heading it's
    listed under."""

    def __init__(self, dir_name: str, h2_label: str):
        self.dir_name = dir_name
        self.h2_label = h2_label


class SectionConfig:
    """One entry of site_config.yaml's content_sections: list."""

    def __init__(self, raw: dict):
        self.dir = str(raw.get("dir", "")).strip()
        self.h1_label = str(raw.get("h1_label", self.dir)).strip()
        self.h2_topics_label = str(raw.get("h2_topics_label", "विषयाः")).strip()
        self.default_chapter_word = (
            str(raw.get("default_chapter_word", "")).strip()
            or str(SITE_CONFIG.get("default_chapter_word", "अध्यायः")).strip()
        )
        self.has_topics = bool(raw.get("topics", False))
        # text_groups: lets a section split its texts across MULTIPLE
        # directories (e.g. kavya/gadya/, kavya/stotra/, kavya/padya/
        # instead of a single kavya/texts/), each becoming its own H2
        # heading — purely a categorization + home-page/nav display
        # choice, zero effect on how a text's content is processed. A
        # section that doesn't set text_groups: (e.g. shastra, which
        # only ever needs one grouping) falls back to the single
        # implicit group this always used: <dir>/texts/, headed
        # h2_text_label (also configurable, unchanged from before).
        raw_groups = raw.get("text_groups")
        if isinstance(raw_groups, list) and raw_groups:
            self.text_groups = [
                TextGroup(str(g.get("dir", "")).strip(), str(g.get("h2_label", "")).strip())
                for g in raw_groups if isinstance(g, dict) and str(g.get("dir", "")).strip()
            ]
        else:
            self.text_groups = [
                TextGroup("texts", str(raw.get("h2_text_label", "ग्रन्थाः")).strip())
            ]

    @property
    def src(self) -> Path:
        return ROOT / self.dir

    @property
    def out_dir(self) -> Path:
        return DOCS / self.dir

    @property
    def topics_src(self) -> Path:
        return self.src / "topics"


SECTIONS: list[SectionConfig] = [
    SectionConfig(raw) for raw in (SITE_CONFIG.get("content_sections") or [])
]
TOPICS_SECTION = next((s for s in SECTIONS if s.has_topics), None)


def group_texts(section: SectionConfig, texts: list["Text"]) -> list[tuple[TextGroup, list["Text"]]]:
    """Buckets `texts` (a flat list — see discover_texts) back into
    section.text_groups order, dropping any group with zero texts (no
    empty heading shown for a group nobody's written anything in yet)."""
    by_dir: dict[str, list["Text"]] = {}
    for t in texts:
        by_dir.setdefault(t.group.dir_name, []).append(t)
    return [(g, by_dir[g.dir_name]) for g in section.text_groups if g.dir_name in by_dir]


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---[ \t]*\n(.*?\n)---[ \t]*\n?", re.DOTALL)


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_text). Tolerant of missing frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        data = yaml.safe_load(m.group(1)) or {}
        if not isinstance(data, dict):
            warn(f"frontmatter did not parse to a mapping: {m.group(1)[:60]!r}")
            data = {}
    except yaml.YAMLError as e:
        warn(f"could not parse YAML frontmatter ({e})")
        data = {}
    return data, text[m.end():]


def as_list(value) -> list[str]:
    """Normalize a frontmatter value that may be a scalar, list, or None."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    v = str(value).strip()
    return [v] if v else []


def read_meta(text_dir: Path) -> dict:
    for name in META_FILENAMES:
        p = text_dir / name
        if p.exists():
            try:
                return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as e:
                warn(f"could not parse {p} ({e})")
                return {}
    return {}


def find_meta_file(text_dir: Path) -> Path | None:
    for name in META_FILENAMES:
        p = text_dir / name
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# Chapter directories and section (.md) filenames both sort by plain
# alphabetical order of their name/stem. Authors are responsible for
# zero-padding numeric prefixes so that plain string sort gives the
# intended order (e.g. "01".."09".."15", not "1", "10", "11", ..., "2").
# This also means an author can always insert a new file between two
# existing ones — e.g. between "prefix-01.md" and "prefix-02.md" — by
# adding "prefix-01-01.md" / "prefix-01-02.md", which alphabetically land
# exactly in between, in that order.
# ---------------------------------------------------------------------------


def rel_link(from_rel_file: str, to_rel_file: str) -> str:
    """Relative link from the page at `from_rel_file` to `to_rel_file`,
    both given as paths relative to the docs root. Real relative-path math
    (not same-depth assumptions), needed once pages live at varying depths
    (e.g. the glossary detail pages).

    NOTE: only works inside genuine Markdown link syntax `[text](...)`
    (MkDocs rewrites those into the clean-URL form for you) — NOT inside
    literal HTML `<a href="...">`, which MkDocs never touches. Use
    `raw_html_href()` for that instead."""
    from_dir = posixpath.dirname(from_rel_file)
    return posixpath.relpath(to_rel_file, start=from_dir or ".")


def raw_html_href(from_rel_md_file: str, to_rel_md_file: str) -> str:
    """Relative href to use inside literal HTML (raw <a href="...">), which
    MkDocs never rewrites — unlike Markdown-syntax links, this must already
    point at the final output file. With `use_directory_urls: false` (see
    build_mkdocs_static — set for offline/local file:// browsing), MkDocs
    serves every docs/**/*.md file at that exact same path with `.md`
    replaced by `.html` — no clean-URL "directory" indirection — so this
    is just that same replacement, made relative to `from_rel_md_file`'s
    own directory."""
    from_dir = posixpath.dirname(from_rel_md_file)
    to_html = to_rel_md_file[:-3] + ".html" if to_rel_md_file.endswith(".md") else to_rel_md_file
    return posixpath.relpath(to_html, start=from_dir or ".")


# ---------------------------------------------------------------------------
# Nesting-aware <div class="..."> parser
# ---------------------------------------------------------------------------
#
# The old version of this script found shloka/commentary divs with a flat
# regex: `<div class="...">(.*?)</div>`. Non-greedy `.*?` stops at the
# FIRST `</div>` it sees — which silently mispairs open/close tags the
# moment a div contains another div before its own true closing tag (e.g.
# a kavya-play's <div class="dialog-block"> wrapping a <div class="shloka">,
# or — found live in shastra/texts/sd/05/sd05-01.md — a run of
# <div class="karika">...) blocks whose authors didn't close each one
# before the next opens). That mispairing is exactly what caused the
# श्लोकसूची to sometimes silently drop verses.
#
# parse_divs() below replaces that with a real (if lightweight) stack-based
# parser: every open/close <div> tag is tracked on a stack, so nesting is
# resolved correctly regardless of depth. It also recovers from the
# "forgot to close it" pattern above with the same rule browsers use for
# things like unclosed <p>: a new div reopening the SAME class while the
# previous one of that class is still open on top of the stack implicitly
# closes the previous one first, rather than nesting under it.
#
# Callers get back a tree of DivNode objects with exact character offsets
# into the original string — so callers can do precise, minimal text
# splices (insert an anchor, replace one div's span, remove a span
# entirely for repositioning) without ever re-serializing text they didn't
# touch. This is important: these files are hand-authored Devanagari
# Markdown, and round-tripping them through an HTML serializer risks
# subtly rewriting whitespace/entities in content the script has no
# business touching.

DIV_OPEN_RE = re.compile(r'<div\b((?:[^>"]|"[^"]*")*)>')
DIV_CLOSE_RE = re.compile(r'</div\s*>')
CLASS_ATTR_RE = re.compile(r'class\s*=\s*"([^"]*)"')


class DivNode:
    __slots__ = (
        "cls", "classes", "base_cls", "attrs_str",
        "start", "tag_end", "inner_end", "end", "children",
    )

    def __init__(self, cls: str, attrs_str: str, start: int, tag_end: int):
        self.cls = cls
        self.classes = cls.split()
        self.base_cls = self.classes[0].lower() if self.classes else ""
        self.attrs_str = attrs_str
        self.start = start          # index of '<' of the opening tag
        self.tag_end = tag_end      # index right after the opening tag's '>'
        self.inner_end: int | None = None   # index of '<' of the matching close (or end-of-text)
        self.end: int | None = None         # index right after the matching close (or == inner_end)
        self.children: list["DivNode"] = []

    def has_class(self, name: str) -> bool:
        return name in self.classes


def parse_divs(text: str) -> list[DivNode]:
    """Parse every <div class="..."> ... </div> in `text` into a forest of
    DivNode, tolerant of (a) real nesting to any depth and (b) a div of
    some class left unclosed right before a sibling *of the same class*
    reopens (see module-level comment above)."""
    tokens: list[tuple[int, int, str, str | None]] = []
    for m in DIV_OPEN_RE.finditer(text):
        tokens.append((m.start(), m.end(), "open", m.group(1)))
    for m in DIV_CLOSE_RE.finditer(text):
        tokens.append((m.start(), m.end(), "close", None))
    tokens.sort(key=lambda t: t[0])

    root: list[DivNode] = []
    stack: list[DivNode] = []

    def finish(node: DivNode, inner_end: int, end: int) -> None:
        node.inner_end = inner_end
        node.end = end
        (stack[-1].children if stack else root).append(node)

    for start, tag_end, kind, attrs_str in tokens:
        if kind == "open":
            cls_m = CLASS_ATTR_RE.search(attrs_str or "")
            cls = cls_m.group(1).strip() if cls_m else ""
            node = DivNode(cls, attrs_str or "", start, tag_end)
            if stack and stack[-1].base_cls == node.base_cls and node.base_cls:
                # implicit close of the previous same-class div right here
                prev = stack.pop()
                finish(prev, start, start)
            stack.append(node)
        else:  # close
            if not stack:
                continue  # stray </div> with nothing open — ignore
            node = stack.pop()
            finish(node, start, tag_end)

    # anything still open at EOF: close it at end-of-text
    while stack:
        node = stack.pop()
        finish(node, len(text), len(text))

    return root


def apply_splices(text: str, splices: list[tuple[int, int, str]]) -> str:
    """Apply a list of non-overlapping (start, end, replacement) spans to
    `text` in one pass. (end == start) means a pure insertion at that
    position with nothing removed."""
    splices = sorted(splices, key=lambda s: s[0])
    out = []
    pos = 0
    for start, end, repl in splices:
        if start < pos:
            raise ValueError(f"overlapping splice at {start} (previous ended at {pos})")
        out.append(text[pos:start])
        out.append(repl)
        pos = end
    out.append(text[pos:])
    return "".join(out)


ATTR_RE = re.compile(r'([a-zA-Z\-]+)\s*=\s*"([^"]*)"')


def parse_attrs(attr_str: str) -> dict:
    return {m.group(1): m.group(2) for m in ATTR_RE.finditer(attr_str)}


# ---------------------------------------------------------------------------
# Discovery: texts (<section>/texts/<slug>)
# ---------------------------------------------------------------------------

def title_order_sort_key(frontmatter: dict, title: str, source_for_warning: object = "") -> tuple:
    """Shared sort key for anything with an optional numeric `order:` field
    (texts on a section's landing page, topics under विषयाः, ...) — explicit
    `order:` takes priority (ascending), with unordered entries (or a
    non-numeric order:) falling back to alphabetical-by-title, sorted after
    every explicitly ordered one."""
    order = frontmatter.get("order")
    try:
        order = float(order) if order is not None else float("inf")
    except (TypeError, ValueError):
        warn(f"{source_for_warning}: 'order: {order!r}' isn't a number — ignoring it, sorting by title instead")
        order = float("inf")
    return (order, title)



class Text:
    def __init__(self, slug: str, directory: Path, meta: dict, section: SectionConfig, group: TextGroup):
        self.slug = slug
        self.dir = directory
        self.meta = meta
        self.section = section
        self.group = group
        self.title = str(meta.get("title", slug)).strip()
        self.author = str(meta.get("author", "")).strip()
        self.default_shloka_type = str(meta.get("default_shloka_type", "")).strip()
        self.default_class = str(meta.get("default_class", "")).strip()
        # This book's own gloss data-types — either brand new ones scoped
        # only to this book, or full overrides of a site-wide
        # gloss_types.yaml entry (same schema as that file's `types:`
        # list; a book's own entry always wins entirely over the
        # site-wide one on a data_type collision, not a field-by-field
        # merge). To share a custom type across MULTIPLE books instead of
        # repeating it in each one's meta.yaml, add it to the site-wide
        # gloss_types.yaml directly — that's already global to every book.
        raw_custom_types = meta.get("gloss_types") or []
        book_types: dict[str, dict] = {}
        if isinstance(raw_custom_types, list):
            for entry in raw_custom_types:
                if not isinstance(entry, dict):
                    continue
                data_type = str(entry.get("data_type", "")).strip().lower()
                if not data_type:
                    continue
                validate_gloss_type_entry(entry, data_type, SUPPORTED_CSS_STYLES, f"{directory}/meta.yaml")
                book_types[data_type] = entry
        # this book's fully-resolved data_type -> config lookup: every
        # site-wide default, with this book's own additions/overrides
        # layered on top. Everything downstream (process_content_sections,
        # extract_shlokas' default_shloka_type resolution, ...) reads
        # THIS, never the module-level GLOSS_TYPES_BY_KEY directly.
        self.effective_gloss_types: dict[str, dict] = {**GLOSS_TYPES_BY_KEY, **book_types}
        # gloss_labels: is the lighter-weight sibling of gloss_types:
        # above — only ever overrides the `label` field of an otherwise
        # unchanged (site-wide or this book's own) type, e.g. some books
        # call claim/refute something other than the site-wide पक्षः/
        # निरासः default. Applied AFTER gloss_types: above, so it always
        # wins even over this book's own custom entry's label.
        raw_labels = meta.get("gloss_labels") or {}
        if isinstance(raw_labels, dict):
            for k, v in raw_labels.items():
                key = str(k).strip().lower()
                if key not in self.effective_gloss_types:
                    warn(f"{directory}/meta.yaml: gloss_labels: references unknown gloss type '{key}' "
                         f"(not in {GLOSS_TYPES_CONFIG_PATH.name} or this book's own gloss_types:)")
                    continue
                # copy-on-write: never mutate a shared dict (GLOSS_TYPES_BY_KEY's
                # values are shared across every Text that doesn't override them)
                self.effective_gloss_types[key] = {**self.effective_gloss_types[key], "label": str(v).strip()}
        # whether a shloka's pada line breaks get put back as explicit
        # <br /> tags (see extract_shlokas / docs/stylesheets/custom.css
        # for why .shloka can't just rely on CSS white-space for this
        # anymore). This text's own meta.yaml wins if it sets the key at
        # all (True OR False); otherwise falls back to the site-wide
        # default in site_config.yaml.
        self.maintain_shloka_linebreak: bool = bool(
            meta["maintain_shloka_linebreak"] if "maintain_shloka_linebreak" in meta
            else SITE_CONFIG.get("maintain_shloka_linebreak", False)
        )
        self.chapters: list["Chapter"] = []

    @property
    def sort_key(self):
        return title_order_sort_key(self.meta, self.title, self.dir)

    @property
    def out_dir(self) -> Path:
        return self.section.out_dir / self.group.dir_name / self.slug

    @property
    def rel_out_dir(self) -> str:
        return f"{self.section.dir}/{self.group.dir_name}/{self.slug}"


class Chapter:
    def __init__(self, text: Text, slug: str, sections: list[Path], meta: dict | None = None):
        self.text = text
        self.slug = slug
        self.sections = sections  # list of source .md Paths, in order
        self.meta = meta or {}

    @property
    def display_style(self) -> str:
        """`chapter_display_style:` in this chapter's own meta.yaml —
        "full_chapter" (default: every section concatenated onto one
        page, exactly as before) or "sections" (a landing/TOC page for
        the chapter plus one separate output page per section — see
        render_chapter_sections). Unrecognized values fall back to
        "full_chapter" with a warning."""
        style = str(self.meta.get("chapter_display_style", "")).strip() or "full_chapter"
        if style not in ("full_chapter", "sections"):
            warn(
                f"{self.text.dir}/{self.slug}: unknown chapter_display_style '{style}' "
                f"— expected 'full_chapter' or 'sections' — falling back to 'full_chapter'"
            )
            return "full_chapter"
        return style

    @property
    def out_file(self) -> Path:
        return DOCS / self.rel_out_file

    @property
    def rel_out_file(self) -> str:
        """The chapter's own "entry" page — the single rendered page in
        full_chapter mode, or the landing/TOC page in sections mode. This
        is what every OTHER page links to when it means "this chapter"
        (text index page, nav, the text-wide prev/next-chapter links) —
        never an individual section page, even in sections mode."""
        if self.display_style == "sections":
            return f"{self.text.rel_out_dir}/{self.slug}/index.md"
        return f"{self.text.rel_out_dir}/{self.slug}.md"

    def section_rel_out_file(self, section: Path) -> str:
        """Only meaningful in sections mode — the individual output page
        for one section (.md file) of this chapter."""
        return f"{self.text.rel_out_dir}/{self.slug}/{section.stem}.md"

    @property
    def full_chapter_label(self) -> str | None:
        """Only relevant in `chapter_display_style: sections` —
        `full_chapter_label:` in this chapter's own meta.yaml. If set, an
        extra "whole chapter on one page" reading view is generated
        alongside the per-section pages (see render_chapter_sections) and
        listed first on the chapter's landing/TOC page, under this exact
        text. Unset/blank (the default) means no such page is generated —
        sections mode shows only the per-section list, as before."""
        label = self.meta.get("full_chapter_label")
        return str(label).strip() or None if label else None

    @property
    def full_chapter_rel_out_file(self) -> str:
        """Only meaningful when full_chapter_label is set — the combined
        reading-view page generated alongside the per-section pages."""
        return f"{self.text.rel_out_dir}/{self.slug}/full.md"

    @property
    def default_shloka_type(self) -> str:
        """Value that fills in `data-type=` on a bare `<div class="shloka">`
        (one that doesn't already carry its own data-type=) — the
        chapter's own meta.yaml wins over the text's. This ONLY ever
        touches already-explicit shloka divs; see default_class for
        naked/undived text."""
        return str(self.meta.get("default_shloka_type", "")).strip() or self.text.default_shloka_type

    @property
    def default_class(self) -> str:
        """Class that any text NOT inside some `<div class="...">` (at
        any nesting level) is wrapped in, as if the author had written
        that div themselves — the chapter's own meta.yaml wins over the
        text's. Unset means naked text stays plain Markdown, unchanged
        (the default)."""
        return str(self.meta.get("default_class", "")).strip() or self.text.default_class

    @property
    def nav_label(self) -> str:
        if self.meta.get("chapter_name"):
            return str(self.meta["chapter_name"]).strip()

        try:
            n = int(self.slug)
            word = (
                str(self.text.meta.get("chapter_type", "")).strip()
                or self.text.section.default_chapter_word
            )
            return f"{word} {n}"
        except ValueError:
            return self.slug


def discover_texts_in_group(section: SectionConfig, group: TextGroup) -> list[Text]:
    texts = []
    src_root = section.src / group.dir_name
    if not src_root.exists():
        warn(f"{src_root} does not exist — no texts found for section '{section.dir}' group '{group.dir_name}'")
        return texts
    for d in sorted(p for p in src_root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        meta_path = find_meta_file(d)
        if not meta_path:
            warn(f"{d} has no meta.yaml/meta.yml — skipping this text")
            continue
        meta = read_meta(d)
        if meta.get("ignore"):
            print(f"Skipping {d} (ignore: true in meta.yaml)")
            continue
        if "title" not in meta:
            warn(f"{meta_path} has no 'title' — skipping this text")
            continue
        texts.append(Text(d.name, d, meta, section, group))
    texts.sort(key=lambda t: t.sort_key)
    return texts


def discover_texts(section: SectionConfig) -> list[Text]:
    """Flat list across every one of this section's text_groups (see
    SectionConfig.text_groups) — groups in their site_config.yaml
    declaration order, texts sorted within each group. Each Text
    remembers which group it came from (Text.group), used for its own
    output path (Text.rel_out_dir) and for re-grouping by heading on the
    home page / section index / nav (see group_texts)."""
    texts: list[Text] = []
    for group in section.text_groups:
        texts.extend(discover_texts_in_group(section, group))
    return texts


def discover_chapters(text: Text) -> list[Chapter]:
    """A chapter is either a subdirectory of section files, or (if no
    directory of the same name exists) a single top-level .md file. A
    top-level .md file that duplicates a chapter directory's name is a
    leftover/error and is skipped in favour of the directory."""
    chapters: list[Chapter] = []
    dir_children = {d.name: d for d in text.dir.iterdir() if d.is_dir() and not d.name.startswith(".")}

    for name, d in dir_children.items():
        sections = []
        for f in sorted(d.glob("*.md"), key=lambda f: f.stem):
            fm, _ = split_frontmatter(f.read_text(encoding="utf-8"))
            if fm.get("ignore"):
                print(f"Skipping {f} (ignore: true in frontmatter)")
                continue
            sections.append(f)
        if not sections:
            warn(f"chapter directory {d} contains no .md sections — skipping")
            continue
        chapter_meta = read_meta(d)  # optional meta.yaml/meta.yml inside the chapter dir (chapter_name, default_shloka_type, default_class, ...)
        chapters.append(Chapter(text, name, sections, chapter_meta))

    for f in text.dir.glob("*.md"):
        if f.stem in dir_children:
            warn(
                f"{f} duplicates chapter directory '{f.stem}/' in the same text "
                f"and will be IGNORED — the directory's sections are used instead. "
                f"This file should be removed from the source."
            )
            continue
        chapters.append(Chapter(text, f.stem, [f]))

    chapters.sort(key=lambda c: c.slug)
    return chapters


# ---------------------------------------------------------------------------
# Discovery: reference pages (topics / chandas / alankara) — always live
# under the one section configured with `topics: true` in site_config.yaml.
# ---------------------------------------------------------------------------

class RefPage:
    def __init__(self, kind: str, slug: str, path: Path, frontmatter: dict, body: str, rel_dir: str):
        self.kind = kind  # "topic"
        self.slug = slug
        self.path = path
        self.frontmatter = frontmatter
        self.body = body
        self.rel_dir = rel_dir  # e.g. "shastra/topics"
        self.title = str(frontmatter.get("title", slug)).strip()
        self.references: list["Reference"] = []  # filled in during the scan
        self.category: "TopicCategory | None" = None  # filled in by main(), after discover_topic_categories

    @property
    def sort_key(self):
        return title_order_sort_key(self.frontmatter, self.title, self.path)

    @property
    def rel_out_file(self) -> str:
        return f"{self.rel_dir}/{self.slug}.md"

    @property
    def out_file(self) -> Path:
        return DOCS / self.rel_out_file


class Reference:
    """One occurrence of a topic/meter/alankara tag inside a chapter's
    rendered output. `page_rel_out_file` is the actual physical page this
    occurrence lives on and what back-links must point at — this is
    `chapter.rel_out_file` for a full_chapter-mode chapter, but an
    individual section's own page in sections mode (see
    Chapter.section_rel_out_file), since chapter.rel_out_file there is
    just the chapter's landing/TOC page, which carries no content of its
    own. `section_title` is set (sections mode only) so back-link labels
    can name the specific section, not just the chapter."""

    def __init__(
        self, title_text: str, chapter: Chapter, anchor: str, preview: str,
        page_rel_out_file: str | None = None, section_title: str | None = None,
    ):
        self.title_text = title_text
        self.chapter = chapter
        self.anchor = anchor
        self.preview = preview
        self.page_rel_out_file = page_rel_out_file or chapter.rel_out_file
        self.section_title = section_title

    @property
    def label(self) -> str:
        base = f"{self.chapter.text.title} — {self.chapter.nav_label}"
        return f"{base} — {self.section_title}" if self.section_title else base


class TopicCategory:
    """One `topics/<category>/` directory — pure categorization + display
    grouping for topics, the same role TextGroup plays for texts, except
    (unlike TextGroup, which is declared centrally in site_config.yaml)
    a topic category is discovered from disk, one per `topics/*/`
    subdirectory with its own meta.yaml — categorizing TOPICS is a
    content-authoring decision (which topics exist and how they cluster
    changes as the corpus grows), not a site-structure one."""

    def __init__(self, slug: str, meta: dict, rel_dir: str, source_for_warning: object):
        self.slug = slug
        self.meta = meta
        self.rel_dir = rel_dir  # e.g. "advaita/topics/sadhana"
        self.title = str(meta.get("title", slug)).strip()
        self._source = source_for_warning
        self.topics: list["RefPage"] = []  # filled in by main(), sorted

    @property
    def expanded_by_default(self) -> bool:
        # Absent => true (today's behavior: every topic always fully
        # listed) — this is opt-IN collapsing, only for categories that
        # ask for it (typically ones with many topics).
        return bool(self.meta.get("expanded_by_default", True))

    @property
    def sort_key(self):
        return title_order_sort_key(self.meta, self.title, self._source)


def discover_topic_categories(topics_src: Path, topics_rel_dir: str) -> list[TopicCategory]:
    """Every `topics/<category>/` subdirectory, each requiring its own
    meta.yaml with `title:`. A stray `.md` file directly under `topics/`
    (the old, pre-category layout) is warned about and skipped — every
    topic must now live inside some category directory. Categories with
    zero topics in them are dropped by main() before display, the same
    way group_texts() drops an empty TextGroup — see there."""
    categories: list[TopicCategory] = []
    if not topics_src.exists():
        return categories
    for p in sorted(topics_src.iterdir()):
        if p.name.startswith("."):
            continue
        if p.is_file():
            if p.suffix == ".md":
                warn(f"{p}: topics must now live inside a category directory "
                     f"(topics/<category>/{p.name}, with topics/<category>/meta.yaml "
                     f"giving that category a title) — this file is directly under "
                     f"topics/ and will be ignored")
            continue
        meta = read_meta(p)
        title = str(meta.get("title", "")).strip()
        if not title:
            warn(f"{p} is a topic category directory with no meta.yaml 'title:' — skipping "
                 f"(and every topic inside it)")
            continue
        categories.append(TopicCategory(p.name, meta, f"{topics_rel_dir}/{p.name}", p))
    return categories


def discover_multifile_topic(d: Path) -> tuple[dict, str]:
    """A `topics/<slug>/` directory: a complex topic authored as several
    .md files instead of one. `d/meta.yaml` carries this topic's own
    `title:` (and `order:`, for its position among OTHER topics — same
    meaning as a single-file topic's frontmatter `order:`); every child
    `*.md` inside `d` carries its OWN `order:` in its frontmatter (falling
    back to filename when absent/non-numeric — same convention as
    everywhere else, see title_order_sort_key), and all of them are
    concatenated in that order into one combined body, exactly as if
    authored as a single file — no headings/separators are injected
    between them; if the source files want section headings, they
    already have their own '#'/'##' lines."""
    meta = read_meta(d)
    parts = []
    children = sorted(
        d.glob("*.md"),
        key=lambda f: title_order_sort_key(split_frontmatter(f.read_text(encoding="utf-8"))[0], f.stem, f),
    )
    for f in children:
        fm, body = split_frontmatter(f.read_text(encoding="utf-8"))
        parts.append(body.strip())
    if not children:
        warn(f"{d} is a topic directory with no .md files inside — it will render empty")
    return meta, "\n\n".join(parts)


def discover_ref_pages(kind: str, folder: Path, rel_dir: str, exclude: set[str] = frozenset()) -> dict[str, RefPage]:
    pages: dict[str, RefPage] = {}
    if not folder.exists():
        return pages
    entries = sorted(p for p in folder.iterdir() if not p.name.startswith("."))
    for p in entries:
        if p.name in exclude:
            continue
        if p.is_dir():
            fm, body = discover_multifile_topic(p)
            f = p  # for warning messages / sort_key source
        elif p.suffix == ".md":
            text = p.read_text(encoding="utf-8")
            fm, body = split_frontmatter(text)
            f = p
        else:
            continue
        title = str(fm.get("title", "")).strip()
        if not title:
            warn(f"{f} has no 'title' in frontmatter/meta.yaml — skipping")
            continue
        if title in pages:
            warn(f"duplicate title '{title}' between {pages[title].path} and {f}")
            continue
        pages[title] = RefPage(kind, p.stem, f, fm, body, rel_dir)
    return pages


# ---------------------------------------------------------------------------
# <topic name="..." define="term" context="...">...</topic> — replaces
# BOTH sahitya mechanisms at once:
#   - the old section-level `topics:` frontmatter ("सम्बद्धाः विषयाः") —
#     here every occurrence is a precise, paragraph-level tag instead of a
#     whole-section declaration;
#   - the old `<paribhasha name="..." source="...">` tag — here
#     `define="<term>"` on a `<topic>` occurrence does the same job (a
#     definition of TERM, collected from wherever it's defined across the
#     corpus), without needing a second tag or a separate global page:
#     the definitions collect onto the NAMED topic's own page (`term`
#     doesn't have to equal `name` — several related terms can collect
#     definitions onto one shared topic page, e.g. name="साधनचतुष्टयम्"
#     define="शमः" and, elsewhere, name="साधनचतुष्टयम्" define="दमः").
#
# Every `<topic name="X">...</topic>` occurrence, define="..." or not,
# registers a Reference on topic X's own RefPage (page.references — see
# render_ref_page) — a plain "cited from here" link, same mechanism
# sahitya used for chandas/alankara/topic back-links, labeled by default
# with the tag's own inner text (or `context="..."` instead, when given
# — for occurrences that don't make a good standalone link label
# themselves). What's new here is that (a) the anchor is per-OCCURRENCE,
# not per-section — the tag is rewritten (spliced) into `<span
# id="tpN">...</span>` in place, so a reader clicking a back-link on the
# topic page lands on the exact paragraph, not just the top of the
# section/chapter it's in; (b) a small forward jump-link to that topic's
# own page is inserted right after it too, so the reverse hop (from the
# text, straight to the topic) is just as immediate; and (c) the same
# occurrence, if define="<term>", also lands in TopicDefinitions (a
# परिभाषाः-style table built once per topic — see build_topic_definitions_table).
#
# Unlike sahitya's <paribhasha>, the tag here IS rewritten/stripped from
# the output (into a `<span id="...">` plus a jump-link), since we need a
# real anchor id at the exact spot — an untouched custom element has
# nowhere to put one without either duplicating IDs or affecting layout.

TOPIC_TAG_RE = re.compile(r"<topic\b(?P<attrs>[^>]*)>(?P<inner>.*?)</topic>", re.IGNORECASE | re.DOTALL)


class TopicDefinition:
    """One `<topic name="X" define="term">...</topic>` occurrence — a
    definition of TERM (not necessarily = X — a topic page can collect
    definitions of several distinct terms; see build_topic_definitions_table)
    found in some text, to be listed on topic X's own page. `text_html` is
    already-escaped, already-`<br>`-joined inner content, safe to drop
    straight into a table cell. `page_rel_out_file`/`anchor` identify
    exactly where this occurrence lives, the same way Reference does."""

    def __init__(self, term: str, text_html: str, page_rel_out_file: str, anchor: str, label: str):
        self.term = term
        self.text_html = text_html
        self.page_rel_out_file = page_rel_out_file
        self.anchor = anchor
        self.label = label  # e.g. "गीता — अध्यायः 2", for the मूलम् column


TOPIC_JUMP_MARK = "↗"


def process_topic_tags(
    body: str, chapter: "Chapter", topics: dict[str, "RefPage"],
    definitions: dict[str, list[TopicDefinition]],
    page_rel_out_file: str, section_title: str | None, start_index: int,
    source_for_warning: object = "", primary: bool = True,
) -> tuple[str, int]:
    """Scans `body` for `<topic name="..." define="?" context="?">...</topic>`
    tags, rewriting each into `<span id="tpN">...</span>` (so the
    surrounding content displays exactly as authored, just with an anchor
    dropped at that precise spot) immediately followed by a small forward
    jump-link to that topic's own page — and, when `primary`, registering
    a Reference on the matching topic's page plus (for define="term") a
    TopicDefinition. `start_index` lets callers number tp-anchors
    contiguously across an entire page (a full_chapter-mode chapter
    concatenates every section onto one page, so ids must stay unique
    across all of them — see render_chapter_full/record_shloka_references
    for the same pattern with shloka `sN` anchors); a sections-mode
    caller instead resets this to 0 per section (each section already has
    its own page/URL). Returns (new_body, next_index).

    `context="..."`, if given, is used as-is (html-escaped) as this
    occurrence's सन्दर्भाः list label, instead of the default (the tag's
    own inner text, trimmed to a preview) — for occurrences where the
    wrapped passage itself doesn't make a good standalone link label
    (e.g. tagging a whole extended discussion rather than one quotable
    line)."""
    counter = start_index
    splices: list[tuple[int, int, str]] = []
    for m in TOPIC_TAG_RE.finditer(body):
        attrs = parse_attrs(m.group("attrs"))
        name = (attrs.get("name") or "").strip()
        inner = m.group("inner")
        if not name:
            if primary:
                warn(f"{source_for_warning}: <topic> tag with no name= attribute — leaving unlinked")
            splices.append((m.start(), m.end(), inner))
            continue
        counter += 1
        anchor = f"tp{counter}"
        known = name in topics
        if known:
            jump_href = raw_html_href(page_rel_out_file, topics[name].rel_out_file)
            jump_link = f' <a class="sv-topic-jump" href="{jump_href}" title="{html.escape(name)}">{TOPIC_JUMP_MARK}</a>'
        else:
            jump_link = ""
        splices.append((m.start(), m.end(), f'<span id="{anchor}">{inner}</span>{jump_link}'))
        if not primary:
            continue
        if not known:
            warn(f"{source_for_warning}: <topic name=\"{name}\"> references unknown topic "
                 f"(no matching topics/*/*.md or topics/*/*/meta.yaml title '{name}')")
            continue
        context = (attrs.get("context") or "").strip()
        preview = html.escape(context) if context else preview_text(inner)
        topics[name].references.append(Reference(name, chapter, anchor, preview, page_rel_out_file, section_title))
        term = (attrs.get("define") or "").strip()
        if term:
            lines = [ln.strip() for ln in re.sub(r"<[^>]+>", "", inner).splitlines() if ln.strip()]
            text_html = "<br>".join(html.escape(ln) for ln in lines)
            if not text_html:
                warn(f"{source_for_warning}: <topic name=\"{name}\" define=\"{term}\"> has no content — skipping definition")
            else:
                label = f"{chapter.text.title} — {chapter.nav_label}"
                if section_title:
                    label = f"{label} — {section_title}"
                definitions.setdefault(name, []).append(
                    TopicDefinition(term, text_html, page_rel_out_file, anchor, label)
                )
    return apply_splices(body, splices), counter


def build_topic_definitions_table(topic_rel_file: str, entries: list[TopicDefinition]) -> str:
    """The auto-generated परिभाषाः table appended to a topic's own page
    when at least one `<topic define="...">` occurrence named it —
    columns संज्ञा (the term being defined — see TopicDefinition; several
    distinct terms can collect onto the same topic page, e.g. topic
    "साधनचतुष्टयम्" collecting separate शमः/दमः/... definitions),
    परिभाषा (the definition, linked back to its exact paragraph), and
    मूलम् (which text/chapter it came from). Column headers come from
    site_config.yaml's labels: (term_column_heading/definition_column_heading/
    source_column_heading), not hardcoded here. Sorted by संज्ञा, with
    runs of the same term (expected — several texts defining the same
    term differently) sharing one vertically-centered, rowspan'd संज्ञा
    cell instead of repeating it — mirrors sahitya's old <paribhasha>
    table for exactly the same reason. Raw HTML `<table>` (rowspan can't
    be expressed in a markdown pipe-table). Returns "" if `entries` is
    empty."""
    if not entries:
        return ""
    entries_sorted = sorted(entries, key=lambda e: e.term)
    rows: list[str] = []
    for term, group_iter in groupby(entries_sorted, key=lambda e: e.term):
        group = list(group_iter)
        term_cell = f'<td rowspan="{len(group)}" class="sv-topic-term">{html.escape(term)}</td>'
        for i, e in enumerate(group):
            href = raw_html_href(topic_rel_file, e.page_rel_out_file) + f"#{e.anchor}"
            cells = [term_cell] if i == 0 else []
            cells.append(f'<td><a href="{href}">{e.text_html}</a></td>')
            cells.append(f"<td>{html.escape(e.label)}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
    thead = "<tr><th>{}</th><th>{}</th><th>{}</th></tr>".format(
        site_label("term_column_heading", "संज्ञा"),
        site_label("definition_column_heading", "परिभाषा"),
        site_label("source_column_heading", "मूलम्"),
    )
    return '<table>\n<thead>\n' + thead + "\n</thead>\n<tbody>\n" + "\n".join(rows) + "\n</tbody>\n</table>"


# ---------------------------------------------------------------------------
# <notes>...</notes> shorthand for <div class="gloss" data-type="notes">
# ---------------------------------------------------------------------------
#
# Purely textual: expanded before anything else touches a section's body
# (process_content_sections/extract_shlokas/process_topic_tags all only
# ever see the expanded form — there's no separate code path for
# <notes>). No collapsible/<details> behavior yet — that's a later pass;
# for now this is exactly equivalent to writing out the full div by hand.

NOTES_TAG_RE = re.compile(r"<notes\b[^>]*>(.*?)</notes>", re.IGNORECASE | re.DOTALL)


def expand_notes_shorthand(body: str) -> str:
    return NOTES_TAG_RE.sub(lambda m: f'<div class="gloss" data-type="notes">{m.group(1)}</div>', body)


# ---------------------------------------------------------------------------
# Shloka extraction — walks the nesting-aware div tree from parse_divs(),
# looking for every <div class="shloka" ...> at any depth.
# ---------------------------------------------------------------------------
#
# Attributes read off a shloka div (all optional):
#   data-type      one of karika / sutra / dialog / ... (free-form; CSS
#                  keys off it). Falls back to the chapter's/text's
#                  default_shloka_type (meta.yaml) when omitted — and the
#                  resolved value is written back into the OUTPUT div
#                  (never into source) so `[data-type="..."]` CSS actually
#                  has something to match even when the author never
#                  wrote data-type at all.
#   highlight="true"   optional; CSS renders a distinct highlight tint.
#                      Left exactly as authored — never rewritten.
#
# (sahitya's copy of this also read data-chandas=/data-alankara= — meter/
# figure tracking for kavya verse — dropped here; these texts aren't kavya.)

DATA_TYPE_INJECT_RE = None  # placeholder, unused — injection is done via splice, see below


def preview_text(raw: str, max_len: int = 60) -> str:
    text = raw.lstrip(">").strip()
    text = re.sub(r"<[^>]+>", "", text)  # strip tags (e.g. <paribhasha ...>) — keep their text content
    text = re.sub(r"\*\*|\*|_", "", text)
    text = re.sub(r"\s+", " ", text)
    first_line = text.split("।")[0].split("॥")[0].strip()
    if not first_line:
        first_line = text.strip()
    if len(first_line) > max_len:
        first_line = first_line[:max_len].rstrip() + "…"
    return first_line


class Shloka:
    def __init__(self, preview: str, data_type: str, highlight: bool):
        self.preview = preview
        self.data_type = data_type
        self.highlight = highlight


def inject_shloka_linebreaks(inner: str) -> str:
    """Puts each pada back on its own visual line via explicit <br />
    tags — needed because .shloka uses white-space: normal (not
    pre-line: see docs/stylesheets/custom.css for the rendering bug that
    caused), so a plain source newline would otherwise collapse to a
    single space like any other markdown text. Only called when
    maintain_shloka_linebreak is on for this text (site_config.yaml,
    overridable per-book in that text's meta.yaml)."""
    lines = [ln.strip() for ln in inner.strip("\n").split("\n") if ln.strip()]
    return "<br />\n".join(lines)


def extract_shlokas(
    body: str, default_shloka_type: str, start_index: int = 0,
    source_for_warning: object = "", maintain_linebreak: bool = False,
) -> tuple[str, list[Shloka], int]:
    """Find every <div class="shloka"> in `body` at any nesting depth,
    inject an id="..." attribute for the Shloka Table to link to (see
    below for why this is an id= on the div itself, not a separate
    anchor tag), inject a resolved data-type="..." attribute into the
    ones that didn't specify their own (from `default_shloka_type` — see
    Chapter.default_shloka_type; this ONLY ever touches an already-explicit
    <div class="shloka">, never naked text — see process_content_sections'
    `default_class` for that), and — if `maintain_linebreak` is on for
    this text — replace the shloka's own source line breaks with
    explicit <br /> tags (see inject_shloka_linebreaks). Returns
    (modified_body, [Shloka, ...], next_index).

    `start_index` lets callers number shlokas contiguously across every
    section in a chapter (ids must be chapter-unique, since all sections
    end up concatenated onto a single generated chapter page and the
    Shloka Table numbers verses chapter-wide, not per-section).
    """
    tree = parse_divs(body)
    shlokas: list[Shloka] = []
    splices: list[tuple[int, int, str]] = []
    counter = start_index

    def visit(nodes: list[DivNode]):
        nonlocal counter
        for node in nodes:
            if node.base_cls != "shloka":
                visit(node.children)  # keep looking, however deep the shloka is nested
                continue

            counter += 1
            attrs = parse_attrs(node.attrs_str)

            data_type = attrs.get("data-type", "").strip() or default_shloka_type
            highlight = attrs.get("highlight", "").strip().lower() == "true"

            inner = body[node.tag_end:node.inner_end]
            anchor = f"s{counter}"
            shlokas.append(Shloka(preview_text(inner), data_type, highlight))

            if maintain_linebreak:
                splices.append((node.tag_end, node.inner_end, inject_shloka_linebreaks(inner)))

            # id= goes directly on the shloka div, NOT a separate
            # <a id="..."></a> tag on its own line before it: a lone <a>
            # is inline HTML, so Python-Markdown wraps a line containing
            # only that in its own <p>, which then carries the theme's
            # default paragraph margin — a real, visible gap before every
            # single shloka for no reason. A div's own id= attribute is a
            # perfectly valid link target (#s1 still works identically)
            # and adds no extra element/margin at all.
            splices.append((node.tag_end - 1, node.tag_end - 1, f' id="{anchor}"'))
            if data_type and not attrs.get("data-type", "").strip():
                # inject the resolved default right before the tag's closing '>'
                splices.append((node.tag_end - 1, node.tag_end - 1, f' data-type="{data_type}"'))
            # a shloka div is a leaf for our purposes — don't recurse into it

    visit(tree)
    new_body = apply_splices(body, splices)
    return new_body, shlokas, counter


# ---------------------------------------------------------------------------
# "Labeled hideable sections" — commentary-type content blocks, driven by
# scripts/gloss_types.yaml (see that file for the full convention). Most
# of these are <div class="gloss" data-type="...">, but a data-type entry
# can instead declare class: vada (claim/refute) — see gloss_types.yaml.
# Every one of these is labeled/marked hideable in place, in exactly the
# order it was authored — content authors are responsible for the order
# they write things in; nothing here ever moves or reorders a div. Also
# tree-based, for the same reason as extract_shlokas: a commentary div
# can legitimately sit inside a structural wrapper (e.g. dialog-block),
# and a flat regex would mispair it.

GLOSS_CLASS = "gloss"  # default div class for a gloss_types.yaml entry when it doesn't set class:

# Two INDEPENDENT concerns, each its own CSS class — see gloss_types.yaml
# for the full convention:
#   TOGGLEABLE_CLASS  - this div is a member of the global Show/Hide
#                       toggle group at all (drives whether the button
#                       even appears — button shows iff >=1 div on the
#                       page carries this class — and whether the button
#                       has any effect on this div once clicked).
#   HIDDEN_INITIAL_CLASS - this div starts hidden on page load. Purely
#                       about initial display; has no bearing on whether
#                       the div is a toggle-group member. A div can be
#                       TOGGLEABLE without HIDDEN_INITIAL (visible on
#                       load, but the button can still hide it), or (in
#                       principle) HIDDEN_INITIAL without TOGGLEABLE —
#                       though nothing currently produces that combination,
#                       since a div that's permanently hidden with no way
#                       to reveal it would be pointless.
TOGGLEABLE_CLASS = "sv-toggleable"
HIDDEN_INITIAL_CLASS = "sv-hidden-default"
CSS_STYLE_CLASS_PREFIX = "sv-style-"


def load_gloss_types_yaml() -> tuple[dict, set[str]]:
    """Loads the site-wide defaults from gloss_types.yaml: the `types:`
    list (keyed by data_type) and the `supported_css_styles:` allow-list
    (see that file's header for what this is — a fixed, code-independent
    set of visual treatments defined in custom.css; this function and
    everything downstream only ever validates a css_style value against
    this list and passes the string straight through as a CSS class
    suffix — it never needs to know what any of the names actually look
    like)."""
    if not GLOSS_TYPES_CONFIG_PATH.exists():
        warn(f"{GLOSS_TYPES_CONFIG_PATH} not found — no gloss data-types will be labeled/hideable/styled")
        return {}, set()
    data = yaml.safe_load(GLOSS_TYPES_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    supported_styles = {str(s).strip() for s in data.get("supported_css_styles", []) if str(s).strip()}
    by_type: dict[str, dict] = {}
    for entry in data.get("types", []):
        data_type = str(entry.get("data_type", "")).strip().lower()
        if data_type:
            validate_gloss_type_entry(entry, data_type, supported_styles, GLOSS_TYPES_CONFIG_PATH)
            by_type[data_type] = entry
    return by_type, supported_styles


def validate_gloss_type_entry(entry: dict, data_type: str, supported_styles: set[str], source: object) -> None:
    """One-time validation at load/merge time (site-wide gloss_types.yaml
    AND any book's own meta.yaml gloss_types: list — see
    Text.__init__) rather than at every point of use, so a bad entry
    warns exactly once regardless of how many divs use that data_type."""
    css_style = str(entry.get("css_style", "")).strip()
    if not css_style:
        warn(f"{source}: gloss type '{data_type}' has no css_style: — it'll render with no distinguishing "
             f"visual treatment at all, just the shared base look")
    elif css_style not in supported_styles:
        warn(f"{source}: gloss type '{data_type}' has css_style: '{css_style}', which isn't declared in "
             f"{GLOSS_TYPES_CONFIG_PATH.name}'s supported_css_styles: (expected one of {sorted(supported_styles)}) "
             f"— it'll render with no distinguishing visual treatment at all")


GLOSS_TYPES_BY_KEY, SUPPORTED_CSS_STYLES = load_gloss_types_yaml()

TOGGLE_HIDE_RE = re.compile(r'\btoggle-hide\s*=\s*"(true|false)"', re.IGNORECASE)


def recognized_div_classes(gloss_types: dict[str, dict]) -> set[str]:
    """Every div class `gloss_types` routes some data-type through —
    "gloss" is always included (the default/implicit class), plus
    whatever other class: values (e.g. "vada") appear in it. A <div>
    whose base class isn't in this set is left alone as structural
    content."""
    return {GLOSS_CLASS} | {str(cfg.get("class", GLOSS_CLASS)).strip().lower() for cfg in gloss_types.values()}


def commentary_css_style_class(type_key: str, gloss_types: dict[str, dict]) -> str:
    """The CSS class that actually gives this div its visual look (see
    gloss_types.yaml's supported_css_styles: and custom.css's
    .sv-style-* rules) — "" if this type has no valid css_style (already
    warned about once, at load time; see validate_gloss_type_entry)."""
    cfg = gloss_types.get(type_key)
    css_style = str(cfg.get("css_style", "")).strip() if cfg else ""
    return f"{CSS_STYLE_CLASS_PREFIX}{css_style}" if css_style in SUPPORTED_CSS_STYLES else ""


def commentary_label(type_key: str, attrs: str, gloss_types: dict[str, dict]) -> str:
    cfg = gloss_types.get(type_key)
    if not cfg:
        return ""
    if cfg.get("label_from_attr"):
        return parse_attrs(attrs).get(cfg["label_from_attr"], "").strip()
    return str(cfg.get("label", "") or "").strip()


def commentary_toggleable(type_key: str, attrs: str, gloss_types: dict[str, dict]) -> bool:
    """Is this instance a member of the global Show/Hide toggle group at
    all? An explicit instance-level toggle-hide="true"/"false" always
    wins — "true" opts this one instance IN (regardless of its type's own
    hideable:), "false" opts it OUT entirely (always visible, completely
    ignoring the button — see gloss_types.yaml)."""
    m = TOGGLE_HIDE_RE.search(attrs)
    if m:
        return m.group(1).lower() == "true"
    cfg = gloss_types.get(type_key)
    return bool(cfg and cfg.get("hideable", True))


def commentary_hidden_initial(type_key: str, attrs: str, gloss_types: dict[str, dict]) -> bool:
    """Does this instance start hidden on page load? Only meaningful for
    a div that's actually toggleable (see commentary_toggleable) — this
    function doesn't check that itself, callers gate on it. An instance's
    own toggle-hide="true"/"false" always wins (and self-selects "start
    hidden" / "start visible" respectively); otherwise falls back to the
    type's own hidden_by_default in gloss_types.yaml."""
    m = TOGGLE_HIDE_RE.search(attrs)
    if m:
        return m.group(1).lower() == "true"
    cfg = gloss_types.get(type_key)
    return bool(cfg and cfg.get("hidden_by_default"))


def render_commentary_div(cls_raw: str, type_key: str, attrs: str, content: str, gloss_types: dict[str, dict]) -> str:
    label = commentary_label(type_key, attrs, gloss_types)
    classes = cls_raw.strip()
    style_class = commentary_css_style_class(type_key, gloss_types)
    if style_class:
        classes = f"{classes} {style_class}"
    toggleable = commentary_toggleable(type_key, attrs, gloss_types)
    hidden_initial = toggleable and commentary_hidden_initial(type_key, attrs, gloss_types)
    if toggleable:
        classes = f"{classes} {TOGGLEABLE_CLASS}"
        if hidden_initial:
            classes = f"{classes} {HIDDEN_INITIAL_CLASS}"
    inner = content.strip()
    rendered = f"<b>{label}</b><br>{inner}" if label else inner
    # data-type is re-emitted (data-name and any other original attribute
    # is intentionally dropped — it was only ever needed to resolve the
    # label above, at build time; CSS keys off the sv-style-* class
    # above, not data-type, so data-type here is purely informational/
    # for content authors reading the generated markdown, not load-bearing).
    type_attr = f' data-type="{type_key}"' if type_key else ""
    return f'<div class="{classes}"{type_attr}>\n\n{rendered}\n\n</div>'


def resolve_default_class(default_class: str, gloss_types: dict[str, dict]) -> tuple[str, str]:
    """`default_class` in meta.yaml names either a gloss/vada data-type
    (e.g. "vritti") or a literal structural class (e.g. "dialog-block") —
    returns (div_class_to_synthesize, type_key), so wrap_gaps can build
    the right synthetic div either way without content authors needing
    to think about the gloss/data-type split at all."""
    value = default_class.strip().lower()
    if not value:
        return "", ""
    if value in gloss_types:
        return GLOSS_CLASS, value
    return value, ""


def process_content_sections(
    body: str, default_class: str, gloss_types: dict[str, dict], source_for_warning: object = "",
) -> str:
    """Returns body with every recognized div labeled/marked hideable in
    place — order in the output always matches order in the source; there
    is no reordering/repositioning of any kind.

    `gloss_types` is this chapter's fully-resolved data_type -> config
    lookup (site-wide gloss_types.yaml, overlaid with this book's own
    meta.yaml gloss_types:/gloss_labels: — see Text.__init__ for how it's
    built). Every data-type/hideable/label/css_style decision below goes
    through this dict, never a module-level global — that's what makes a
    book able to add or override gloss types that only apply to itself.

    `default_class`, when set, makes THAT the chapter-wide default for
    content: any run of text that isn't inside some other `<div>` (at any
    nesting level) is treated exactly as if the author had written that
    div themselves — same hidden/label handling as an explicit div of
    that type, with no difference in outcome. This is what makes e.g.
    `default_class: vritti` mean "the whole chapter is वृत्ति prose by
    default; only explicitly-tagged blocks (shloka/karika, other gloss
    data-types, ...) are anything else" — matching how these texts
    actually alternate root-verse and prose, without needing a
    `<div class="gloss" data-type="vritti">` wrapped around every single
    paragraph. See resolve_default_class() for how a value is decided to
    be a gloss data-type vs. a literal structural class.

    Unset (the default), body text outside of any div is left as plain
    Markdown, unchanged — the pre-existing behavior.

    This is a *different* mechanism from `default_shloka_type` (see
    extract_shlokas), which only fills in `data-type=` on an *already
    explicit* `<div class="shloka">` lacking one — that one only ever
    concerns shloka divs, never naked text.
    """
    tree = parse_divs(body)
    splices: list[tuple[int, int, str]] = []
    wrap_div_class, wrap_type_key = resolve_default_class(default_class, gloss_types)
    div_classes = recognized_div_classes(gloss_types)

    def handle_matched(
        cls_raw: str, type_key: str, attrs: str, content: str, start: int, end: int, pad: bool = False,
    ) -> None:
        rendered = render_commentary_div(cls_raw, type_key, attrs, content, gloss_types)
        if pad:
            # a gap-wrapped synthetic div (see wrap_gaps) swallows all
            # of the original whitespace between it and its neighbors
            # as part of the splice — re-add a blank line on each
            # side so it doesn't end up glued directly against an
            # adjacent </div><div...> with no blank line between
            # them, which risks the two not being parsed as separate
            # block-level HTML.
            rendered = f"\n\n{rendered}\n\n"
        splices.append((start, end, rendered))

    def wrap_gaps(start: int, end: int, nodes: list[DivNode]) -> None:
        """Any non-whitespace text directly inside [start, end) that
        ISN'T covered by one of `nodes` (this level's div children,
        already known to be non-overlapping and in order) gets treated as
        a synthetic default_class div, run through the exact same
        handling as a real one."""
        if not wrap_div_class:
            return
        cursor = start
        for n in nodes + [None]:
            gap_end = n.start if n is not None else end
            gap = body[cursor:gap_end]
            if gap.strip():
                handle_matched(wrap_div_class, wrap_type_key, "", gap, cursor, gap_end, pad=True)
            cursor = n.end if n is not None else end

    def visit(nodes: list[DivNode], parent_start: int, parent_end: int):
        wrap_gaps(parent_start, parent_end, nodes)
        for node in nodes:
            if node.base_cls == "shloka":
                # shloka is its own leaf unit, handled entirely and
                # separately by extract_shlokas() afterward — its inner
                # text is already explicitly typed by being inside a
                # <div class="shloka">, so it must NOT be re-wrapped in
                # default_class (there'd be nothing bounding it from the
                # inside, since a shloka div has no div children of its
                # own — every character of it would otherwise look like
                # "naked" text to wrap_gaps). Left completely untouched
                # here; it still correctly bounds the gaps around it,
                # since it's one of `nodes`.
                continue
            is_glosslike = node.base_cls in div_classes
            type_key = parse_attrs(node.attrs_str).get("data-type", "").strip().lower() if is_glosslike else ""
            matched = is_glosslike or bool(TOGGLE_HIDE_RE.search(node.attrs_str))
            if not matched:
                visit(node.children, node.tag_end, node.inner_end)  # structural divs (dialog-block, ...) — look inside, but leave as-is
                continue
            if is_glosslike and type_key and type_key not in gloss_types:
                warn(f"{source_for_warning}: <div class=\"{node.base_cls}\" data-type=\"{type_key}\"> — "
                     f"'{type_key}' isn't declared in {GLOSS_TYPES_CONFIG_PATH.name} or this book's own "
                     f"meta.yaml gloss_types: (no label/hide/style will apply to it, only toggle-hide= if "
                     f"set explicitly)")
            content = body[node.tag_end:node.inner_end]
            handle_matched(node.cls, type_key, node.attrs_str, content, node.start, node.end)
            # a matched gloss/vada div is opaque — don't recurse into it

    visit(tree, 0, len(body))
    return apply_splices(body, splices)


# ---------------------------------------------------------------------------
# Top navbar: just "Home" + "Up / TOC" (see render_topnav). Replaces the
# previous full list of top-level section tabs (navigation.tabs is turned
# off in build_mkdocs_static below) — every generated page gets a small
# two-button bar computed at build time (a plain relative link, no JS
# needed) pointing at the site home and at whatever TOC makes sense for
# that specific page (the containing text's TOC for a chapter page, the
# containing section's landing page for a text's own TOC page, etc).
# ---------------------------------------------------------------------------

def render_topnav(
    current_rel_file: str, up_target_rel_file: str | None, up_label: str | None,
    prev_target_rel_file: str | None = None, next_target_rel_file: str | None = None,
) -> str:
    """The small sticky pill at the top of every generated page — Home,
    then (if given) an Up-to-TOC link, then (if given) icon-only Prev/Next
    links to whatever's adjacent: the neighboring chapter in this text
    for a full_chapter-mode chapter page or a sections-mode chapter's own
    landing/TOC page (see render_chapter_full / render_chapter_sections),
    or the neighboring section within the chapter for an individual
    section page (render_chapter_sections). Either arrow is simply
    omitted at the first/last item — no dead/disabled-looking link."""
    home_link = rel_link(current_rel_file, "index.md")
    parts = [f"[{site_label('home_button_label', 'मुखपृष्ठम्')}]({home_link})"]
    if up_target_rel_file:
        up_link = rel_link(current_rel_file, up_target_rel_file)
        parts.append(f'[⬆ {up_label}]({up_link})')
    if prev_target_rel_file:
        # Raw HTML (not `[←](...)` + attr_list) on purpose: a markdown
        # link's URL segment `(...)` immediately followed by `{: .cls}`
        # is indistinguishable, to convert_bracket_attr_spans' bare-paren
        # pattern, from the kavya stage-direction convention it exists
        # to convert — it would silently eat the link. raw_html_href
        # (not rel_link) because this is literal HTML, never rewritten
        # by MkDocs' Markdown-link clean-URL handling.
        prev_href = raw_html_href(current_rel_file, prev_target_rel_file)
        parts.append(f'<a class="sv-topnav-arrow" href="{prev_href}">←</a>')
    if next_target_rel_file:
        next_href = raw_html_href(current_rel_file, next_target_rel_file)
        parts.append(f'<a class="sv-topnav-arrow" href="{next_href}">→</a>')
    inner = " · ".join(parts)
    return f'<div class="sv-topnav">\n\n{inner}\n\n</div>\n'


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

ASSETS_SRC = ROOT / "assets"
ASSETS_OUT = DOCS / "assets"


def clean_output():
    for section in SECTIONS:
        if section.out_dir.exists():
            shutil.rmtree(section.out_dir)
    if ASSETS_OUT.exists():
        shutil.rmtree(ASSETS_OUT)
    index_md = DOCS / "index.md"
    if index_md.exists():
        index_md.unlink()
    DOCS.mkdir(parents=True, exist_ok=True)


def copy_assets() -> int:
    """Mirrors `assets/` (repo root — audio/*.mp3 today, anything else
    later) into `docs/assets/`, so MkDocs serves it as static files.
    Unlike everything else this script writes, these files are never
    parsed as Markdown or linked from nav/home cards on their own — they
    only exist to be linked (or embedded, e.g. `<audio src=...>`) FROM a
    regular page, with a plain relative path (`rel_link` works fine for
    this — assets aren't clean-URL-rewritten the way *.md pages are, so
    no special-casing is needed there). Dotfiles (.DS_Store, .gitkeep,
    ...) are skipped. Returns the number of files copied."""
    if not ASSETS_SRC.exists():
        return 0

    def ignore_dotfiles(_dir: str, names: list[str]) -> list[str]:
        return [n for n in names if n.startswith(".")]

    shutil.copytree(ASSETS_SRC, ASSETS_OUT, ignore=ignore_dotfiles)
    return sum(1 for p in ASSETS_OUT.rglob("*") if p.is_file())


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


DIV_OPEN_ANY_RE = re.compile(r"<div\b([^>]*)>")


def enable_markdown_in_divs(text: str) -> str:
    """MkDocs' md_in_html extension only processes Markdown syntax (bold,
    links, etc.) *inside* a raw <div> if that div carries markdown="1" (or
    has a blank line right after its opening tag, which none of our
    sources do). Without this, things like **bold karika text** would
    render as literal asterisks. This is purely an output-side annotation
    (added only to the generated docs/ copies, never to the source .md
    files) so content authors don't need to remember to add it."""

    def repl(m: re.Match) -> str:
        attrs = m.group(1)
        if "markdown=" in attrs:
            return m.group(0)
        return f"<div{attrs} markdown=\"1\">"

    return DIV_OPEN_ANY_RE.sub(repl, text)


BRACKET_ATTR_SPAN_RE = re.compile(
    r'(?:\[(?P<bracketed>[^\]\n]+)\]|(?P<bare>\([^)\n]+\)))'
    r'\s*\.?\s*\{:\s*\.(?P<cls>[a-zA-Z0-9_-]+)\s*\}'
)


def convert_bracket_attr_spans(text: str) -> str:
    """The kavya prose/play sources mark stage directions with a bracket +
    inline-attribute-list convention, e.g. `[(प्रविश्य)].{: .action}` (and,
    inconsistently, sometimes without the brackets: `(निष्क्रान्ता){: .action}`).
    Standard Markdown's attr_list extension only attaches `{: .class}` to
    already-recognized inline elements (links, emphasis, code) — not to
    bare bracketed/parenthesized text — so as written this would render as
    literal brackets. This converts both forms straight into
    `<span class="...">` before Markdown ever sees them, so the existing
    source convention works without content authors needing to change it."""

    def repl(m: re.Match) -> str:
        content = m.group("bracketed") if m.group("bracketed") is not None else m.group("bare")
        return f'<span class="{m.group("cls")}">{content}</span>'

    return BRACKET_ATTR_SPAN_RE.sub(repl, text)


def write_md(path: Path, content: str):
    """Like write(), but also enables md_in_html on every <div> so inline
    Markdown (bold, links, etc.) inside content blocks renders correctly.
    Only ever used for generated docs/**/*.md files, never for mkdocs.yml."""
    content = convert_bracket_attr_spans(content)
    content = enable_markdown_in_divs(content)
    write(path, content)


# ---------------------------------------------------------------------------
# Section (शास्त्रम्/काव्यम्/...) + text + chapter page rendering
# ---------------------------------------------------------------------------

def render_topic_categories(rel_file: str, categories: list["TopicCategory"], heading_level: str) -> list[str]:
    """Shared by build_home_page/build_domain_index_page/build_topics_index_page
    — every place that lists topics grouped by category. A category with
    `expanded_by_default: true` (the default) gets a plain heading (at
    `heading_level`, e.g. "###") + list, exactly like a TextGroup's texts
    (see build_domain_index_page). One with `expanded_by_default: false`
    instead gets a native `<details>` (closed), so a category with many
    topics doesn't dominate the page — click to expand; works with no JS,
    including fully offline. `markdown="1"` on the wrapping tag is needed
    for the nested markdown-syntax list to render at all inside raw HTML
    — see md_in_html in build_mkdocs_static."""
    lines: list[str] = []
    for cat in categories:
        items = [f"- [{t.title}]({rel_link(rel_file, t.rel_out_file)})" for t in cat.topics]
        if cat.expanded_by_default:
            lines.append(f"{heading_level} {cat.title}")
            lines.append("")
            lines.extend(items)
            lines.append("")
        else:
            lines.append('<details class="sv-topic-category" markdown="1">')
            lines.append(f"<summary>{cat.title}</summary>")
            lines.append("")
            lines.extend(items)
            lines.append("")
            lines.append("</details>")
            lines.append("")
    return lines


def build_domain_index_page(section: SectionConfig, texts: list[Text], topic_categories: list["TopicCategory"]) -> str:
    """A section's own landing page — mirrors its home-page card (texts,
    grouped by section.text_groups, then topics grouped by category if
    this is the topics-carrying section), just as a full page rather than
    a card. This is the "Up" target for every text's own TOC page, and
    (via the "मुखपृष्ठम्" button) reachable from anywhere."""
    rel_file = f"{section.dir}/index.md"
    lines = [render_topnav(rel_file, None, None), f"# {section.h1_label}", ""]
    for group, texts_in_group in group_texts(section, texts):
        lines.append(f"## {group.h2_label}")
        lines.append("")
        for t in texts_in_group:
            target = f"{t.rel_out_dir}/index.md"
            lines.append(f"- [{t.title}]({rel_link(rel_file, target)})")
        lines.append("")
    if section.has_topics and topic_categories:
        lines.append(f"## {section.h2_topics_label}")
        lines.append("")
        lines.extend(render_topic_categories(rel_file, topic_categories, "###"))
    return "\n".join(lines)


def build_topics_index_page(section: SectionConfig, topic_categories: list["TopicCategory"]) -> str:
    """Dedicated विषयाः landing page — the "Up" target for every individual
    topic page, so going "up" from inside a topic lands you back among
    *other topics* (grouped by category), not back among the texts
    (which is a different, unrelated listing one level further up, at
    the section's own domain index page)."""
    rel_file = f"{section.dir}/topics/index.md"
    up_target = f"{section.dir}/index.md"
    lines = [
        render_topnav(rel_file, up_target, section.h1_label),
        f"# {section.h2_topics_label}",
        "",
    ]
    lines.extend(render_topic_categories(rel_file, topic_categories, "##"))
    return "\n".join(lines)


def build_text_index_page(text: Text) -> str:
    rel_file = f"{text.rel_out_dir}/index.md"
    up_target = f"{text.section.dir}/index.md"
    lines = [render_topnav(rel_file, up_target, text.section.h1_label), f"# {text.title}", ""]
    if text.author:
        lines += [f"**{site_label('author_label', 'कर्ता:')}** {text.author}", ""]
    header = str(text.meta.get("header", "")).strip()
    if header:
        lines += [header, ""]
    chapters_label = str(text.meta.get("chapters", "")).strip() or "अध्यायाः / भागाः"
    lines.append(f"## {chapters_label}")
    lines.append("")
    for ch in text.chapters:
        lines.append(f"- [{ch.nav_label}]({rel_link(rel_file, ch.rel_out_file)})")
    lines.append("")
    return "\n".join(lines)


def section_display_title(fm: dict, stem: str) -> str:
    """The title shown for one section on a sections-mode chapter's
    landing/TOC page: that section's own `title:` frontmatter, or (if
    absent) its filename without extension."""
    if fm.get("title"):
        return str(fm["title"]).strip()
    return stem


def build_shloka_table(all_shlokas: list[Shloka]) -> list[str]:
    """Renders the श्लोकसूची list shared by every page that can carry
    shlokas — a full_chapter-mode chapter page, or (in sections mode) an
    individual section page — one entry per shloka in `all_shlokas`
    (1-indexed => anchor "#s{i}", matching extract_shlokas' numbering).
    (sahitya's version had छन्दः/अलङ्काराः columns here — dropped along
    with the rest of the meter/alankara glossary; these texts aren't
    kavya.) Returns [] if there are no shlokas at all (nothing to show)."""
    if not all_shlokas:
        return []
    table_lines = [f"## {site_label('shloka_list_heading', 'श्लोकसूची')}", ""]
    for i, sh in enumerate(all_shlokas, start=1):
        table_lines.append(f"- [{sh.preview}](#s{i})")
    table_lines += ["", "---", ""]
    return table_lines


def render_chapter_full(
    chapter: Chapter, topics: dict[str, RefPage], definitions: dict[str, list[TopicDefinition]],
    *,
    current_rel_file: str | None = None,
    topnav_override: str | None = None,
    primary: bool = True,
) -> tuple[str, list[Shloka]]:
    """Returns (rendered_markdown, all_shlokas_in_anchor_order). The
    `chapter_display_style: full_chapter` (default) render path — every
    section concatenated onto one page: every section gets a
    `<div id="sec{i}">` anchor, `<notes>` shorthand is expanded,
    `<topic name="..." define="?">` tags are processed (see
    process_topic_tags — tp-anchors are numbered contiguously across the
    WHOLE page, same reasoning as the shloka counter below), and a
    श्लोकसूची list (see build_shloka_table) is appended whenever the
    chapter has any shlokas at all.

    The keyword-only params exist for exactly one other caller —
    render_chapter_sections's `full_chapter_label:` companion page, which
    reuses this same rendering at a different URL
    (chapter.full_chapter_rel_out_file, not chapter.rel_out_file — the
    landing/TOC page there is a separate, already-written file), with its
    own topnav (Home + up-to-chapter-TOC only, no chapter-level prev/next
    — see render_chapter_sections). `primary=False` marks that call as a
    secondary reading view of content already fully processed once for
    the per-section pages: it skips re-registering topic references and
    re-emitting warnings already reported during that per-section pass."""
    current_rel_file = current_rel_file or chapter.rel_out_file
    body_parts = []
    all_shlokas: list[Shloka] = []
    shloka_counter = 0
    topic_tag_counter = 0
    for i, section in enumerate(chapter.sections):
        raw = section.read_text(encoding="utf-8")
        fm, body = split_frontmatter(raw)
        anchor = f"sec{i+1}"
        body = expand_notes_shorthand(body)
        body, topic_tag_counter = process_topic_tags(
            body, chapter, topics, definitions, current_rel_file, None, topic_tag_counter,
            source_for_warning=section, primary=primary,
        )
        body = process_content_sections(
            body, chapter.default_class, chapter.text.effective_gloss_types, source_for_warning=section,
        )
        body, shlokas, shloka_counter = extract_shlokas(
            body, chapter.default_shloka_type,
            shloka_counter, source_for_warning=section, maintain_linebreak=chapter.text.maintain_shloka_linebreak,
        )
        all_shlokas.extend(shlokas)
        body_parts.append(f'<div id="{anchor}"></div>\n\n{body.strip()}')

    if topnav_override is not None:
        topnav = topnav_override
    else:
        up_target = f"{chapter.text.rel_out_dir}/index.md"
        siblings = chapter.text.chapters
        idx = siblings.index(chapter)
        prev_ch = siblings[idx - 1] if idx > 0 else None
        next_ch = siblings[idx + 1] if idx < len(siblings) - 1 else None
        topnav = render_topnav(
            current_rel_file, up_target, chapter.text.title,
            prev_target_rel_file=prev_ch.rel_out_file if prev_ch else None,
            next_target_rel_file=next_ch.rel_out_file if next_ch else None,
        )
    title_line = f"# {chapter.text.title} — {chapter.nav_label}"
    table_lines = build_shloka_table(all_shlokas)
    content = "\n".join([topnav, title_line, ""] + body_parts + [""] + table_lines) + "\n"
    return content, all_shlokas


def render_chapter_sections(
    chapter: Chapter, topics: dict[str, RefPage], definitions: dict[str, list[TopicDefinition]],
) -> None:
    """The `chapter_display_style: sections` render path — writes one
    output page per section (own URL, own topnav, own श्लोकसूची list,
    shloka anchors numbered from #s1 and topic-tag anchors from #tp1
    within that page) plus a separate chapter landing/TOC page
    (chapter.out_file == chapter.rel_out_file) listing the chapter itself
    followed by each section (title from that section's own `title:`
    frontmatter, or its filename if absent — see section_display_title),
    each linking to its page. If `full_chapter_label:` is set in this
    chapter's meta.yaml, an extra page combining every section (via
    render_chapter_full — same rendering as full_chapter mode, own
    topnav, no chapter-level prev/next since there's nothing
    chapter-level to page between here) is generated at
    chapter.full_chapter_rel_out_file and listed FIRST on the
    landing/TOC page, under that label — a secondary reading view
    (`primary=False`), so it deliberately does not re-register topic
    references or re-emit warnings already reported for the same content
    while building the per-section pages. Unlike render_chapter_full,
    this writes its own output files directly (there's no single "the"
    chapter page to hand back to the caller) and records references
    against each section's own page, not the chapter's landing page —
    see Reference."""
    up_target = f"{chapter.text.rel_out_dir}/index.md"
    siblings = chapter.text.chapters
    idx = siblings.index(chapter)
    prev_ch = siblings[idx - 1] if idx > 0 else None
    next_ch = siblings[idx + 1] if idx < len(siblings) - 1 else None

    toc_entries: list[tuple[str, str]] = []  # (display_title, rel_out_file)

    for i, section in enumerate(chapter.sections):
        raw = section.read_text(encoding="utf-8")
        fm, body = split_frontmatter(raw)
        display_title = section_display_title(fm, section.stem)
        section_rel_file = chapter.section_rel_out_file(section)
        toc_entries.append((display_title, section_rel_file))

        body = expand_notes_shorthand(body)
        body, _ = process_topic_tags(
            body, chapter, topics, definitions, section_rel_file, display_title, 0,
            source_for_warning=section, primary=True,
        )
        body = process_content_sections(
            body, chapter.default_class, chapter.text.effective_gloss_types, source_for_warning=section,
        )
        body, shlokas, _ = extract_shlokas(
            body, chapter.default_shloka_type,
            0, source_for_warning=section, maintain_linebreak=chapter.text.maintain_shloka_linebreak,
        )

        prev_sec = chapter.sections[i - 1] if i > 0 else None
        next_sec = chapter.sections[i + 1] if i < len(chapter.sections) - 1 else None
        topnav = render_topnav(
            section_rel_file, chapter.rel_out_file, chapter.nav_label,
            prev_target_rel_file=chapter.section_rel_out_file(prev_sec) if prev_sec else None,
            next_target_rel_file=chapter.section_rel_out_file(next_sec) if next_sec else None,
        )
        title_line = f"# {chapter.text.title} — {chapter.nav_label} — {display_title}"
        table_lines = build_shloka_table(shlokas)
        anchor = "sec1"
        content = "\n".join(
            [topnav, title_line, ""] + [f'<div id="{anchor}"></div>\n\n{body.strip()}'] + [""] + table_lines
        ) + "\n"
        write_md(DOCS / section_rel_file, content)

    if chapter.full_chapter_label:
        full_rel_file = chapter.full_chapter_rel_out_file
        full_topnav = render_topnav(full_rel_file, chapter.rel_out_file, chapter.nav_label)
        full_content, _ = render_chapter_full(
            chapter, topics, definitions,
            current_rel_file=full_rel_file, topnav_override=full_topnav, primary=False,
        )
        write_md(DOCS / full_rel_file, full_content)
        toc_entries.insert(0, (chapter.full_chapter_label, full_rel_file))

    topnav = render_topnav(
        chapter.rel_out_file, up_target, chapter.text.title,
        prev_target_rel_file=prev_ch.rel_out_file if prev_ch else None,
        next_target_rel_file=next_ch.rel_out_file if next_ch else None,
    )
    lines = [topnav, f"# {chapter.text.title} — {chapter.nav_label}", ""]
    for display_title, section_rel_file in toc_entries:
        lines.append(f"- [{display_title}]({rel_link(chapter.rel_out_file, section_rel_file)})")
    lines.append("")
    write_md(chapter.out_file, "\n".join(lines))


def process_chapter(
    chapter: Chapter, topics: dict[str, RefPage], definitions: dict[str, list[TopicDefinition]],
) -> None:
    """Renders and writes everything for one chapter, dispatching on
    Chapter.display_style — the single entry point main() calls per
    chapter, so it doesn't need to know which render path applies."""
    if chapter.display_style == "sections":
        render_chapter_sections(chapter, topics, definitions)
        return
    content, _ = render_chapter_full(chapter, topics, definitions)
    write_md(chapter.out_file, content)


H1_RE = re.compile(r"^\s*#\s+\S")


def render_ref_page(page: RefPage, definitions: list[TopicDefinition]) -> str:
    # "Up" goes to the विषयाः listing (other topics), NOT to the section's
    # texts listing one level further up — those are a different, sibling
    # menu, not this topic's parent.
    up_target = f"{TOPICS_SECTION.dir}/topics/index.md" if TOPICS_SECTION else None
    up_label = TOPICS_SECTION.h2_topics_label if TOPICS_SECTION else None
    parts = [render_topnav(page.rel_out_file, up_target, up_label)]
    body = page.body.strip()
    if not H1_RE.match(body):
        # only add a title heading if the source body doesn't already
        # start with one (some reference pages, like the topics/*.md
        # samples, already include their own '# ...' heading).
        parts.append(f"# {page.title}")
        parts.append("")
    parts.append(body)
    table_html = build_topic_definitions_table(page.rel_out_file, definitions)
    if table_html:
        parts.append("")
        parts.append(f"## {site_label('definitions_heading', 'परिभाषाः')}")
        parts.append("")
        parts.append(table_html)
    if page.references:
        parts.append("")
        parts.append(f"## {site_label('references_heading', 'सन्दर्भाः')}")
        parts.append("")
        for ref in page.references:
            link = rel_link(page.rel_out_file, ref.page_rel_out_file) + f"#{ref.anchor}"
            parts.append(f"- [{ref.preview}]({link}) — {ref.label}")
    parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Home page — one card per configured content section (see site_config.yaml
# content_sections:), each listing that section's texts (and, for the
# topics-carrying section, its विषयाः too). Cards are plain <div
# class="sv-home-card">...</div> — docs/stylesheets/custom.css draws the
# box; add a new section to site_config.yaml and its card just appears.
# ---------------------------------------------------------------------------

def build_home_page(
    sections_with_texts: list[tuple[SectionConfig, list[Text]]],
    topic_categories: list["TopicCategory"],
) -> str:
    home_title = site_label("home_title", "मुखपृष्ठम्")
    lines = [f"# {home_title}", "", '<div class="sv-home-cards" markdown="1">', ""]

    for section, texts in sections_with_texts:
        lines.append('<div class="sv-home-card" markdown="1">')
        lines.append("")
        lines.append(f"## {section.h1_label}")
        lines.append("")
        for group, texts_in_group in group_texts(section, texts):
            lines.append(f"### {group.h2_label}")
            lines.append("")
            for t in texts_in_group:
                lines.append(f"- [{t.title}]({t.rel_out_dir}/index.md)")
            lines.append("")
        if section.has_topics and topic_categories:
            lines.append(f"### {section.h2_topics_label}")
            lines.append("")
            lines.extend(render_topic_categories("index.md", topic_categories, "####"))
        lines.append("</div>")
        lines.append("")

    lines.append("</div>")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# mkdocs.yml — static settings + auto-generated nav
# ---------------------------------------------------------------------------

NAV_HEADER = """\
# THIS FILE IS AUTO-GENERATED by scripts/generate_indices.py — do not edit
# the `nav:` block by hand, it will be overwritten on the next run. Static
# settings below `nav:` are safe to edit; the script only rewrites the
# `nav:` list itself each time it runs.
"""

MKDOCS_STATIC_TMPL = """\
hooks:
  - scripts/mkdocs_hooks.py

site_name: {site_name}
docs_dir: docs

# use_directory_urls: false — pages build as foo.html (not foo/index.html
# served via a clean "foo/" URL) so a plain double-click on a file in a
# downloaded-and-unzipped copy of site/ (no web server, e.g. a phone/
# tablet's file browser, offline) opens and links between pages
# correctly. See .github/workflows/deploy.yml for the zip artifact this
# is aimed at; the live GitHub Pages deployment works identically either
# way, this setting only matters for the offline copy.
use_directory_urls: false

theme:
  name: material
  language: {language}
  features:
    # navigation.tabs is deliberately OFF: the top bar is just the two
    # buttons rendered by render_topnav() (Home / Up-to-TOC) on every
    # page, not a tab per top-level section — see site update notes.
    #
    # navigation.instant is deliberately OFF too (sahitya's copy of this
    # template had it on): it fetches pages via JS (History API +
    # fetch()), which fails under a plain file:// URL (no web server) —
    # exactly the offline/local-browsing case use_directory_urls: false
    # above is for. Plain links work identically either way when the
    # site IS served over http(s) (e.g. GitHub Pages), just without the
    # instant/no-reload transition.
    - navigation.indexes
    - navigation.top
    - toc.follow
    - search.suggest
  palette:
    - scheme: default
      primary: {primary}
      accent: {accent}

extra_css:
  - stylesheets/custom.css

extra_javascript:
  - javascripts/notes-toggle.js
{analytics_block}
# Enables Jinja macros/variables in markdown content — most commonly
# {{{{ page.meta.some_key }}}} to pull in a value from that page's own
# YAML frontmatter (e.g. `warning_text: ...` in a page's header, then
# `{{{{ page.meta.warning_text }}}}` anywhere in its body). See
# https://mkdocs-macros-plugin.readthedocs.io/en/latest/pages/ for the
# full templating surface (also reaches config/extra values, and lets a
# page reference another page's frontmatter, conditionals, loops, etc.).
# No define_env() hook file is configured — this site only uses the
# built-in page/config access, not custom Python macros.
#
# Jinja's default comment syntax, {{#... #}}, collides with the
# `{{#some-id}}` attr_list convention already used in this site's source
# content (e.g. `## heading {{#custom-anchor}}`, `[](){{#gunavritti}}`) —
# both start with a bare `{{#`. Rather than touch existing/future content,
# the comment delimiter alone is moved out of the way; {{{{ }}}} (variables)
# and {{% %}} (control flow) are untouched.
plugins:
  - search
  - macros:
      j2_comment_start_string: "{{##"
      j2_comment_end_string: "##}}"

markdown_extensions:
  - attr_list
  - md_in_html
  - tables
  - def_list
  - footnotes
  - admonition
  - pymdownx.details
  - pymdownx.superfences:
      # Enables ```mermaid fenced code blocks (flowcharts, sequence
      # diagrams, etc.) anywhere in any source .md file — Material for
      # MkDocs renders them client-side, no extra_javascript needed.
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - toc:
      permalink: true
      # Unicode-aware (Devanagari-safe) slugify is set via the on_config
      # hook in scripts/mkdocs_hooks.py, not here — see that file's
      # docstring for why: !!python/name: can only resolve genuinely
      # importable/installed packages, and a project-local file isn't
      # one, so this couldn't be a plain inline config value.

# A chapter_display_style: sections chapter's individual per-section
# pages, and its optional full_chapter_label: combined-reading page, are
# intentionally not added to nav (only reachable by clicking through from
# that chapter's own landing/TOC page — see render_chapter_sections) —
# tell MkDocs not to warn/fail on them under --strict.
validation:
  nav:
    omitted_files: ignore
"""


def build_mkdocs_static() -> str:
    """site_name/palette/language come from scripts/site_config.yaml (falls
    back to sensible defaults if that file is missing or a key is absent).
    `language:` is Material's OWN built-in UI-string translation
    mechanism (search box, footer, edit-this-page, the "Table of
    contents" sidebar heading, etc. — see
    https://squidfunk.github.io/mkdocs-material/setup/changing-the-language/
    for the full list of ~70 supported codes). This is separate from —
    and additional to — the site's own content-specific labels_ block
    above (home_title, references_heading, ...), which only covers
    strings THIS SCRIPT generates, not Material's own chrome. Material
    ships an official Sanskrit pack ("sa") that already covers every one
    of its strings, including "toc": "सामग्रीसारणी" for the sidebar
    heading — a much better fit for this site than leaving Material's
    chrome in English while the content itself is Devanagari throughout."""
    theme_cfg = SITE_CONFIG.get("theme", {}) or {}
    ga_property = str(SITE_CONFIG.get("google_analytics_property", "")).strip()
    analytics_block = (
        f"\nextra:\n  analytics:\n    provider: google\n    property: {ga_property}\n"
        if ga_property else ""
    )
    return MKDOCS_STATIC_TMPL.format(
        site_name=SITE_CONFIG.get("site_name") or "साहित्यशास्त्रम्",
        language=theme_cfg.get("language") or "en",
        primary=theme_cfg.get("primary") or "deep orange",
        accent=theme_cfg.get("accent") or "amber",
        analytics_block=analytics_block,
    )


def yaml_dump_nav(nav) -> str:
    return yaml.dump({"nav": nav}, allow_unicode=True, sort_keys=False, default_flow_style=False)


def build_nav(
    sections_with_texts: list[tuple[SectionConfig, list[Text]]],
    topic_categories: list["TopicCategory"],
) -> list:
    def text_nav(t: Text):
        entry = [{site_label("intro_nav_label", "परिचयः"): f"{t.rel_out_dir}/index.md"}]
        for ch in t.chapters:
            entry.append({ch.nav_label: ch.rel_out_file})
        return {t.title: entry}

    nav = [{site_label("home_nav_label", "मुखपृष्ठम्"): "index.md"}]
    for section, texts in sections_with_texts:
        # Give the section an explicit landing page as its own first
        # entry — without one, MkDocs makes any nav group link to the
        # first descendant page it finds, which looks like the section
        # only shows its first text.
        entries = [{section.h1_label: f"{section.dir}/index.md"}]
        for group, texts_in_group in group_texts(section, texts):
            entries.append({group.h2_label: [text_nav(t) for t in texts_in_group]})
        if section.has_topics and topic_categories:
            entries.append(
                {section.h2_topics_label: [
                    {section.h2_topics_label: f"{section.dir}/topics/index.md"},
                    *({cat.title: [{t.title: t.rel_out_file} for t in cat.topics]} for cat in topic_categories),
                ]}
            )
        nav.append({section.h1_label: entries})
    return nav


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def main():
    if not SECTIONS:
        print("No content_sections configured in site_config.yaml — nothing to build.", file=sys.stderr)
        sys.exit(1)

    clean_output()
    n_assets = copy_assets()

    topics: dict[str, RefPage] = {}
    definitions: dict[str, list[TopicDefinition]] = {}
    topic_categories: list[TopicCategory] = []
    topics_rel_dir = f"{TOPICS_SECTION.dir}/topics" if TOPICS_SECTION else ""

    if TOPICS_SECTION:
        topic_categories = discover_topic_categories(TOPICS_SECTION.topics_src, topics_rel_dir)
        for cat in topic_categories:
            cat_topics = discover_ref_pages("topic", TOPICS_SECTION.topics_src / cat.slug, cat.rel_dir)
            for title, page in cat_topics.items():
                if title in topics:
                    warn(f"duplicate topic title '{title}' between {topics[title].path} (category "
                         f"'{topics[title].category.title}') and {page.path} (category '{cat.title}') "
                         f"— a topic's title must be unique across the whole site, not just within its "
                         f"category, since that's what <topic name=\"...\"> tags match against")
                    continue
                page.category = cat
                topics[title] = page
            # this category's own topics, sorted by order:/title — used by
            # render_topic_categories for this category's list, and by
            # build_nav for its nested nav entries.
            cat.topics = sorted(cat_topics.values(), key=lambda e: e.sort_key)
        # drop any category nobody's put a topic in yet — same reasoning
        # as group_texts() dropping an empty TextGroup: no empty heading
        # shown for something nobody's written anything in yet.
        topic_categories = [c for c in topic_categories if c.topics]
        topic_categories.sort(key=lambda c: c.sort_key)

    # --- discover every configured section's texts + chapters ------------
    sections_with_texts: list[tuple[SectionConfig, list[Text]]] = []
    for section in SECTIONS:
        texts = discover_texts(section)
        for t in texts:
            t.chapters = discover_chapters(t)
        sections_with_texts.append((section, texts))

    # --- render chapters + text index pages for every section ------------
    # process_chapter() dispatches per-chapter on chapter_display_style —
    # see render_chapter_full() / render_chapter_sections()'s docstrings.
    # This is also where every <topic> tag in the corpus gets discovered
    # and registered onto `topics`/`definitions` (see process_topic_tags)
    # — so topic pages (written just below) always see every reference.
    for section, texts in sections_with_texts:
        for t in texts:
            for ch in t.chapters:
                process_chapter(ch, topics, definitions)
            write_md(t.out_dir / "index.md", build_text_index_page(t))

        write_md(DOCS / f"{section.dir}/index.md", build_domain_index_page(section, texts, topic_categories))

    # --- topics index page (the "Up" target for individual topic pages) --
    if TOPICS_SECTION and topic_categories:
        write_md(
            DOCS / f"{TOPICS_SECTION.dir}/topics/index.md",
            build_topics_index_page(TOPICS_SECTION, topic_categories),
        )

    # --- topic pages: write with injected परिभाषाः table + सन्दर्भाः back-links
    for title, page in topics.items():
        write_md(page.out_file, render_ref_page(page, definitions.get(title, [])))

    # --- home page ---------------------------------------------------------
    write_md(DOCS / "index.md", build_home_page(sections_with_texts, topic_categories))

    # --- mkdocs.yml (nav auto-generated, static settings preserved) -------
    nav = build_nav(sections_with_texts, topic_categories)
    mkdocs_yml = NAV_HEADER + "\n" + yaml_dump_nav(nav) + "\n" + build_mkdocs_static()
    write(ROOT / "mkdocs.yml", mkdocs_yml)

    n_texts = sum(len(texts) for _, texts in sections_with_texts)
    n_definitions = sum(len(v) for v in definitions.values())
    print(f"\nDone. {n_texts} text(s) across {len(SECTIONS)} section(s), "
          f"{len(topics)} topic(s) in {len(topic_categories)} categor(y/ies), "
          f"{n_definitions} topic definition(s), {n_assets} asset file(s).")
    if WARNINGS:
        print(f"\n{len(WARNINGS)} warning(s) were printed above — please review.", file=sys.stderr)


if __name__ == "__main__":
    main()
