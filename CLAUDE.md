# bmxpartsdepot.com

Static one-page marketing site for BMX Parts Depot, a used and mid-school BMX parts
seller based in Maryland. Sales happen on eBay. This site exists to look legitimate
and route people to the eBay store.

## Stack

Still no framework and no bundler. If a change seems to call for one, it doesn't.

The three original pages are hand-written and fully self-contained: all CSS in a
`<style>` block, all JS in a `<script>` block at the end of body.

The guide section is generated, because eleven pages sharing one 30KB stylesheet
should not inline it eleven times. `build.py` reads Markdown from `content/` and
writes plain HTML into `guides/`. Python 3 standard library only, no
package.json, no node_modules, nothing to install.

```
index.html      the one-pager
privacy.html    privacy notice, text carried over verbatim from the old site
terms.html      terms of use, same
CNAME           written by GitHub Pages, contains bmxpartsdepot.com. Do not delete.

build.py        the generator. Run it, commit what it writes, push.
buildhub.py     hub page, sitemap.xml, robots.txt, llms.txt. Imported by build.py.
schema_terms.py DefinedTerm generation and validation. Run it directly for a report.
test_autolink.py  adversarial tests for the auto-linker. Run after touching it.
content/pillars/*.md    the ten pillar guide sources. Edit these, not the HTML.
content-plan/terms.tsv  THE TERM REGISTRY. Single source of truth for the A-Z.
content-plan/   planning docs: the old A-Z dictionary (superseded, kept as the
                research record), the 100 questions, the verified spec
                research, the asset query sheet. Not published.
guides/         GENERATED OUTPUT. Never hand-edit, build.py overwrites it.
assets/guide.css        shared stylesheet for guide pages only
assets/guide.js         progressive enhancement for guide pages only
snippets/       paste-in HTML for eBay item descriptions, inline-styled
sitemap.xml robots.txt llms.txt    GENERATED. Do not hand-edit.
```

### Working on the guides

```bash
python3 build.py        # regenerate everything
python3 -m http.server 8000
```

**The build fails on defects.** `python3 build.py` exits non-zero on any of:
an unfilled caliper, video or diagram placeholder, a duplicate section id, a
term claimed with no matching section anchor, a claimed slug that is not in the
registry, or a claimed slug still marked `planned`. Each one ships a page that
looks fine and is quietly broken, and as warnings they simply scrolled past.

Pass `--allow-warnings` while a term is half-written. It is for work in
progress, not for pushing.

**A `::: needsverify` block is NOT a defect and never fails the build.** It is
the opposite: someone went looking, could not source the figure, and published
the hole rather than a plausible number. For some figures that is permanent. No
BMX brand publishes a casing TPI or a Shore A durometer for its tyres, so those
blocks are never going away, and the page is more honest for carrying them.

This was wrong for one commit, and the consequence is worth remembering: with
the build failing on them, the directive was unusable in a clean run, so the
honest answer got quietly rewritten as prose instead. A gate that punishes the
behaviour it exists to protect will be routed around, and the routing around
will look like a passing build.

The build counts them separately, as "figures published as visible holes".

Two pillars claiming one term is **not** a defect and stays a note. The
registry's `home` column decides which page owns the canonical section; the
second claim only affects which page the A-Z links to.

The build also prints coverage per category. `source_status` is **derived from
the sourcing badges on the pages**, never set by hand, so the table describes
what is published rather than what someone intended when the term was planned:

| value | meaning |
|---|---|
| `confirmed` | every badge in the term's section is Confirmed |
| `single` | weakest badge is Single source. A second source upgrades it. |
| `conflict` | publishes a conflict and gives the range. Correct, not a gap. |
| `review` | publishes figures with no badge of its own. Needs a human read. |
| `no-figure` | publishes no dimensional claim, so there is nothing to source |
| `wont-source` | can never be sourced. Set by hand. Era terms only. |

`review` is not automatically a defect. Some of those sections mention a figure
in prose and point at a badged table in a neighbouring section, which is fine.
Others have their own spec table whose last column is Notes where sources
should be, which is not. Telling them apart needs a person reading the page, so
the build flags them rather than guessing.

