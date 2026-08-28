"""
DefinedTerm JSON-LD generation and validation for the A-Z fitment dictionary.

Imported by buildhub.py so there is one generator rather than two that drift.
Run directly for a validation report:

    python3 schema_terms.py

Design notes, because two of these constrain what the payload may claim.

A term is NOT a page. All 107 terms live as sections inside the ten pillar
guides, so a term's canonical URL is the pillar URL plus its section fragment.
There is no per-term canonical and no /dictionary/ page. Emitting either would
put @ids in the graph that resolve to nothing.

A term is only emitted when its section anchor actually exists on the target
page. A DefinedTerm whose @id points at a fragment that is not in the HTML is
a broken node, so terms claimed without a matching anchor are reported and
skipped rather than published. Fix them by writing the section, not by
loosening this check.
"""

import json
import re
import unicodedata

# Characters that survive a copy-paste from a word processor and then break
# either JSON consumers or plain-text extraction. Mapped to ASCII equivalents.
NONASCII_FIXES = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", " ": " ",
    "′": "'", "″": '"', "×": "x", "−": "-",
}

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean_text(s):
    """Strip HTML, normalise unicode punctuation to ASCII, collapse whitespace.

    Returns plain text safe to embed as a JSON string value. Quote escaping is
    left to json.dumps, which is the only correct place for it; doing it here
    as well would double-escape.
    """
    if not s:
        return ""
    s = TAG_RE.sub("", s)
    s = unicodedata.normalize("NFKC", s)
    for bad, good in NONASCII_FIXES.items():
        s = s.replace(bad, good)
    s = s.replace("&amp;", "and").replace("&nbsp;", " ")
    return WS_RE.sub(" ", s).strip()


def term_url(site, page_slug, term_slug):
    return "%s/guides/%s/#%s" % (site, page_slug, term_slug)


def build_defined_terms(entries, term_map, site):
    """Map dictionary entries to DefinedTerm nodes.

    entries  -- iterable of {"term","slug","definition"} from the A-Z source
    term_map -- {term_slug: (page_slug, page_title, has_anchor)}
    Returns (nodes, skipped) where skipped is [(slug, reason)].
    """
    nodes, skipped, seen = [], [], set()

    for e in entries:
        slug = e["slug"]
        target = term_map.get(slug)

        if target is None:
            skipped.append((slug, "not placed on any pillar page"))
            continue
        page_slug, _page_title, has_anchor = target
        if not has_anchor:
            skipped.append((slug, "claimed by %s with no matching section anchor" % page_slug))
            continue
        if slug in seen:
            skipped.append((slug, "duplicate slug in the dictionary source"))
            continue
        seen.add(slug)

        url = term_url(site, page_slug, slug)
        nodes.append({
            "@type": "DefinedTerm",
            "@id": url,
            "name": clean_text(e["term"]),
            "description": clean_text(e["definition"]),
            "termCode": slug,
            "url": url,
            "inDefinedTermSet": {"@id": site + "/guides/#dictionary"},
        })

    return nodes, skipped


def validate(nodes, known_anchors=None):
    """Return a list of problem strings. Empty list means the payload is clean.

    known_anchors -- optional {page_slug: set(anchor_ids)} to prove every @id
                     fragment resolves to a real element in the built HTML.
    """
    problems = []
    ids = {}

    for n in nodes:
        name = n.get("name") or "(unnamed)"

        for field in ("@type", "@id", "name", "description", "termCode", "inDefinedTermSet"):
            if not n.get(field):
                problems.append("%s: missing required field %s" % (name, field))

        nid = n.get("@id", "")
        if nid in ids:
            problems.append("%s: duplicate @id %s (also %s)" % (name, nid, ids[nid]))
        ids[nid] = name

        if not nid.startswith("https://"):
            problems.append("%s: @id is not an absolute https URL" % name)
        if "#" not in nid:
            problems.append("%s: @id has no fragment, so it points at a page not a term" % name)

        for field in ("name", "description"):
            v = n.get(field, "")
            if "<" in v or ">" in v:
                problems.append("%s: %s still contains markup" % (name, field))
            bad = [c for c in v if ord(c) > 126]
            if bad:
                problems.append("%s: %s has non-ASCII %r (U+%04X)"
                                % (name, field, bad[0], ord(bad[0])))
            # json.dumps escapes quotes; a raw backslash still breaks consumers.
            if "\\" in v:
                problems.append("%s: %s contains a backslash" % (name, field))

        d = n.get("description", "")
        if d and not d.endswith("."):
            problems.append("%s: description does not end in a full stop" % name)
        if d.count(".") > 3:
            problems.append("%s: description looks longer than two sentences" % name)

        if known_anchors is not None and "#" in nid:
            base, frag = nid.rsplit("#", 1)
            page = base.rstrip("/").rsplit("/", 1)[-1]
            anchors = known_anchors.get(page)
            if anchors is None:
                problems.append("%s: @id points at unknown page %s" % (name, page))
            elif frag not in anchors:
                problems.append("%s: @id fragment #%s is not in %s" % (name, frag, page))

        # Round-trip proves the node survives serialisation intact.
        try:
            if json.loads(json.dumps(n, ensure_ascii=False)) != n:
                problems.append("%s: does not round-trip through JSON" % name)
        except (TypeError, ValueError) as exc:
            problems.append("%s: not JSON serialisable (%s)" % (name, exc))

    return problems


