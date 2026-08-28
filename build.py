#!/usr/bin/env python3
"""
bmxpartsdepot.com static generator.

Reads Markdown sources from content/ and writes plain HTML into guides/.
Python 3 standard library only. No package.json, no node_modules, no
bundler, no framework. Run it, commit the HTML it produces, push.

    python3 build.py

The site GitHub Pages serves is still hand-checkable static HTML. This
script is a tool that lives in the repo, not a dependency of the site.
If you delete it tomorrow, every published page keeps working.

Source format is Markdown with a small frontmatter block and a handful
of block directives (::: quickanswer, ::: video, ::: caliper, and so
on). Raw HTML passes straight through, so spec tables can be written as
real HTML5 tables.
"""

import hashlib
import html
import json
import os
import re
import shutil
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
OUT = os.path.join(ROOT, "guides")
SITE = "https://bmxpartsdepot.com"
EBAY = "https://www.ebay.com/usr/bmx-parts-depot"

# Era names carry NO year ranges. The commonly quoted boundaries
# (pre-1995, 1995-2008, 2009 onward) could not be traced to a primary
# source during research, and pillar 10 argues exactly that. A chip
# asserting dates above a page saying the dates are unsourced would
# undercut the whole site. Eras are recognised by features, not years.
ERA_LABELS = {
    "old": ("Old School", ""),
    "mid": ("Mid School", ""),
    "modern": ("Modern", ""),
    "all": ("All Eras", ""),
}


# --------------------------------------------------------------------------
# frontmatter
# --------------------------------------------------------------------------