### Content source format

Markdown with `key: value` frontmatter and `:::` block directives. Raw HTML
passes through, so spec tables are authored as real HTML5 `<table class="spec-table">`.
See `content/pillars/01-bottom-brackets-and-spindles.md`, which is the format
model and the quality bar. Directives: `quickanswer`, `needsverify`, `caliper`,
`video`, `figure`, `faq`, `ebay`, `fitbadge`.

Raw HTML passes through at **block** level only. Inside a paragraph everything is
escaped, with two exceptions: backticked code, and a sourcing badge. The badge
exception exists because the honest-hole pattern ends a sentence with one:

```
No manufacturer publishes it. <span class="src src-conflict">Unpublished</span>
```

Without the exception that shipped as visible markup text to readers, which it
did on nine pages until it was caught. `SRC_BADGE_RE` in `build.py` matches that
span and only that span: the three known classes, a short plain-text label, no
attributes. Any other tag mid-paragraph still escapes, deliberately.

Three labels currently ride the `src-conflict` style: Unpublished, Unverified
and Conflicting. They mean different things and only the third is a conflict.
Worth splitting when someone touches this next.

A `## Heading {#anchor}` whose anchor matches a registry slug is what makes the
hub's A-Z link deep-link into that section. Claiming a term in frontmatter without
writing the matching section means the hub links to the page instead, and the
build says so.

New sections are currently appended after `## Questions` rather than before it,
so the FAQ sits mid-page on four pillars. Cosmetic, pre-existing, and worth
fixing in one pass rather than per batch.

### The term registry

`content-plan/terms.tsv` is the single source of truth for the glossary. Tab
separated, `#` comments, eleven columns. Add terms there first, then write the
section. `content-plan/az-dictionary.md` is superseded and no longer read.

Two columns do more work than they look like they do.

`status` is `published` or `planned`. A planned term is excluded from the A-Z,
from the schema and from the auto-linker, because it has no section and
therefore no anchor: publishing it would put a dead link in the glossary and an
unresolvable `@id` in the graph. Flipping status to `published` is the last step
of writing a term, not the first.

`letter` is which A-Z group the term files under, and it is editorial rather
than mechanical. The glossary files by concept keyword, so Wheel Dish sits
under D and Handlebar Backsweep under B. Do not derive it from the first
character of the name; that reshuffles about a third of the glossary.

`category` is one of the eight (drivetrain, frame, wheels, steering, brakes,
cockpit, vintage, hardware) and **a category is not a pillar**. Drivetrain
spans pillars 01, 04 and 05. Cockpit spans 08 and 09. Hardware is distributed
across all ten with a canonical home per term. `home` is the pillar that owns
the section; that is the column the build actually resolves links against.

### Structured data

Each pillar emits the `DefinedTerm` nodes for the terms it owns, on the page
that holds the anchor. The hub emits the `DefinedTermSet` they all point at,
without enumerating its members. Do not move the nodes back onto the hub: that
was 53% of that page's bytes at 104 terms and projected to 578KB at 1,000.

Only the owning page emits a node. Twelve terms are claimed by two pillars, and
before this rule both emitted a `DefinedTerm` with the same `termCode` and a
different `@id`. `home` decides which is canonical.

`python3 schema_terms.py` validates the lot and must report zero skipped and
zero problems.

**One Organization, one WebSite, one @id each.** `/#org` and `/#website`,
defined identically on all fourteen pages. Every TechArticle points its
`publisher` and `author` at `/#org`.

`index.html`, `privacy.html` and `terms.html` are hand-written, so nothing kept
their structured data in step with `site_entities()`. It drifted once: a block
was added to the homepage defining a second Organization at `/#organization`,
with a different logo, while every article kept pointing at the `/#org` the
homepage did not define. One business, two identities, and a crawler left to
pick.

`build.check_static_entities()` now fails the build if any of the three is
missing a node, has drifted from `site_entities()`, or reintroduces
`/#organization`. To regenerate the block after changing `site_entities()`:

