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

DICT_SRC = "content-plan/az-dictionary.md"
LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]

ROW_RE = re.compile(r"^\|(.+)\|\s*$")


def parse_dictionary(root):
    """Pull (letter -> [entries]) out of the planning markdown.

    The planning doc is the single source of truth for the term list, so
    the hub cannot drift from it. Rows that are not real entries (header
    rows, separators) are skipped.
    """
    path = os.path.join(root, DICT_SRC)
    if not os.path.isfile(path):
        return {}
    groups = {}
    letter = None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = re.match(r"^##\s+([A-Z])\s*$", line)
        if m:
            letter = m.group(1)
            groups.setdefault(letter, [])
            continue
        if letter is None:
            continue
        if line.startswith("## "):
            letter = None
            continue
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if len(cells) < 4:
            continue
        if cells[0].lower() == "term" or set(cells[0]) <= set("- :"):
            continue
        groups[letter].append({
            "term": cells[0],
            "slug": cells[1],
            "definition": cells[2],
            "relevance": cells[3],
            "confidence": cells[4] if len(cells) > 4 else "",
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
    root = os.path.dirname(os.path.abspath(__file__))
    groups = parse_dictionary(root)

    term_map, collisions = build_term_map(pages)

    # a claimed term that is not a real dictionary slug is a typo
    known = {e["slug"] for v in groups.values() for e in v}
    unknown = sorted(s for s in term_map if s not in known)

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

    # One generator for the dictionary JSON-LD, shared with schema_terms.py.
    # Terms with no matching section anchor are skipped there rather than
    # emitted with an @id that resolves to nothing.
    term_entries = [e for L in LETTERS for e in groups.get(L, [])]
    term_nodes, term_skipped = schema_terms.build_defined_terms(term_entries, term_map, SITE)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": url + "#page",
                "name": "BMX Fitment Guide and A-Z Spec Dictionary",
                "description": ("Reference guides and an A-Z dictionary for identifying used BMX "
                                "parts and checking whether they fit."),
                "url": url,
                "isPartOf": {"@type": "WebSite", "@id": SITE + "/#website"},
            },
            schema_terms.defined_term_set(term_nodes, SITE),
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
        title="BMX Fitment Guide and A-Z Spec Dictionary | BMX Parts Depot",
        description=("Work out whether a used BMX part fits before you buy it. Ten reference "
                     "guides and an A-Z dictionary of BMX standards, dimensions, and part variations."),
        url=url, site=SITE, schema=json.dumps(schema, indent=2, ensure_ascii=False),
        nav=nav_html("guides"),
    )

    page = head + """
<section class="guide-head">
  <div class="wrap">
    <p class="crumbs"><a href="/">Home</a><span aria-hidden="true">/</span>Fitment Guide</p>
    <p class="eyebrow">Reference</p>
    <h1 class="display">BMX Fitment Guide<br>and A-Z Spec Dictionary</h1>
    <p class="standfirst">Ten reference guides and {total} dictionary entries covering the standards, dimensions, and part variations that decide whether a used BMX part fits your bike. Built from manufacturer sources, with the measurements you should take yourself called out as you go.</p>
  </div>
</section>

<div class="hub-tools">
  <div class="wrap">
    <div class="hub-search">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/></svg>
      <input type="search" id="dict-search" placeholder="Search the guide: 19mm spindle, Mid BB, freecoaster..." aria-label="Search the fitment guide" autocomplete="off" aria-describedby="search-count">
    </div>
    <p class="search-count" id="search-count" role="status" aria-live="polite" hidden></p>
    <nav class="az-bar" aria-label="Jump to letter">{az_bar}</nav>
  </div>
</div>

<div class="guide-body">
  <div class="wrap">
    <main id="main">
      <h2 class="display" id="guides-head" style="font-size:clamp(26px,3.4vw,36px);margin:0 0 6px">The Ten Master Guides</h2>
      <div class="sec-rule" id="guides-rule"></div>
      <div class="pillar-grid" id="pillar-grid">{cards}</div>

      <h2 class="display" id="dictionary" style="font-size:clamp(26px,3.4vw,36px);margin:0 0 6px">A-Z Dictionary</h2>
      <div class="sec-rule"></div>
      <p style="max-width:70ch;color:var(--muted);margin:0 0 28px">Every term links into the guide section that covers it. {mapped} of {total} entries are live so far, and the rest are being written.</p>
      <div id="az-results">{az}</div>
      <p class="no-results" id="no-results" hidden>Nothing matched that. Try a shorter word, or the part name on its own.</p>
    </main>
  </div>
</div>
{footer}
<script src="/assets/guide.js" defer></script>
</body>
</html>
""".format(total=total_terms, mapped=mapped, az_bar=az_bar,
           cards="".join(cards), az="".join(az_html), footer=footer_html(top_guides))

    outdir = os.path.join(root, "guides")
    os.makedirs(outdir, exist_ok=True)
    from build import relativise
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(relativise(page, "../"))

    unmapped = [e["term"] for L in LETTERS for e in groups.get(L, []) if e["slug"] not in term_map]
    print("hub: %d dictionary entries, %d linked to a guide section, %d not yet placed"
          % (total_terms, mapped, len(unmapped)))
    if collisions:
        print("  %d term collisions (first claim kept, second ignored):" % len(collisions))
        for slug, kept, dropped in collisions:
            print("    %-32s kept on %s, also claimed by %s" % (slug, kept, dropped))
    noanchor = sorted(s for s, v in term_map.items() if not v[2])
    if noanchor:
        print("  %d terms claimed but with no matching section anchor "
              "(hub links to the page, not a fragment):" % len(noanchor))
        print("    " + ", ".join(noanchor))
    if unknown:
        print("  %d claimed terms are not in the dictionary (likely typos): %s"
              % (len(unknown), ", ".join(unknown)))
    return unmapped


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
        "## Master pillar guides",
        "",
    ]
    for i, p in enumerate(pages, 1):
        m = p["meta"]
        lines.append("- [%s](%s/guides/%s/): %s"
                     % (m.get("short", m.get("title", "")), SITE, p["slug"],
                        m.get("description", "")))
    lines.append("")
    lines.append("## Section anchors")
    lines.append("")
    lines.append("Each guide is deep-linkable. The sections are:")
    lines.append("")
    for p in pages:
        m = p["meta"]
        lines.append("### %s" % m.get("short", m.get("title", "")))
        lines.append("")
        for anchor, title in p["sections"]:
            lines.append("- [%s](%s/guides/%s/#%s)" % (title, SITE, p["slug"], anchor))
        lines.append("")
    lines += [
        "## Reference",
        "",
        "- [A-Z fitment dictionary](%s/guides/#dictionary): every BMX term, standard, and "
        "dimension covered on the site, each linking into the guide section that explains it." % SITE,
        "- [eBay store](https://www.ebay.com/usr/bmx-parts-depot): the live inventory.",
        "",
        "## Optional",
        "",
        "- [Privacy policy](%s/privacy.html)" % SITE,
        "- [Terms of use](%s/terms.html)" % SITE,
        "",
    ]
    open(os.path.join(root, "llms.txt"), "w", encoding="utf-8").write("\n".join(lines))

    print("wrote sitemap.xml (%d urls), robots.txt, llms.txt" % len(urls))
