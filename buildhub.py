#!/usr/bin/env python3
"""
Hub page and root file generation for bmxpartsdepot.com.

Imported by build.py. Kept separate only so build.py stays readable.
Standard library only.
"""

import html
import json
import os
import re
from datetime import date

import schema_terms

DICT_SRC = "content-plan/terms.tsv"
LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]

REGISTRY_COLUMNS = [
    "slug", "term", "letter", "category", "tier", "home", "status",
    "definition", "relevance", "source_status", "related",
]

CATEGORIES = {
    "drivetrain", "frame", "wheels", "steering",
    "brakes", "cockpit", "vintage", "hardware",
}

_REGISTRY_CACHE = {}


def load_registry(root):
    """Read content-plan/terms.tsv into a list of dicts, in file order.

    This is the single source of truth for the term list. It replaced
    content-plan/az-dictionary.md, which is kept as the original research
    record and is no longer read by anything.

    A missing or malformed registry is a hard error rather than an empty
    result. Returning {} on a bad read used to mean the hub silently built
    with no glossary at all, which looks like a content problem rather than
    a build one and wasted an afternoon finding it.
    """
    path = os.path.join(root, DICT_SRC)
    if path in _REGISTRY_CACHE:
        return _REGISTRY_CACHE[path]
    if not os.path.isfile(path):
        raise SystemExit("term registry missing: %s" % path)

    rows = []
    header = None
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            cells = line.split("\t")
            if header is None:
                header = cells
                if header != REGISTRY_COLUMNS:
                    raise SystemExit(
                        "%s line %d: unexpected columns\n  found:    %s\n  expected: %s"
                        % (path, lineno, header, REGISTRY_COLUMNS))
                continue
            if len(cells) != len(REGISTRY_COLUMNS):
                raise SystemExit("%s line %d: %d columns, expected %d"
                                 % (path, lineno, len(cells), len(REGISTRY_COLUMNS)))
            row = dict(zip(REGISTRY_COLUMNS, (c.strip() for c in cells)))
            if row["status"] not in ("published", "planned"):
                raise SystemExit("%s line %d: bad status %r"
                                 % (path, lineno, row["status"]))
            if row["category"] not in CATEGORIES:
                raise SystemExit("%s line %d: unknown category %r"
                                 % (path, lineno, row["category"]))
            if row["letter"] not in LETTERS:
                raise SystemExit("%s line %d: letter %r is not A-Z"
                                 % (path, lineno, row["letter"]))
            row["related"] = [s for s in row["related"].split("|") if s]
            rows.append(row)

    seen = {}
    for r in rows:
        if r["slug"] in seen:
            raise SystemExit("%s: duplicate slug %s" % (path, r["slug"]))
        seen[r["slug"]] = r
    dangling = sorted({s for r in rows for s in r["related"] if s not in seen})
    if dangling:
        raise SystemExit("%s: related points at unknown slugs: %s"
                         % (path, ", ".join(dangling)))

    _REGISTRY_CACHE[path] = rows
    return rows


def parse_dictionary(root):
    """(letter -> [entries]) for the terms that are actually live.

    Planned terms are deliberately excluded. A planned term has no section
    and therefore no anchor, so publishing it here would put a dead link in
    the A-Z and an unresolvable @id in the schema. It becomes visible the
    moment its status flips to published.

    Grouping comes from the registry's letter column, not from the first
    character of the name. The A-Z files by concept keyword: Wheel Dish sits
    under D, Handlebar Backsweep under B, Hub End Caps under E. Recomputing
    it would quietly reshuffle a third of the glossary.
    """
    groups = {}
    for row in load_registry(root):
        if row["status"] != "published":
            continue
        groups.setdefault(row["letter"], []).append({
            "term": row["term"],
            "slug": row["slug"],
            "definition": row["definition"],
            "relevance": row["relevance"],
            "confidence": row["source_status"],
        })
    return groups