```bash
python3 -c "import build; print(build.static_entity_block())"
```

Paste the output over the existing block in all three files. The build tells
you which ones are wrong.

### The auto-linker

`build.autolink` links the first mention of each glossary term to the section
that defines it. It runs on the rendered HTML, walking the tag stream rather
than regexing the document, so it never touches an attribute value.

It will not link inside a heading, table, existing link, code block, caliper
block, eBay card or the table of contents; it will not link a term the current
page owns; it will not link a planned term; and it stops at `AUTOLINK_MAX` per
page. `AUTOLINK_STOPLIST` holds terms whose display name is an everyday word
("Driver", "Neck", "Old School") where the first match on a page is reliably
the wrong sentence.

Run `python3 test_autolink.py` after changing any of it. A linker that is wrong
once in fifty is worse than no linker, because nobody reads the diff.

### Two cyans, deliberately

`--cyan` (#007bb0) is for light backgrounds. `--cyan-on-dark` (#00a4e6, the
original brand cyan) is for the same accent where it sits on ink: the hero
emphasis, eyebrows, footer link hover, and links inside a Quick Answer block.

One value cannot do both. #00a4e6 measures 2.82 against white, and #007bb0
measures 4.23 on #08090b. Swapping the single token fixed the light failures
and silently broke the dark ones, which the axe run caught and eyeballing
would not have.

When adding a cyan-on-dark rule, watch specificity. `article.guide a` is
(0,1,2) and beats a bare `.quick-answer a` at (0,1,1). Match the qualifier
rather than reaching for `!important`. The same trap once painted the eBay CTA
cyan on cyan.

## Hosting

GitHub Pages, deploy from `main` branch, root directory. Push to `main` and it
redeploys in about a minute. Live at https://bmxpartsdepot.com.

DNS is Cloudflare (Mission Agency account). Every record must stay **DNS only**, grey
cloud. Turning on the orange cloud breaks GitHub's certificate issuance and renewal,
and previously caused a Cloudflare error 1000 on www. If proxying is ever wanted, set
SSL mode to Full (strict) and re-add an `_acme-challenge` CNAME first.

Apex points at the four GitHub A records (185.199.108-111.153) plus the four AAAA
(2606:50c0:8000-8003::153). `www` is a CNAME to `joe-mission.github.io`.

## Brand

Carried over from the previous site, do not invent new values.

| Token | Value | Use |
|---|---|---|
| cyan | `#007bb0` | primary, links, accents, on light backgrounds |
| cyan on dark | `#00a4e6` | the same accent where it sits on ink |
| candy blue gradient | `#7fe4ff` → `#1cb9f7` → `#0083d8` | the "BMX" in the wordmark |
| orange | `#e64700` | secondary accent, ticker, contact CTA |
| deep blue | `#0032e6` | tertiary, used sparingly |
| ink | `#08090b` / `#0e1116` | dark sections |
| paper | `#f9fafb` / `#f0f2f4` | light sections |

Fonts: **Anton** for the wordmark, **Bebas Neue** for headings, **Inter** for body.
All three load from Google Fonts. Every stack has a real fallback; Impact and Arial
Narrow Bold stand in for the condensed faces.

Page rhythm alternates dark and light: dark nav and hero, orange ticker, light
category grid, dark value props, light process, dark contact, dark footer.

## Content rules

- The eBay store is **https://www.ebay.com/usr/bmx-parts-depot**. Note `usr`, not
  `str`, and the hyphenated handle. `str/bmxpartsdepot` is wrong and 404s.
- The eBay seller handle displayed on the page is `bmx-parts-depot`.
- Contact is a `mailto:` link to **`bmxpartsdepot@gmail.com`**, confirmed by Joe on
  29 August 2026. No hyphens. It is also the Organization `email` in the structured
  data on all fourteen pages and the contact address in the legal pages. There is no
  contact form and there should not be one; the site is static and has no backend.
