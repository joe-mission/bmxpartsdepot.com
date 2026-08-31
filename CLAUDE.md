# bmxpartsdepot.com

Static site for BMX Parts Depot, a used and mid-school BMX parts seller based in
Maryland. Sales happen on eBay. This site exists to look legitimate, route people
to the eBay store, and answer the fitment question that comes before a purchase.

It started as a one-pager and is now fifteen pages plus two games: the home page,
two legal pages, the guides hub, ten pillar guides and the standalone BMX FAQ.

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
content/pages/*.md      standalone pages. Same renderer, same directives, but
                        they land at the site root rather than under /guides/
                        and stay out of the ten-card grid. /bmx-faq/ is one.
content-plan/terms.tsv  THE TERM REGISTRY. Single source of truth for the A-Z.
content-plan/   planning docs: the old A-Z dictionary (superseded, kept as the
                research record), the 100 questions, the verified spec
                research, the asset query sheet. Not published.
guides/         GENERATED OUTPUT. Never hand-edit, build.py overwrites it.
assets/guide.css        shared stylesheet for guide pages only
assets/guide.js         progressive enhancement for guide pages only
assets/video/           card clips, captured from the two games. See below.
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
registry, a claimed slug still marked `planned`, a `href="#x"` with no matching
id on that page, or escaped block markup shipping as visible text. Each one ships a page that
looks fine and is quietly broken, and as warnings they simply scrolled past.

Pass `--allow-warnings` while a term is half-written. It is for work in
progress, not for pushing.

**A `::: needsverify` block is NOT a defect and never fails the build.** It is
the opposite: someone went looking, could not source the figure, and published
the hole rather than a plausible number. For some figures that is permanent. No
BMX brand publishes a casing TPI or a Shore A durometer for its tires, so those
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

Raw HTML passes through at **block** level only, and that now includes block
HTML inside a directive body. `render_prose()` handles paragraphs, raw blocks
and lists, and both `::: quickanswer` and `::: faq` use it, so a spec table
written inside a directive renders the same as one written at the top level.
It did not always: directive bodies split on blank lines and ran every piece
through `inline()`, which escaped a whole table into visible markup on the FAQ
page, where the table was the answer.

Inside a paragraph everything is still escaped, with two exceptions:
backticked code, and a sourcing badge. The badge
exception exists because the honest-hole pattern ends a sentence with one:

```
No manufacturer publishes it. <span class="src src-conflict">Unpublished</span>
```

Without the exception that shipped as visible markup text to readers, which it
did on nine pages until it was caught. `SRC_BADGE_RE` in `build.py` matches that
span and only that span: the three known classes, a short plain-text label, no
attributes. Any other tag mid-paragraph still escapes, deliberately.

**Four badge styles, and the difference between the last two matters.**

| class | reader sees | meaning |
|---|---|---|
| `src-confirmed` | Confirmed | two or more independent sources agree |
| `src-single` | Single source | one source |
| `src-conflict` | Sources vary | sources disagree; the page gives the range |
| `src-gap` | Unpublished / Unverified | nobody publishes it |

The class names are internal and the labels are what ships. `src-conflict`
used to render as "Conflicting", which read as an error state rather than as
information about the industry. The label changed; the disclosure did not.
Do not resolve one of these by picking a single number.

`src-gap` exists because those twenty badges used to wear the conflict orange.
Twenty-seven orange badges read as a site full of disagreement when only seven
were, and the mislabelling ran downstream: the derivation checks
`src-conflict` first, so ten terms with perfectly good sources plus one
unsourceable figure were being recorded as `conflict` in the registry. Fixing
the style fixed the coverage table too, and conflict fell from thirteen terms
to three.

`src-gap` is slate rather than an alarm colour, deliberately. A figure that was
looked for and not found is an honest state, not a warning.

A `## Heading {#anchor}` whose anchor matches a registry slug is what makes the
hub's A-Z link deep-link into that section. Claiming a term in frontmatter without
writing the matching section means the hub links to the page instead, and the
build says so.

New sections are currently appended after `## Questions` rather than before it,
so the FAQ sits mid-page on four pillars. Cosmetic, pre-existing, and worth
fixing in one pass rather than per batch.

### Standalone pages, and why they are not pillars

`content/pages/*.md` builds with the same `build_pillar` function and the same
directives, with `standalone=True`. The difference is where it lands and what
it is left out of: the site root rather than `/guides/`, and deliberately kept
out of the `pages` list that drives the ten-card grid, the home grid and the
pillar numbering. It still reaches `sitemap.xml`, `llms.txt` and every build
gate.

This exists because the Ten Master Guides are load-bearing brand structure.
The blueprint turned down a Pillar 11 for that reason, and dropping a file
into `content/pillars/` would silently make an eleventh card appear.

`/bmx-faq/` is the first one. It answers buying questions, which sit a layer
above the fitment questions the pillars answer, and it links down into the
glossary rather than redefining anything.

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
defined identically on all fifteen pages (the two games carry none). Every TechArticle points its
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

### FAQ blocks and their schema

`::: faq Q01 | The question?` renders `<div class="faq-block" id="slug"><h3>`
with the answer as paragraphs, and the same call appends to `ctx["faqs"]`,
which becomes the page's `FAQPage` JSON-LD. One source, two outputs, so the
schema cannot drift from the rendered text. Use it rather than hand-writing a
schema block.

The pattern is a heading plus paragraphs, always visible, with no ARIA state.
That is deliberate and should not be swapped for `<details>`/`<summary>`:
there is no disclosure state for a screen reader to get wrong, and the direct
answer stays in the rendered view where a snippet can reach it.

Google switched FAQ rich results off on 7 May 2026 and removed the
documentation on 15 June 2026, so the JSON-LD no longer earns a SERP feature
for anyone. Keep emitting it, because other consumers read it and it costs
nothing, but do not build a page on the promise of FAQ rich results.

### Embedded video, and uploadDate

`::: video Title | youtube-id | uploaded-datetime`

The third field is the video's real upload time on YouTube, in full ISO 8601
with an offset. It is not decoration. **A video without one emits no
`VideoObject` at all**, which is the same rule the rest of this site applies to
any figure it cannot source.

That rule exists because the alternative shipped. `uploadDate` used to fall
back to the page's own `updated:` value, so all eleven embedded videos claimed
they were uploaded on the day the pages were last generated. Search Console
flagged two of them, and only for the format: a bare date carries no timezone.
The real problem was larger and quieter. Every one of the eleven dates was
false, and these are not our videos, they belong to Park Tool and The Basement
Bike Shop. Reformatting the fallback would have cleared the warning and left
the site asserting eleven things it had no basis for.

Omitting just `uploadDate` and keeping the object is not an option either. It
is required, so that trades a warning for an invalid item.

Real dates and their provenance are in `content-plan/verified-specs-bb.md`.

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
  data on all fifteen pages and the contact address in the legal pages. There is no
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

## The nav

Order is shop first, then reference:

```
What We Stock   Our Process   Contact   [separator]   Fitment Guide   BMX FAQ
```

The separator is a 9px checker diamond in neon cyan (`.nav-sep`), `aria-hidden`,
picking up the checkerboard motif from the games. The hamburger carries the same
order and its own `.nav-sep-h`, which needs `display:block` because the panel is
a block container and an inline span has no width to give.

**The row is tight and anything added to it needs re-measuring at 1280.** With
the separator in, it measured 810px into 784px and wrapped, which is why the gap
is 18px rather than 22px and why `.nav-sep` carries `margin:0 -4px`.

The nav lives in three places and all three have to move together:

| where | pages |
|---|---|
| `index.html` inline | home |
| `build.py` nav template plus `assets/guide.css` | hub, ten pillars, BMX FAQ |
| `privacy.html` and `terms.html` inline | the two legal pages |

That split is exactly how the nav drifted before: the reorder landed only on the
home page, the generated pages kept the old order, and privacy and terms were
still on the original one-pager's menu of What We Stock / Why Us / Contact with
no mobile menu at all. Below 820px those two showed a logo and an eBay button
and nothing else.

Their breakpoint is now 1200px like everything else. Five links plus the
separator need about 1200 before the row wraps, so at 820 they wrapped onto two
lines from 825 up to about 1100.

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
- No `localStorage`. **Google Analytics 4 (`G-RX3VR6S5CN`) is live site-wide** via
  `assets/analytics.js`, which is the only place the property ID appears. It sets
  cookies, so the old "no cookies, no analytics, deliberate" note is retired.
  There is still no consent banner. That is a live decision rather than an
  oversight: traffic is intended to be US, advertising features are off on the
  property, and the privacy page names GA4 as the single processor and points at
  Google's opt-out add-on. If the site starts drawing EU or UK traffic, revisit it.
- **The privacy page describes what the site actually does.** It used to carry
  inherited boilerplate naming Meta, LinkedIn and Microsoft as advertising
  partners, on a site that has never run an ad. Those are gone. If a processor is
  ever added, that page is part of shipping it.

## Local development

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000. That is the whole workflow. Opening the file with
`file://` also works but Google Fonts may behave differently.

## Known issues

- **Enforce HTTPS** may still be unticked in the repo's Pages settings. The
  certificate has issued and the site serves over HTTPS, so the toggle should be
  selectable now. Check Settings > Pages.
- **The domain publishes a null MX** (`0 .`), which says explicitly that it
  accepts no mail, alongside `v=spf1 -all` and a `p=reject` DMARC. Mail to any
  `@bmxpartsdepot.com` address bounces immediately and by design. If a real
  address is ever wanted there, the null MX has to come out first or nothing
  will arrive.
- **The logo is a raster image** now, `assets/logo.png`, wired into the nav and
  footer on every page. It is white on the right half, so it only works on dark
  backgrounds; every nav and footer on the site is dark, so that is fine today.
  It has no dark-on-light variant and no vector, which rules it out for eBay
  templates, packing material and anything printed.

## /bmx-exploded-view/, the spin game

A hand-written standalone page, not generated. It is a full-viewport three.js
canvas with `overflow:hidden` and fixed-position chrome, so putting it through
`build_pillar` would wrap it in the site shell and break its layout. It sits at
the repo root beside `index.html`, `privacy.html` and `terms.html`.

Two modes off one button: an exploded diagram naming 35 components, and a
fifteen second spin game. It lands in spin mode.

**three.js is self-hosted** at `assets/vendor/three.r128.min.js` rather than
loaded from cdnjs. The page has no error path if the library fails to load: it
is a silent black screen. This site otherwise has zero third-party runtime
dependencies, and a CDN outage taking out a page in the nav is not a trade
worth making for 590KB.

Two exits back to the site, because the panel that holds the first one is
hidden during a spin and spin mode is what loads first.

Its own fonts, deliberately unlike the rest of the site. It is a toy and reads
as one. The palette is no longer unrelated though: see the visual system below.

In `sitemap.xml` and `llms.txt` as of 29 August 2026.

## /bmx-wheelie-run/, the second game

Same shape as the spin game: a hand-written full-viewport three.js page at the
repo root, not generated. First person, balance the wheelie, steer the gates.

Both games follow the same rules and both were prepared the same way. Point at
`/assets/vendor/three.r128.min.js` rather than cdnjs, carry
`/assets/analytics.js`, and add a visible way back to the site, since a full
screen canvas has no other exit and people arrive on these from shared links.

**Neither game is in the nav.** They are reached from the "Two BMX Games"
section near the foot of the homepage and from the footer, and nowhere else.
That is deliberate: the nav was full at five full-phrase labels, and a games
section on the homepage is a better shop window than a nav item anyway. Both
"Back to BMX Parts Depot" links return to `/#games` rather than the top of the
home page, so leaving a game puts you back where you started.

Both are in `sitemap.xml` and `llms.txt` as of 29 August 2026.

Neither carries the site nav, and neither should. They are full-viewport and
have their own chrome.

## The visual system, and how the card clips are made

Both games and the home page hero share one look: a synthwave sunset over a
Vans-style checkerboard. Palette is `#150d3a` deep sky, `#b02f6b` magenta,
`#ff7a35` orange, `#ffb347` gold at the horizon, `#7ff0ff` neon cyan for the
horizon line, PLAY links and the nav separator.

`bmx-exploded-view` gets its backdrop from CSS behind the canvas, which works
because the renderer is `alpha:true` and the canvas is transparent. The floor is
one element with a `repeating-conic-gradient` under `perspective()` and
`rotateX()`, so it stays sharp at any size.

`bmx-wheelie-run` has the scene itself repainted: sky texture stops, `scene.fog`,
both lights, the verge material. Grading afterwards cannot work here, because a
tint over a blue sky is a tinted blue sky. One non-obvious thing: the warm end of
the sky ramp has to be pulled **up** into the visible band, because the camera
only ever sees the top of that 1024x512 texture and a sunset spread evenly over
0..1 puts the orange below the horizon where the ground plane hides it.

Both HUDs were built against a near-black page and stopped being legible over a
bright sky. Fixed with `text-shadow` on the floating readouts rather than
recolouring every element.

### Capturing the clips in `assets/video/`

They are captured from the live games. Two things are worth keeping:

**Never screen-record in real time.** Recording off a software GL renderer gives
unevenly spaced frames, which reads as choppy, and no re-encode recovers a
cadence the source never had.

**Fake the clock instead.** Replace `requestAnimationFrame` with a queue and
freeze `performance.now()` to a virtual time advanced by hand, so every frame is
exactly 1/60s of simulated time from the last. CSS animations ignore that clock,
so `document.getAnimations()` gets paused and its `currentTime` set per frame
too.

Both games wrap their code in an IIFE, so nothing is reachable from outside.
Drive them through public surfaces (real clicks, key presses, `PointerEvent`s),
or `page.route()` the HTML and inject a script between the three.js tag and the
game tag, where `THREE` exists but nothing is built yet.

Traps, all of which cost time once:

- `toDataURL('image/jpeg')` composites transparency onto **black**. Flatten onto
  an explicit colour first, or export PNG.
- Hiding parts must happen **after** the mode switch. Leaving spin mode calls
  `setBrakesVisible(true)` and silently undoes it.
- A perspective checkerboard aliases hard near the horizon; one sample per pixel
  turns the far field into noise. Supersample it.
- Constant rotation comes from the orbit drag handler with a fixed pointer delta
  per frame. The spin game's own velocity decays and the idle auto-rotation is
  far too slow. 3.74px per frame is exactly 2*PI over 240 frames, so the clip
  loops with no seam.

The cards play on scroll into view rather than on hover, phones included, with
`preload="none"` and load on first intersection. Source order is per clip:
whichever of webm/mp4 is smaller goes first, since browsers take the first they
can play.

**Measure contrast off the composited pixels, not the CSS.** Text over video is
not text over a known colour.

## Cross browser notes

Tested in Chromium across 320, 390, 768, 1280 and 1440. Firefox and WebKit
could not be installed in the sandbox that ran these checks, so Safari and
Firefox behaviour is reasoned from feature support rather than observed. If
you can run the site in real Safari, the two things worth looking at are the
blur behind the nav and the game panels, and whether game sound plays.

**Every `backdrop-filter` needs `-webkit-backdrop-filter` beside it.** Safari
still requires the prefix, and that includes every browser on iOS. The three
hand-written pages and `guide.css` always had it; both games arrived without
it and would have lost the blur on Mac and iPhone.

**An AudioContext must be resumed.** Safari creates one suspended unless it
is constructed inside a user gesture, and both games make sounds from their
run loop. Without `if (ctx.state === 'suspended') ctx.resume()` they are
silent on Safari and iOS permanently, with no error to notice.

**`.btn` is `white-space:nowrap`.** Right for short labels, wrong for long
ones: the FAQ call to action measured 473px inside a 350px column at 390px
wide and pushed the whole homepage into horizontal scroll. A long button
label needs a wrap rule at narrow widths. The no-horizontal-scroll rule is
checked at 320, 390, 768, 1280 and 1440, ignoring the skip link and anything
inside a `.table-scroll`, both of which overflow their parent by design.