def build_term_map(pages):
    """term slug -> (pillar slug, pillar title, has_matching_anchor).

    A term can only live on one page. Two pillars claiming the same term
    is a content decision, not something the build should silently resolve,
    so first claim wins and the collision is reported.

    Extracted so schema_terms.py generates its JSON-LD from the same mapping
    the hub links against, rather than a second copy that can drift.
    """
    term_map = {}
    collisions = []
    for p in pages:
        for slug, _label in p["terms"]:
            if slug in term_map:
                collisions.append((slug, term_map[slug][0], p["slug"]))
                continue
            term_map[slug] = (p["slug"], p["meta"].get("short", p["meta"].get("title", "")),
                              slug in p.get("ids", set()))
    return term_map, collisions


def write_hub(pages, top_guides, nav_html, footer_html, HEAD, SITE):
    # Deferred like the relativise import below: build.py imports this module
    # from inside a function, so importing it back at module level would
    # re-execute build.py as a second module object.
    from build import versioned
    import build

    root = os.path.dirname(os.path.abspath(__file__))
    groups = parse_dictionary(root)

    term_map, collisions = build_term_map(pages)

    # A claimed term the registry has never heard of is a typo. A claimed term
    # the registry knows but still marks planned is a different mistake with a
    # different fix, and it is the one people will actually make: write the
    # section, claim the term in frontmatter, forget to flip status. Saying
    # "not in the registry" there sends them looking for a spelling error that
    # is not present.
    rows = load_registry(root)
    all_slugs = {r["slug"] for r in rows}
    published_slugs = {r["slug"] for r in rows if r["status"] == "published"}
    unknown = sorted(s for s in term_map if s not in all_slugs)
    still_planned = sorted(s for s in term_map if s in all_slugs and s not in published_slugs)

    total_terms = sum(len(v) for v in groups.values())
    mapped = sum(1 for v in groups.values() for e in v if e["slug"] in term_map)

    # ---- A-Z groups -----------------------------------------------------
    az_html = []
    for L in LETTERS:
        entries = groups.get(L, [])
        if not entries:
            continue
        items = []
        for e in entries:
            target = term_map.get(e["slug"])
            defn = html.escape(e["definition"])
            name = html.escape(e["term"])
            if target:
                href = ("/guides/%s/#%s" % (target[0], e["slug"])) if target[2] \
                    else ("/guides/%s/" % target[0])
                items.append(
                    '<li><a href="%s" data-term="%s"><span class="t">%s</span>'
                    '<span class="d">%s</span></a></li>'
                    % (href, html.escape((e["term"] + " " + e["definition"]).lower(), quote=True),
                       name, defn)
                )
            else:
                items.append(
                    '<li><a href="/guides/" data-term="%s" style="opacity:.62">'
                    '<span class="t">%s</span><span class="d">%s</span></a></li>'
                    % (html.escape((e["term"] + " " + e["definition"]).lower(), quote=True),
                       name, defn)
                )
        az_html.append(
            '<section class="az-group" id="letter-%s" data-letter="%s">'
            '<h2 class="display">%s</h2><ul class="az-list">%s</ul></section>'
            % (L, L, L, "".join(items))
        )

    az_bar = "".join(
        '<button type="button" data-jump="%s"%s>%s</button>'
        % (L, "" if groups.get(L) else ' class="is-empty" disabled', L)
        for L in LETTERS
    )

    # ---- pillar cards ---------------------------------------------------
    cards = []
    for i, p in enumerate(pages, 1):
        m = p["meta"]
        cards.append(
            '<a class="pillar-card" href="/guides/%s/" data-term="%s">'
            '<span class="pc-num">Pillar %02d</span>'
            '<h3>%s</h3><p>%s</p>'
            '<span class="pc-count">%d sections &middot; %d questions</span></a>'
            % (p["slug"], html.escape((m.get("short", "") + " " + m.get("cardline", "") + " "
                                       + " ".join(t for _a, t in p["sections"])).lower(), quote=True),
               i, html.escape(m.get("short", m.get("title", ""))),
               html.escape(m.get("cardline", m.get("description", ""))[:160]),
               len(p["sections"]), p["faqs"])
        )

    url = SITE + "/guides/"
    # "N of M live so far, and the rest are being written" is false once
    # every term is placed. Say what is actually true instead.
    if mapped >= total_terms:
        az_status = "All %d entries are live." % total_terms
    else:
        az_status = ("%d of %d entries are live so far, and the rest are being written."
                     % (mapped, total_terms))


    # The DefinedTerm nodes themselves are emitted by the pillar pages, each
    # on the page that holds its anchor (see build.build_schema). The hub
    # emits the set they all point at, without enumerating them. Nodes are
    # still generated here so the count can be reported and validated.
    term_entries = [e for L in LETTERS for e in groups.get(L, [])]
    term_nodes, term_skipped = schema_terms.build_defined_terms(term_entries, term_map, SITE)

    schema = {
        "@context": "https://schema.org",
        "@graph": build.site_entities() + [
            {
                "@type": "CollectionPage",
                "@id": url + "#page",
                "name": "BMX Fitment Guide and A-Z Parts Glossary",
                "description": ("Reference guides and an A-Z dictionary for identifying used BMX "
                                "parts and checking whether they fit."),
                "url": url,
                "isPartOf": {"@type": "WebSite", "@id": SITE + "/#website"},
            },
            schema_terms.defined_term_set([], SITE),
            {
                "@type": "ItemList",
                "@id": url + "#pillars",
                "name": "Master Pillar Guides",
                "itemListElement": [
                    {
                        "@type": "ListItem", "position": i,
                        "name": p["meta"].get("short", p["meta"].get("title", "")),
                        "url": "%s/guides/%s/" % (SITE, p["slug"]),
                    }
                    for i, p in enumerate(pages, 1)
                ],
            },
            {
                "@type": "BreadcrumbList",
                "@id": url + "#crumbs",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Fitment Guide", "item": url},
                ],
            },
        ],
    }

    head = HEAD.format(
        title="BMX Fitment Guide and A-Z Parts Glossary | BMX Parts Depot",
        description=("Work out whether a used BMX part fits before you buy it. Ten reference "
                     "guides plus an A-Z glossary of BMX standards, dimensions and part variations."),
        url=url, site=SITE, schema=json.dumps(schema, indent=2, ensure_ascii=False),
        nav=nav_html("guides"), css_href=versioned("/assets/guide.css"),
    )

    page = head + """
<section class="guide-head">
  <div class="wrap">
    <p class="crumbs"><a href="/">Home</a><span aria-hidden="true">/</span>Fitment Guide</p>
    <p class="eyebrow">Reference</p>
    <h1 class="display">BMX Fitment Guide<br>and A-Z Parts Glossary</h1>
    <p class="standfirst">Ten reference guides and an A-Z glossary of {total} BMX terms, covering the standards, dimensions, and part variations that decide whether a used BMX part fits your bike. Built from manufacturer sources, with the measurements you should take yourself called out as you go.</p>
  </div>
</section>

<div class="hub-tools">
  <div class="wrap">
    <div class="az-row" id="azRow">
      <nav class="az-bar" aria-label="Jump to letter"><button class="search-toggle" id="searchToggle" type="button" aria-expanded="false" aria-controls="dict-search" aria-label="Search the guide"><svg class="ico-search" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/></svg><svg class="ico-clear" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><line x1="5" y1="5" x2="19" y2="19"/><line x1="19" y1="5" x2="5" y2="19"/></svg></button>{az_bar}</nav>
      <input type="search" id="dict-search" class="hub-input" placeholder="freecoaster, spindle, chainline, pivotal..." aria-label="Search the fitment guide" autocomplete="off" aria-describedby="search-count" tabindex="-1">
    </div>
    <p class="search-count" id="search-count" role="status" aria-live="polite" hidden></p>
  </div>
</div>

<div class="guide-body">
  <div class="wrap">
    <main id="main">
      <section class="hub-sec" id="pillars-sec" aria-labelledby="guides-head">
        <h2 class="display" id="guides-head" style="font-size:clamp(26px,3.4vw,36px);margin:0 0 6px">The Ten Master Guides</h2>
        <div class="sec-rule" id="guides-rule"></div>
        <div class="pillar-grid" id="pillar-grid">{cards}</div>
      </section>

      <section class="hub-sec" id="dict-sec" aria-labelledby="dictionary">
        <h2 class="display" id="dictionary" style="font-size:clamp(26px,3.4vw,36px);margin:0 0 6px">The A-Z Parts Glossary</h2>
        <div class="sec-rule"></div>
        <p style="max-width:70ch;color:var(--muted);margin:0 0 28px">Every term links into the guide section that covers it. {az_status}</p>
        <div id="az-results">{az}</div>
        <p class="no-results" id="no-results" hidden>Nothing matched that. Try a shorter word, or the part name on its own.</p>
      </section>
    </main>
  </div>
</div>
{footer}
<script src="{js_href}" defer></script>
</body>
</html>
""".format(total=total_terms, mapped=mapped, az_status=az_status, az_bar=az_bar,
           cards="".join(cards), az="".join(az_html), footer=footer_html(top_guides),
           js_href=versioned("/assets/guide.js"))

    outdir = os.path.join(root, "guides")
    os.makedirs(outdir, exist_ok=True)
    from build import relativise
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(relativise(page, "../"))

    unmapped = [e["term"] for L in LETTERS for e in groups.get(L, []) if e["slug"] not in term_map]
    print("hub: %d dictionary entries, %d linked to a guide section, %d not yet placed"
          % (total_terms, mapped, len(unmapped)))

    # Defects the build should refuse to ship, as opposed to things worth
    # mentioning. See main() for what happens to them.
    defects = []

    # Two pillars claiming one term is normal and stays a note: the registry's
    # home column decides which owns the canonical section, and the second
    # claim only affects which page the A-Z links to.
    if collisions:
        print("  %d terms claimed by two pillars (home decides the canonical "
              "section; the A-Z links to the first claim):" % len(collisions))
        for slug, kept, dropped in collisions:
            print("    %-32s kept on %s, also claimed by %s" % (slug, kept, dropped))

    # These two are defects. A term claimed with no anchor degrades its A-Z
    # entry to a whole-page link and drops it from the schema entirely, and a
    # claimed slug that is not in the registry is a typo that silently does
    # nothing. Both used to scroll past in a wall of build output.
    noanchor = sorted(s for s, v in term_map.items() if not v[2])
    for s in noanchor:
        defects.append("term %s is claimed but has no matching section anchor, "
                       "so the A-Z links to the page and the schema skips it" % s)
    for s in unknown:
        defects.append("term %s is claimed by a pillar but is not in the registry "
                       "at all (likely a typo in frontmatter)" % s)
    for s in still_planned:
        defects.append("term %s is claimed by %s but is still marked planned in "
                       "the registry, so it is missing from the A-Z and the "
                       "schema. Set status to published once the section is "
                       "written." % (s, term_map[s][0]))

    # ---- coverage -------------------------------------------------------
    cats = sorted(CATEGORIES)
    print()
    print("coverage by category")
    print("  %-12s %9s %9s %8s   %s" % ("category", "published", "planned", "total", "unsourced"))
    for c in cats:
        rs = [r for r in rows if r["category"] == c]
        pub = [r for r in rs if r["status"] == "published"]
        plan = [r for r in rs if r["status"] == "planned"]
        # A published term whose figure was never confirmed by two sources.
        # Not a defect, but it is the backlog that decides whether a category
        # is actually finished or only nominally finished.
        unsourced = sum(1 for r in pub if r["source_status"] not in ("solid", "src-confirmed"))
        print("  %-12s %9d %9d %8d   %d" % (c, len(pub), len(plan), len(rs), unsourced))
    tot_pub = sum(1 for r in rows if r["status"] == "published")
    print("  %-12s %9d %9d %8d" % ("all", tot_pub, len(rows) - tot_pub, len(rows)))

    return defects