def split_front(text):
    """Return (dict, body). Frontmatter is `key: value` between --- fences."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    meta = {}
    key = None
    for line in raw.split("\n"):
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and key:
            meta[key] += " " + line.strip()
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        meta[key] = val.strip()
    return meta, body


def as_list(meta, key):
    v = meta.get(key, "").strip()
    return [x.strip() for x in v.split(",") if x.strip()] if v else []


PAIR_RE = re.compile(r"([a-z0-9][a-z0-9-]*)\|(.*?)(?=\s*,\s*[a-z0-9][a-z0-9-]*\||\s*$)")


def as_pairs(meta, key):
    """`slug|Label, slug2|Label 2` -> [(slug, label), ...]

    Labels are allowed to contain commas ("Frame ID, Materials and Geometry"),
    so this splits on the slug|label boundary rather than on every comma.
    Splitting naively produced links to /guides/Materials and Geometry/.
    """
    raw = meta.get(key, "").strip()
    if not raw:
        return []
    pairs = [(m.group(1), m.group(2).strip().rstrip(",").strip())
             for m in PAIR_RE.finditer(raw)]
    if pairs:
        return pairs
    return [(x, x.replace("-", " ").title()) for x in as_list(meta, key)]


# --------------------------------------------------------------------------
# inline markdown
# --------------------------------------------------------------------------

CODE_RE = re.compile(r"`([^`]+)`")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
EM_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def inline(s):
    """Escape, then re-introduce the small set of inline markup we allow."""
    stash = []

    def keep(m):
        stash.append("<code>%s</code>" % html.escape(m.group(1)))
        return "\x00%d\x00" % (len(stash) - 1)

    s = CODE_RE.sub(keep, s)
    s = html.escape(s, quote=False)
    s = LINK_RE.sub(
        lambda m: '<a href="%s">%s</a>' % (html.escape(m.group(2), quote=True), m.group(1)),
        s,
    )
    s = BOLD_RE.sub(r"<strong>\1</strong>", s)
    s = EM_RE.sub(r"<em>\1</em>", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], s)
    return s


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "section"


def asset_ver(relpath):
    """Short content hash for cache-busting a static asset.

    Without this, a returning visitor gets freshly generated HTML alongside
    whatever guide.css their browser cached, which renders as a broken page
    rather than an old one. Changing the file changes the query string, so
    the browser refetches exactly when it should and keeps caching the rest
    of the time.
    """
    path = os.path.join(ROOT, relpath.lstrip("/"))
    try:
        with open(path, "rb") as fh:
            return hashlib.md5(fh.read()).hexdigest()[:8]
    except OSError:
        return ""


def versioned(relpath):
    v = asset_ver(relpath)
    return relpath + ("?v=" + v if v else "")


# --------------------------------------------------------------------------
# block directives
# --------------------------------------------------------------------------

def d_quickanswer(arg, body, ctx):
    paras = "".join("<p>%s</p>" % inline(p.strip()) for p in body.split("\n\n") if p.strip())
    ident = ' id="quick-answer"' if not ctx["seen_qa"] else ""
    ctx["seen_qa"] = True
    return (
        '<div%s class="quick-answer">'
        '<p class="qa-label">Quick Answer</p>%s</div>' % (ident, paras)
    )


def d_caliper(arg, body, ctx):
    """Bench measurements, recorded by Joe. Never write a figure into one of
    these that did not come off a part in the shop.

    A block carrying `tool:` plus one or more `- Label | reading` rows renders
    as verified, with the tool named in the badge. Anything else renders as an
    open request, so a half-filled block cannot pass itself off as measured.
    """
    subject = inline(arg) if arg else "this section"
    filled = body.strip()
    icon = (
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M3 3v14a4 4 0 0 0 4 4h14"/><path d="M7 7h10"/><path d="M7 12h6"/></svg>'
    )

    tool = part = ""
    rows, prose = [], []
    for line in filled.split("\n"):
        s = line.strip()
        if s.lower().startswith("tool:"):
            tool = s[5:].strip()
        elif s.lower().startswith("part:"):
            part = s[5:].strip()
        elif s.startswith("- ") and "|" in s:
            label, _, reading = s[2:].partition("|")
            rows.append((label.strip(), reading.strip()))
        else:
            prose.append(line)

    if tool and rows:
        body_html = "".join(
            "<p>%s</p>" % inline(p.strip())
            for p in "\n".join(prose).split("\n\n") if p.strip()
        )
        part_html = ('<p class="cal-part">Measured off %s</p>' % inline(part)) if part else ""
        return (
            '<aside class="caliper verified">'
            '<p class="cal-label">%s Depot Caliper Verification</p>'
            '<p class="cal-badge">Caliper Verified &middot; %s</p>'
            '<table class="cal-table"><tbody>%s</tbody></table>%s%s</aside>'
            % (icon, html.escape(tool),
               "".join('<tr><th scope="row">%s</th><td class="num">%s</td></tr>'
                       % (inline(l), inline(r)) for l, r in rows),
               part_html, body_html)
        )

    ctx["todo"].append("caliper: %s" % (arg or "unlabelled"))
    return (
        '<aside class="caliper"><p class="cal-label">%s Depot Caliper Verification</p>'
        '<p><span class="todo">[CALIPER VERIFICATION NEEDED]</span><br>'
        'Measure %s on the bench and record the reading here, with the tool used and '
        'the part it came off. Leave this block out rather than filling it with a figure '
        'taken from somewhere else.</p></aside>' % (icon, subject)
    )


def d_video(arg, body, ctx):
    parts = [p.strip() for p in arg.split("|")]
    title = parts[0] if parts else ""
    vid = parts[1] if len(parts) > 1 else ""
    caption = body.strip()
    cap_html = (
        "<figcaption><b>%s</b>%s</figcaption>"
        % (inline(title), (" " + inline(caption)) if caption else "")
    ) if title or caption else ""

    if vid and not vid.upper().startswith("TBD"):
        ctx["videos"].append({"title": title, "id": vid, "caption": caption})
        frame = (
            '<div class="video-frame">'
            '<iframe src="https://www.youtube-nocookie.com/embed/%s" '
            'title="%s" loading="lazy" allowfullscreen '
            'allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
            'referrerpolicy="strict-origin-when-cross-origin"></iframe></div>'
            % (html.escape(vid, quote=True), html.escape(title, quote=True))
        )
    else:
        ctx["todo"].append("video: %s" % (title or "untitled"))
        frame = (
            '<div class="video-frame placeholder">'
            '<span class="todo">[VIDEO ID NEEDED]</span>'
            '<span class="hint">%s</span></div>'
            % inline(title or "Drop a YouTube video id into the source file.")
        )
    return '<figure class="video">%s%s</figure>' % (frame, cap_html)


def inline_svg(path, uid):
    """Inline an SVG so the page's own fonts and CSS reach it.

    Loaded through <img> an SVG is a sealed document: webfonts never
    arrive, its text is not selectable, not searchable and invisible to a
    screen reader. Inlining fixes all of that, but it drops the file's
    guts into a shared document, and these files were drawn independently:
    `.bg` is defined in all thirteen and `id="arrow-end"` in four. Three
    diagrams share the headset page, so unscoped they would fight, and
    every marker reference would resolve to whichever SVG the browser
    parsed first.

    So everything gets namespaced on the way in: internal ids and the
    url(#...) references that point at them, and every CSS selector gets
    prefixed with the wrapper's own id.
    """
    raw = open(path, encoding="utf-8").read()
    raw = re.sub(r"<\?xml[^>]*\?>\s*", "", raw)
    raw = re.sub(r"<!DOCTYPE[^>]*>\s*", "", raw)

    # ids first, longest name first so short names cannot corrupt long ones
    for ident in sorted(set(re.findall(r'\bid="([^"]+)"', raw)), key=len, reverse=True):
        new = "%s-%s" % (uid, ident)
        raw = raw.replace('id="%s"' % ident, 'id="%s"' % new)
        raw = raw.replace("url(#%s)" % ident, "url(#%s)" % new)
        raw = raw.replace('href="#%s"' % ident, 'href="#%s"' % new)

    def scope(m):
        css = m.group(1)
        # the drawings ask for system-ui; the page already loads Inter,
        # so put it in front and keep the rest of the stack as written
        css = re.sub(r"font-family:\s*system-ui", "font-family: Inter, system-ui", css)
        out = []
        for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            sels = ",".join("#%s %s" % (uid, s.strip()) for s in sel.split(",") if s.strip())
            if sels:
                out.append("%s{%s}" % (sels, decl.strip()))
        return "<style>%s</style>" % "".join(out)

    raw = re.sub(r"<style[^>]*>(.*?)</style>", scope, raw, flags=re.S)

    def root(m):
        tag = re.sub(r'\s(?:width|height)="[^"]*"', "", m.group(0))
        return tag.replace(
            "<svg",
            '<svg id="%s" role="img" style="display:block;width:100%%;height:auto"' % uid,
            1,
        )

    return re.sub(r"<svg[^>]*>", root, raw, count=1)


def d_figure(arg, body, ctx):
    parts = [p.strip() for p in arg.split("|")]
    title = parts[0] if parts else ""
    src = parts[1] if len(parts) > 1 else ""
    alt = parts[2] if len(parts) > 2 else title
    caption = body.strip()
    cap_html = (
        "<figcaption><b>%s</b>%s</figcaption>"
        % (inline(title), (" " + inline(caption)) if caption else "")
    ) if title or caption else ""

    if src and not src.upper().startswith("TBD"):
        ctx["images"].append({"title": title, "src": src, "caption": caption or title})
        local = os.path.join(ROOT, src.lstrip("/"))
        if src.lower().endswith(".svg") and os.path.isfile(local):
            uid = "dg-" + slugify(os.path.splitext(os.path.basename(src))[0])
            body_html = '<div class="fig-body">%s</div>' % inline_svg(local, uid)
        else:
            body_html = (
                '<div class="fig-body"><img src="%s" alt="%s" loading="lazy" decoding="async"></div>'
                % (html.escape(src, quote=True), html.escape(alt, quote=True))
            )
    else:
        ctx["todo"].append("diagram: %s" % (title or "untitled"))
        body_html = (
            '<div class="fig-body placeholder">'
            '<span class="todo">[DIAGRAM NEEDED]</span>'
            '<span>%s</span></div>' % inline(title or "Add the image path in the source file.")
        )
    return '<figure class="diagram">%s%s</figure>' % (body_html, cap_html)


def d_faq(arg, body, ctx):
    parts = [p.strip() for p in arg.split("|")]
    qid = parts[0] if parts else ""
    question = parts[1] if len(parts) > 1 else qid
    anchor = slugify(question)[:60]
    answer_paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    plain = " ".join(re.sub(r"\s+", " ", strip_md(p)) for p in answer_paras)
    ctx["faqs"].append({"q": question, "a": plain, "id": anchor})
    ctx["ids"].add(anchor)
    inner = "".join("<p>%s</p>" % inline(p) for p in answer_paras)
    qid_html = '<span class="qid">%s</span>' % html.escape(qid) if qid else ""
    return (
        '<div class="faq-block" id="%s"><h3>%s%s</h3>%s</div>'
        % (anchor, qid_html, inline(question), inner)
    )


def d_ebay(arg, body, ctx):
    parts = [p.strip() for p in arg.split("|")]
    title = parts[0] if parts else "Listing"
    grade = (parts[1] if len(parts) > 1 else "").upper()
    price = parts[2] if len(parts) > 2 else ""
    url = parts[3] if len(parts) > 3 else EBAY
    thumb = parts[4] if len(parts) > 4 else ""
    note = body.strip()

    # A grade, a price and a photo describe one specific item. A card that points
    # at the store rather than at an item has none of them, and must not invent
    # them: no badge, no price, no dashed photo box. Leave the field empty and the
    # card renders as a clean category link instead of a half-filled listing.
    if grade and not grade.startswith("TBD"):
        gclass = {"A": "grade-a", "B": "grade-b", "C": "grade-c"}.get(grade, "grade-b")
        gtext = {"A": "Grade A", "B": "Grade B", "C": "Grade C"}.get(grade, "Grade " + grade)
        grade_html = '<span class="grade %s">%s</span>' % (gclass, gtext)
    else:
        grade_html = ""

    if thumb and not thumb.upper().startswith("TBD"):
        thumb_html = '<div class="thumb"><img src="%s" alt="%s" loading="lazy"></div>' % (
            html.escape(thumb, quote=True), html.escape(title, quote=True))
    else:
        thumb_html = ""

    if price and not price.upper().startswith("TBD"):
        price_html = '<span class="price">%s</span>' % html.escape(price)
    else:
        price_html = ""
    note_html = "<p>%s</p>" % inline(note) if note else ""
    arrow = (
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
        '<polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>'
    )
    meta_html = ('<div class="meta">%s%s</div>' % (grade_html, price_html)) if (grade_html or price_html) else ""
    cta_text = "View Live Item on eBay" if thumb_html or meta_html else "Browse the eBay Store"
    return (
        '<div class="part-card%s">%s<div class="pc-body">'
        '<h4><a href="%s" target="_blank" rel="noopener nofollow">%s</a></h4>'
        '%s%s'
        '<a class="btn sm cta" href="%s" target="_blank" rel="noopener nofollow">'
        '%s %s</a></div></div>'
        % ("" if thumb_html else " no-thumb", thumb_html,
           html.escape(url, quote=True), inline(title),
           meta_html, note_html, html.escape(url, quote=True),
           html.escape(cta_text), arrow)
    )


def d_fitbadge(arg, body, ctx):
    parts = [p.strip() for p in arg.split("|")]
    question = parts[0] if parts else ""
    label = parts[1] if len(parts) > 1 else "Read the guide"
    href = parts[2] if len(parts) > 2 else "/guides/"
    icon = (
        '<svg class="fb-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/>'
        '<line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
    )
    return (
        '<a class="fit-badge" href="%s">%s<span class="fb-text">'
        '<span class="fb-q">%s</span>'
        '<span class="fb-a">Read <b>%s</b></span></span></a>'
        % (html.escape(href, quote=True), icon, inline(question), inline(label))
    )


def d_needsverify(arg, body, ctx):
    """A visible, honest hole. Better than a plausible invented number.

    Renders as a checklist of the specs this section still needs sourced.
    Every one of these should be gone before the page is called finished.
    """
    items = [l.strip("- ").strip() for l in body.split("\n") if l.strip()]
    ctx["todo"].extend("spec: %s" % i for i in items)
    lis = "".join("<li>%s</li>" % inline(i) for i in items)
    return (
        '<aside class="caliper" data-needs-verify="%d">'
        '<p class="cal-label">Specifications pending verification</p>'
        '<p><span class="todo">[SOURCE CHECK NEEDED]</span><br>'
        'These figures are not published yet because they have not been confirmed '
        'against a manufacturer or other primary source. %s</p>'
        '<ul style="margin:10px 0 0;padding-left:20px;font-size:15px;color:var(--muted)">%s</ul>'
        '</aside>' % (len(items), inline(arg) if arg else "", lis)
    )


DIRECTIVES = {
    "needsverify": d_needsverify,
    "quickanswer": d_quickanswer,
    "caliper": d_caliper,
    "video": d_video,
    "figure": d_figure,
    "faq": d_faq,
    "ebay": d_ebay,
    "fitbadge": d_fitbadge,
}


def strip_md(s):
    s = CODE_RE.sub(r"\1", s)
    s = LINK_RE.sub(r"\1", s)
    s = BOLD_RE.sub(r"\1", s)
    s = EM_RE.sub(r"\1", s)
    return s.strip()


# --------------------------------------------------------------------------
# block renderer
# --------------------------------------------------------------------------

HEAD_RE = re.compile(r"^(#{2,4})\s+(.*?)(?:\s*\{#([a-z0-9-]+)\})?\s*$")
DIR_OPEN = re.compile(r"^:::\s*(\w+)\s*(.*)$")


def render(body, ctx):
    lines = body.split("\n")
    out = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        m = DIR_OPEN.match(line)
        if m and m.group(1) in DIRECTIVES:
            name, arg = m.group(1), m.group(2).strip()
            inner = []
            i += 1
            while i < n and lines[i].strip() != ":::":
                inner.append(lines[i])
                i += 1
            i += 1
            out.append(DIRECTIVES[name](arg, "\n".join(inner), ctx))
            continue

        m = HEAD_RE.match(line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            anchor = m.group(3) or slugify(strip_md(text))
            # Two headings resolving to the same id silently break deep links:
            # the browser and the schema both take the first, so the second
            # section becomes unreachable. Usually an explicit {#anchor} on one
            # heading colliding with the auto-slug of another.
            if anchor in ctx["ids"]:
                ctx["dupe_ids"].append(anchor)
            ctx["ids"].add(anchor)
            if level == 2:
                ctx["toc"].append((anchor, strip_md(text)))
                out.append('<h2 id="%s">%s</h2><div class="sec-rule"></div>' % (anchor, inline(text)))
            else:
                out.append("<h%d id=\"%s\">%s</h%d>" % (level, anchor, inline(text), level))
            i += 1
            continue

        # raw HTML block passthrough, so real HTML5 tables can be authored
        if line.lstrip().startswith("<"):
            block = []
            while i < n and lines[i].strip():
                block.append(lines[i])
                i += 1
            raw = "\n".join(block)
            if "<table" in raw:
                # A scrollable region only a mouse can scroll strands the
                # content inside it for keyboard users (WCAG 2.1.1), so the
                # wrapper is focusable and labelled.
                #
                # Sources hand-write <div class="table-scroll"> around their
                # tables, and this used to wrap them a second time, nesting
                # two identical scroll containers. Add the attributes to the
                # one that is already there rather than making another.
                ATTRS = ' tabindex="0" role="region" aria-label="Specification table, scrollable"'
                if 'class="table-scroll"' in raw:
                    raw = raw.replace('<div class="table-scroll">',
                                      '<div class="table-scroll"%s>' % ATTRS)
                else:
                    raw = '<div class="table-scroll"%s>%s</div>' % (ATTRS, raw)
            out.append(raw)
            continue

        if line.lstrip().startswith(("- ", "* ")):
            items = []
            while i < n and lines[i].lstrip().startswith(("- ", "* ")):
                items.append(inline(lines[i].lstrip()[2:].strip()))
                i += 1
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % x for x in items))
            continue

        if re.match(r"^\d+\.\s", line.lstrip()):
            items = []
            while i < n and re.match(r"^\d+\.\s", lines[i].lstrip()):
                items.append(inline(re.sub(r"^\d+\.\s", "", lines[i].lstrip()).strip()))
                i += 1
            out.append("<ol>%s</ol>" % "".join("<li>%s</li>" % x for x in items))
            continue

        para = []
        while i < n and lines[i].strip() and not DIR_OPEN.match(lines[i]) \
                and not HEAD_RE.match(lines[i]) and not lines[i].lstrip().startswith("<") \
                and not lines[i].lstrip().startswith(("- ", "* ")):
            para.append(lines[i].strip())
            i += 1
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para)))

    return "\n".join(out)


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------

def build_schema(meta, ctx, url):
    graph = []
    title = meta.get("title", "")
    desc = meta.get("description", "")

    article = {
        "@type": "TechArticle",
        "@id": url + "#article",
        "headline": meta.get("headline", title),
        "name": title,
        "description": desc,
        "inLanguage": "en-US",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "url": url,
        "isPartOf": {"@type": "WebSite", "@id": SITE + "/#website"},
        "publisher": {"@type": "Organization", "@id": SITE + "/#org"},
        "datePublished": meta.get("published", str(date.today())),
        "dateModified": meta.get("updated", str(date.today())),
    }
    terms = [(s_, l) for s_, l in as_pairs(meta, "terms") if s_ in ctx["ids"]]
    if terms:
        article["about"] = [
            {
                "@type": "DefinedTerm",
                "@id": "%s#%s" % (url, slug),
                "name": label,
                "termCode": slug,
                "url": "%s#%s" % (url, slug),
                "inDefinedTermSet": {
                    "@type": "DefinedTermSet",
                    "@id": SITE + "/guides/#dictionary",
                    "name": "BMX Parts Depot A-Z Parts Glossary",
                    "url": SITE + "/guides/",
                },
            }
            for slug, label in terms
        ]
    graph.append(article)

    if ctx["faqs"]:
        graph.append({
            "@type": "FAQPage",
            "@id": url + "#faq",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f["q"],
                    "url": "%s#%s" % (url, f["id"]),
                    "acceptedAnswer": {"@type": "Answer", "text": f["a"]},
                }
                for f in ctx["faqs"]
            ],
        })

    for v in ctx["videos"]:
        graph.append({
            "@type": "VideoObject",
            "@id": "%s#video-%s" % (url, v["id"]),
            "name": v["title"],
            "description": v["caption"] or v["title"],
            "embedUrl": "https://www.youtube-nocookie.com/embed/" + v["id"],
            "contentUrl": "https://www.youtube.com/watch?v=" + v["id"],
            "thumbnailUrl": "https://i.ytimg.com/vi/%s/hqdefault.jpg" % v["id"],
            "uploadDate": v.get("uploaded", meta.get("updated", str(date.today()))),
        })

    for im in ctx["images"]:
        src = im["src"]
        full = src if src.startswith("http") else SITE + "/" + src.lstrip("/")
        graph.append({
            "@type": "ImageObject",
            "@id": "%s#image-%s" % (url, slugify(im["title"])),
            "name": im["title"],
            "caption": im["caption"],
            "contentUrl": full,
            "url": full,
        })

    graph.append({
        "@type": "BreadcrumbList",
        "@id": url + "#crumbs",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Fitment Guide", "item": SITE + "/guides/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": url},
        ],
    })

    return {"@context": "https://schema.org", "@graph": graph}


# --------------------------------------------------------------------------
# page shell
# --------------------------------------------------------------------------

def nav_html(active=""):
    def cur(key):
        return ' aria-current="page"' if active == key else ""
    return """<header class="nav">
  <div class="wrap">
    <a class="wordmark" href="/"><img src="/assets/logo.png" width="1302" height="160" alt="BMX Parts Depot"></a>
    <div class="links">
      <a class="lnk" href="/#stock">What We Stock</a>
      <a class="lnk"%s href="/guides/">Fitment Guide</a>
      <a class="lnk" href="/#process">Our Process</a>
      <a class="lnk" href="/#contact">Contact</a>
      <a class="btn sm" href="%s" target="_blank" rel="noopener">
        <span class="hide-xs">Shop on&nbsp;</span>eBay
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
      </a>
      <button class="nav-toggle" type="button" id="navToggle" aria-expanded="false" aria-controls="navPanel" aria-label="Open menu">
        <svg class="ico-open" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><line x1="3" y1="7" x2="21" y2="7"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="17" x2="21" y2="17"/></svg>
        <svg class="ico-close" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><line x1="5" y1="5" x2="19" y2="19"/><line x1="19" y1="5" x2="5" y2="19"/></svg>
      </button>
    </div>
  </div>
  <nav class="nav-panel" id="navPanel" aria-label="Main menu" hidden>
    <a href="/#stock">What We Stock</a>
    <a href="/guides/">Fitment Guide</a>
    <a href="/#process">Our Process</a>
    <a href="/#contact">Contact</a>
  </nav>
</header>
<div class="nav-scrim" id="navScrim" aria-hidden="true"></div>""" % (cur("guides"), EBAY)


def footer_html(top_guides):
    links = "".join(
        '<a href="/guides/%s/">%s</a>' % (s, html.escape(t)) for s, t in top_guides
    )
    return """<footer class="site">
  <div class="wrap">
    <div class="cols">
      <div>
        <a class="wordmark" href="/"><img src="/assets/logo.png" width="1302" height="160" alt="BMX Parts Depot"></a>
        <p class="tagline">Used BMX parts, honestly priced.</p>
      </div>
      <div>
        <p class="col-title">BMX Knowledge Base</p>
        <nav>
          <a href="/guides/">Fitment Guide</a>
          %s
        </nav>
      </div>
      <div>
        <p class="col-title">Shop</p>
        <nav>
          <a href="%s" target="_blank" rel="noopener">eBay Store</a>
          <a href="/#stock">What We Stock</a>
          <a href="/#process">Our Process</a>
          <a href="/#contact">Contact</a>
        </nav>
      </div>
      <div>
        <p class="col-title">Site</p>
        <nav>
          <a href="/privacy.html">Privacy Policy</a>
          <a href="/terms.html">Terms of Use</a>
          <a href="/llms.txt">llms.txt</a>
          <a href="/sitemap.xml">Sitemap</a>
        </nav>
      </div>
    </div>
    <div class="bottom">
      <span>&copy; <span id="yr">%s</span> BMX Parts Depot. All rights reserved.</span>
      <span>Specs are checked against manufacturer sources. Measure before you buy.</span>
    </div>
  </div>
  <script>document.getElementById('yr').textContent=new Date().getFullYear()</script>
</footer>""" % (links, EBAY, date.today().year)


HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="theme-color" content="#0a0a0a">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{site}/assets/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css_href}">
<script type="application/ld+json">
{schema}
</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{nav}
"""


ROOTREL_RE = re.compile(r'\b(href|src)="/(?!/)')


def relativise(page, base):
    """Rewrite root-relative href/src to page-relative.

    Absolute /assets/... paths are correct once the site is served from the
    domain root, but they break when a page is opened straight off disk or
    served from a subdirectory: the browser resolves them against the
    filesystem root and the stylesheet and script silently never load. The
    page still renders as unstyled HTML, so it looks like the search box is
    broken rather than like the script is missing.

    Rewriting to a relative base makes every context work, production
    included. Full URLs (canonical, og:url, eBay) start with https and are
    untouched, as are protocol-relative //.
    """
    return ROOTREL_RE.sub(lambda m: '%s="%s' % (m.group(1), base), page)


def era_row(eras):
    if not eras:
        return ""
    pills = []
    for e in eras:
        if e not in ERA_LABELS:
            continue
        name, span = ERA_LABELS[e]
        label = "%s%s" % (name, (" " + span) if span else "")
        pills.append('<span class="era era-%s">%s</span>' % (e, html.escape(label)))
    if not pills:
        return ""
    return '<div class="era-row">%s</div>' % "".join(pills)


# --------------------------------------------------------------------------
# pillar pages
# --------------------------------------------------------------------------

def build_pillar(path, all_pillars, top_guides):
    src = open(path, encoding="utf-8").read()
    meta, body = split_front(src)
    slug = meta.get("slug") or os.path.splitext(os.path.basename(path))[0]
    url = "%s/guides/%s/" % (SITE, slug)

    ctx = {"toc": [], "faqs": [], "videos": [], "images": [], "todo": [],
           "seen_qa": False, "ids": set(), "dupe_ids": []}
    main = render(body, ctx)

    toc = ""
    if ctx["toc"]:
        items = "".join(
            '<li><a href="#%s">%s</a></li>' % (a, html.escape(t)) for a, t in ctx["toc"]
        )
        toc = ('<aside class="toc"><p class="toc-label">On this page</p>'
               '<ol>%s</ol></aside>' % items)

    related = ""
    rel = as_pairs(meta, "related")
    if rel:
        cards = "".join(
            '<a class="xlink" href="/guides/%s/"><span class="xl-kind">Pillar Guide</span>'
            '<span class="xl-name">%s</span></a>' % (s, html.escape(t)) for s, t in rel
        )
        related = ('<div class="xlinks"><h2>Related guides</h2>'
                   '<div class="xlink-grid">%s</div></div>' % cards)

    schema = json.dumps(build_schema(meta, ctx, url), indent=2, ensure_ascii=False)

    head = HEAD.format(
        title=html.escape(meta.get("title", ""), quote=True),
        description=html.escape(meta.get("description", ""), quote=True),
        url=url, site=SITE, schema=schema, nav=nav_html("guides"),
        css_href=versioned("/assets/guide.css"),
    )

    page = head + """
<section class="guide-head">
  <div class="wrap">
    <p class="crumbs"><a href="/">Home</a><span aria-hidden="true">/</span><a href="/guides/">Fitment Guide</a><span aria-hidden="true">/</span>{short}</p>
    <p class="eyebrow">{eyebrow}</p>
    <h1 class="display">{h1}</h1>
    <p class="standfirst">{standfirst}</p>
    {eras}
  </div>
</section>

<div class="guide-body">
  <div class="wrap guide-grid">
    <main id="main">
      <article class="guide">
{main}
{related}
      </article>
    </main>
    {toc}
  </div>
</div>
{footer}
<script src="{js_href}" defer></script>
</body>
</html>
""".format(
        short=html.escape(meta.get("short", meta.get("title", ""))),
        eyebrow=html.escape(meta.get("eyebrow", "Pillar Guide")),
        h1=html.escape(meta.get("h1", meta.get("title", ""))),
        standfirst=inline(meta.get("standfirst", meta.get("description", ""))),
        eras=era_row(as_list(meta, "eras")),
        main=main, related=related, toc=toc, footer=footer_html(top_guides),
        js_href=versioned("/assets/guide.js"),
    )

    outdir = os.path.join(OUT, slug)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(relativise(page, "../../"))

    return {
        "slug": slug, "meta": meta, "url": url,
        "sections": ctx["toc"], "faqs": len(ctx["faqs"]),
        "todo": ctx["todo"],
        "terms": as_pairs(meta, "terms"),
        "dupe_ids": ctx["dupe_ids"],
        "ids": ctx["ids"],
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    if not os.path.isdir(CONTENT):
        print("no content/ directory", file=sys.stderr)
        return 1

    files = sorted(
        os.path.join(CONTENT, "pillars", f)
        for f in os.listdir(os.path.join(CONTENT, "pillars"))
        if f.endswith(".md") and not f.startswith("_")
    )

    metas = []
    for p in files:
        m, _ = split_front(open(p, encoding="utf-8").read())
        metas.append((m.get("slug", ""), m.get("short", m.get("title", "")), m))
    top_guides = [(s, t) for s, t, _ in metas][:5]

    pages = [build_pillar(p, metas, top_guides) for p in files]

    # hub + root files are written by their own modules
    from buildhub import write_hub, write_root_files
    write_hub(pages, top_guides, nav_html, footer_html, HEAD, SITE)
    write_root_files(pages, SITE, ROOT)

    todo_total = sum(len(p["todo"]) for p in pages)
    print("built %d pillar pages" % len(pages))
    for p in pages:
        print("  %-42s %2d sections  %2d faqs  %2d placeholders"
              % (p["slug"], len(p["sections"]), p["faqs"], len(p["todo"])))
    print("%d placeholders awaiting Joe (caliper readings, video ids, diagrams)" % todo_total)

    dupes = [(p["slug"], a) for p in pages for a in p.get("dupe_ids", [])]
    if dupes:
        print("  DUPLICATE SECTION IDS (the second one is unreachable):")
        for slug, a in dupes:
            print("    %-42s #%s" % (slug, a))
    return 0


if __name__ == "__main__":
    sys.exit(main())