def defined_term_set(nodes, site):
    """Wrap the terms in the DefinedTermSet node the pages already reference."""
    return {
        "@type": "DefinedTermSet",
        "@id": site + "/guides/#dictionary",
        "name": "BMX Parts Depot A-Z Fitment Dictionary",
        "description": "BMX technical terms, dimensional standards, and part variations.",
        "url": site + "/guides/",
        "hasDefinedTerm": nodes,
    }


def _slugify(s):
    """Mirror of build.py's slugify. Kept identical on purpose."""
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "section"


def _parse_pages(root):
    """Minimal stand-in for build.py's page loader, for the standalone report.

    Only reads what build_term_map needs: slug, terms, meta title, anchors.
    """
    import glob
    import os

    PAIR = re.compile(r"([a-z0-9][a-z0-9-]*)\|(.*?)(?=\s*,\s*[a-z0-9][a-z0-9-]*\||\s*$)")
    pages = []
    for path in sorted(glob.glob(os.path.join(root, "content/pillars/*.md"))):
        text = open(path, encoding="utf-8").read()
        fm = text.split("---", 2)[1]
        meta = dict(re.findall(r"^([a-z]+):\s*(.*)$", fm, re.M))
        pages.append({
            "slug": meta.get("slug", ""),
            "meta": meta,
            "terms": [(m.group(1), m.group(2).strip())
                      for m in PAIR.finditer(meta.get("terms", ""))],
            # Explicit {#anchor} plus the ids build.py auto-slugifies from any
            # heading that has none. Reading only the explicit ones under-reports
            # and makes the report disagree with the shipped page.
            "ids": (set(re.findall(r"\{#([a-z0-9-]+)\}", text))
                    | {_slugify(m) for m in re.findall(r"^#{2,4}\s+(.+?)\s*$", text, re.M)
                       if "{#" not in m}),
        })
    return pages


def _report():
    import glob
    import os
    import build
    import buildhub

    root = os.path.dirname(os.path.abspath(__file__))
    site = build.SITE
    groups = buildhub.parse_dictionary(root)
    entries = [e for L in buildhub.LETTERS for e in groups.get(L, [])]

    # Reuse the real page loader so the report cannot disagree with the build.
    pages = build.load_pages() if hasattr(build, "load_pages") else _parse_pages(root)
    term_map, _collisions = buildhub.build_term_map(pages)

    nodes, skipped = build_defined_terms(entries, term_map, site)

    anchors = {}
    for f in glob.glob("guides/*/index.html"):
        page = f.split("/")[1]
        anchors[page] = set(re.findall(r'id="([^"]+)"', open(f).read()))

    problems = validate(nodes, anchors)

    print("dictionary entries : %d" % len(entries))
    print("emitted            : %d" % len(nodes))
    print("skipped            : %d" % len(skipped))
    for slug, why in skipped:
        print("    %-30s %s" % (slug, why))
    print("validation problems: %d" % len(problems))
    for p in problems:
        print("    " + p)

    with open("schema-terms.json", "w") as fh:
        json.dump({"@context": "https://schema.org",
                   "@graph": [defined_term_set(nodes, site)]},
                  fh, indent=2, ensure_ascii=False)
    print("wrote schema-terms.json")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(_report())