def write_root_files(pages, SITE, root):
    today = str(date.today())

    # ---- sitemap.xml ----------------------------------------------------
    urls = [(SITE + "/", "1.0", today), (SITE + "/guides/", "0.9", today)]
    urls += [("%s/guides/%s/" % (SITE, p["slug"]), "0.8", p["meta"].get("updated", today))
             for p in pages]
    urls += [(SITE + "/privacy.html", "0.2", today), (SITE + "/terms.html", "0.2", today)]

    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, prio, mod in urls:
        sm.append("  <url><loc>%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>"
                  % (html.escape(loc), mod, prio))
    sm.append("</urlset>")
    open(os.path.join(root, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(sm) + "\n")

    # ---- robots.txt -----------------------------------------------------
    robots = """# bmxpartsdepot.com
# Static site. Everything here is meant to be crawled.

User-agent: *
Allow: /

# AI crawlers are welcome. The guides exist to be quoted.
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: %s/sitemap.xml
""" % SITE
    open(os.path.join(root, "robots.txt"), "w", encoding="utf-8").write(robots)

    # ---- llms.txt -------------------------------------------------------
    lines = [
        "# BMX Parts Depot",
        "",
        "> Used and mid-school BMX parts, sold through eBay. This site is a fitment and "
        "identification reference: what the BMX standards are, what dimensions they use, "
        "and how to tell which one you have before buying a used part.",
        "",
        "Sales happen on eBay, not here. There is no checkout on this site. Inventory links "
        "point out to the eBay store.",
        "",
        "## How specs on this site are sourced",
        "",
        "Dimensions are taken from component manufacturer and established retailer "
        "documentation, and each figure carries its status in the page: confirmed by two or "
        "more independent sources, single source, or sources in conflict. Where sources "
        "disagree the range is published rather than a single figure picked for tidiness. "
        "Blocks marked as caliper verification are bench measurements taken in the shop. "
        "This site does not publish sales figures, review counts, or years in business.",
        "",
        "## Fitment Guides and Key Pages",
        "",
        "- [Home](%s/) : Used and mid-school BMX parts reference and shop portal." % SITE,
        "- [BMX Fitment Guide and A-Z Parts Glossary](%s/guides/) : The master index page and searchable dictionary of all BMX fitment standards." % SITE,
    ]
    for p in pages:
        m = p["meta"]
        lines.append("- [%s](%s/guides/%s/) : %s"
                     % (m.get("short", m.get("title", "")), SITE, p["slug"],
                        m.get("description", "")))
    lines.append("")
    lines.append("## Section Anchors")
    lines.append("")
    lines.append("Each guide is deep-linkable. The sections are:")
    lines.append("")
    for p in pages:
        m = p["meta"]
        lines.append("### %s" % m.get("short", m.get("title", "")))
        lines.append("")
        for anchor, title in p["sections"]:
            lines.append("- [%s](%s/guides/%s/#%s) : Section of the guide covering %s." % (title, SITE, p["slug"], anchor, title.lower()))
        lines.append("")
    lines += [
        "## Optional",
        "",
        "- [eBay Store](https://www.ebay.com/usr/bmx-parts-depot) : The live eBay inventory store.",
        "- [Privacy Policy](%s/privacy.html) : Privacy policy for the website." % SITE,
        "- [Terms of Use](%s/terms.html) : Terms and conditions of using the website." % SITE,
        "",
    ]
    open(os.path.join(root, "llms.txt"), "w", encoding="utf-8").write("\n".join(lines))

    print("wrote sitemap.xml (%d urls), robots.txt, llms.txt" % len(urls))
