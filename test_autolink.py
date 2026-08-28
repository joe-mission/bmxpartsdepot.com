#!/usr/bin/env python3
"""Adversarial tests for the auto-linker.

    python3 test_autolink.py

The linker rewrites published prose without anyone reading the diff, so the
failure mode is quiet: a link lands inside a spec table or on the wrong word
and nobody notices for a month. These are the cases that would do that.

Standard library only, like everything else here. No pytest.
"""

import sys

import build

# A fake registry, so the tests do not move every time a real term is added.
REG = [
    {"slug": "cassette-hub", "term": "Cassette Hub", "status": "published",
     "home": "wheels", "definition": "", "letter": "C", "category": "wheels",
     "tier": "1", "relevance": "", "source_status": "solid", "related": []},
    {"slug": "u-brake", "term": "U-Brake", "status": "published",
     "home": "brakes", "definition": "", "letter": "U", "category": "brakes",
     "tier": "1", "relevance": "", "source_status": "solid", "related": []},
    {"slug": "chromoly", "term": "Chromoly (4130)", "status": "published",
     "home": "frame", "definition": "", "letter": "C", "category": "frame",
     "tier": "1", "relevance": "", "source_status": "solid", "related": []},
    {"slug": "half-link-chain", "term": "Half Link", "status": "planned",
     "home": "drivetrain", "definition": "", "letter": "H", "category": "drivetrain",
     "tier": "1", "relevance": "", "source_status": "risk-low", "related": []},
    {"slug": "cassette-driver", "term": "Driver", "status": "published",
     "home": "wheels", "definition": "", "letter": "D", "category": "drivetrain",
     "tier": "1", "relevance": "", "source_status": "solid", "related": []},
]

FAILURES = []


def check(name, got, want):
    if got != want:
        FAILURES.append("%s\n     got:  %s\n     want: %s" % (name, got, want))


def link(html, page="other"):
    return build.autolink(html, page, REG)


def main():
    # --- the basic case ---------------------------------------------------
    out, n = link("<p>A cassette hub is one option.</p>")
    check("links a first mention", out,
          '<p>A <a href="/guides/wheels/#cassette-hub" class="xterm">cassette hub</a>'
          ' is one option.</p>')
    check("counts it", n, 1)

    # --- first mention only ----------------------------------------------
    out, n = link("<p>A cassette hub. Another cassette hub.</p>")
    check("second mention untouched", out.count("xterm"), 1)

    # --- skip zones -------------------------------------------------------
    for zone, html in [
        ("heading", "<h2>The cassette hub</h2>"),
        ("table", "<table><tr><td>cassette hub</td></tr></table>"),
        ("code", "<p><code>cassette hub</code></p>"),
        ("existing link", '<p><a href="/x">a cassette hub</a></p>'),
        ("caliper block", '<aside class="caliper"><p>cassette hub</p></aside>'),
        ("ebay card", '<div class="ebay-card"><p>cassette hub</p></div>'),
        ("toc", '<aside class="toc"><li>cassette hub</li></aside>'),
    ]:
        out, n = link(html)
        check("never links inside a %s" % zone, (out, n), (html, 0))

    # --- attributes are not text -----------------------------------------
    # The bug a naive regex over the whole document always has.
    html = '<p data-term="cassette hub">Nothing here.</p>'
    out, n = link(html)
    check("never rewrites an attribute value", (out, n), (html, 0))

    html = '<img alt="a cassette hub on a bench">'
    out, n = link(html)
    check("never rewrites an alt attribute", (out, n), (html, 0))

    # --- leaving a skip zone restores linking -----------------------------
    out, n = link("<table><tr><td>cassette hub</td></tr></table><p>cassette hub</p>")
    check("links again after the table closes", n, 1)
    check("and only outside it", out.index("xterm") > out.index("</table>"), True)

    # --- self-linking -----------------------------------------------------
    out, n = link("<p>A cassette hub.</p>", page="wheels")
    check("a page never links a term it owns", n, 0)

    # --- planned terms ----------------------------------------------------
    out, n = link("<p>A half link is useful.</p>")
    check("planned terms have no section, so no link", n, 0)

    # --- stoplist ---------------------------------------------------------
    out, n = link("<p>The driver of the car.</p>")
    check("stoplisted everyday words are left alone", n, 0)

    # --- word boundaries --------------------------------------------------
    out, n = link("<p>The u-brakes were fine.</p>")
    check("matches a simple plural", n, 1)
    out, n = link("<p>Talk of cassette hubbery.</p>")
    check("does not match inside a longer word", n, 0)
    out, n = link("<p>A non-cassette hub.</p>")
    check("does not match across a hyphen boundary", n, 0)

    # --- names that break \b ---------------------------------------------
    out, n = link("<p>Made from Chromoly (4130) tubing.</p>")
    check("matches a name ending in a bracket", n, 1)

    # --- case is preserved ------------------------------------------------
    out, _ = link("<p>Cassette Hub and cassette hub.</p>")
    check("keeps the author's capitalisation", ">Cassette Hub</a>" in out, True)

    # --- whitespace across a line break -----------------------------------
    out, n = link("<p>A cassette\n  hub here.</p>")
    check("matches across a line break", n, 1)

    # --- longest match wins ----------------------------------------------
    out, _ = link("<p>Chromoly (4130) is the good stuff.</p>")
    check("no partial-name link left behind", out.count("xterm"), 1)

    # --- the cap ----------------------------------------------------------
    body = "".join("<p>A cassette hub, a u-brake, Chromoly (4130).</p>"
                   for _ in range(40))
    _out, n = link(body)
    check("respects the per-page cap", n <= build.AUTOLINK_MAX, True)

    # --- malformed input does not explode ---------------------------------
    for junk in ["<p>unclosed cassette hub", "<p><b>cassette hub</p>",
                 "cassette hub", "", "<<>><p>cassette hub</p>"]:
        try:
            link(junk)
        except Exception as exc:                       # noqa: BLE001
            FAILURES.append("crashed on %r: %s" % (junk, exc))

    if FAILURES:
        print("FAIL (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - " + f)
        return 1
    print("auto-linker: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