- Two wrong addresses were live before that: `bmx-parts-depot@gmail.com` (hyphenated,
  a guess) on the contact button and in all the schema, and `info@bmxpartsdepot.com`
  in four places in the privacy notice, including the COPPA paragraph, on a domain
  with no MX records. Note that the hyphens belong to the eBay handle
  `bmx-parts-depot`, not to the email; that is where the guess came from.
- Never claim sales figures, review counts, customer numbers, or years in business.
  There is no data behind any of it and inventing it would be lying to buyers.

### Specifications: the rule that matters most

The guide section publishes dimensions people will spend money on. A wrong figure
is worse than a missing one.

- Every published figure carries its sourcing badge: `src-confirmed` (two or more
  independent good sources agree), `src-single` (one source), `src-conflict`
  (sources disagree, and the page says so and gives the range).
- If a number cannot be sourced, it goes in a `::: needsverify` block as a visible
  hole. It does not get written into a table with a confident badge.
- `content-plan/verified-specs-bb.md` is the research record: every claim, its
  source URL, and its status. Add to it rather than replacing it. Anything not in
  there has not been checked.
- **A standards number is not a source until someone has opened the standard.**
  Two got through: ISO 5681 cited for spoke gauge (it is crop protection
  vocabulary) and ISO 4210-2 cited sixteen times for component dimensions (it is
  a safety test standard whose introduction says it "specifically avoided
  standardization of components"). Both looked like the most authoritative
  source on the page, which is why neither was questioned. Prefer a manufacturer
  or retailer page someone can open in a browser.
- `::: caliper` blocks are for Joe's own bench measurements only. Never write
  a measurement into one. Fabricating first-hand shop data to look authoritative
  is exactly the kind of thing this site exists not to do.
- Era year ranges (old school, mid school, modern) are NOT sourced. Research
  could not trace them to any primary source. Describe eras by their features.
  Do not publish year boundaries, and note that the era chips deliberately carry
  no dates for this reason.
- Known traps, all found by checking rather than assuming: 3/8 inch is 9.525mm and
  is not a 10mm axle. Dropout spacing (110mm nominal) is not axle diameter (14mm).
  "24mm" spindle is 15/16 inch, 23.81mm. "19, 22, 24" is the complete spindle set
  for freestyle only, race adds 30mm and 35mm. American shell diameter has no
  single agreed figure.

## Writing style

Prose over bullets. Short and direct. No em dashes, use hyphens or parentheses.
Avoid ampersands in body copy unless the source text already uses one. Honest and
plain rather than salesy: "if something is cracked, bent, or sketchy, it does not get
sold" is the tone, not "premium quality guaranteed."

## Accessibility and robustness

- Everything must survive `prefers-reduced-motion: reduce`. There is a media query
  that kills all animation and forces revealed elements visible. Test any new
  animation against it.
- The hero headline lines use `overflow: hidden` for the rise-in reveal, and a
  `.done` class removes the clipping after 1.4s so a slow or failed webfont can never
  leave text permanently cut off. Preserve that if you touch the hero.
- Scroll reveals use IntersectionObserver with a non-IO fallback that just shows
  everything. Do not make content depend on JS to be readable.
- No horizontal scroll at any width down to 320px. Verify after layout changes.
- No `localStorage` or cookies. There is no analytics and no consent banner, which is
  deliberate.

## Local development

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000. That is the whole workflow. Opening the file with
`file://` also works but Google Fonts may behave differently.

## Known issues

- **Enforce HTTPS** may still be unticked in the repo's Pages settings, pending
  certificate issuance. Check Settings > Pages and enable it once selectable.
- **No MX records** exist on the domain, so mail to any `@bmxpartsdepot.com`
  address is still not delivered anywhere. Nothing on the site points at one now,
  but do not introduce one without setting up MX first.
- **The wordmark is CSS text**, not an image. A raster logo exists (heavy italic,
  distressed, blue-to-white two-tone) and is a better fit, but has not been wired in.
  If it is: it is white on the right half, so it only works on dark backgrounds. Every
  nav and footer on the site is dark, so that is fine today.
