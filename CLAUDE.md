# bmxpartsdepot.com

Static one-page marketing site for BMX Parts Depot, a used and mid-school BMX parts
seller based in Maryland. Sales happen on eBay. This site exists to look legitimate
and route people to the eBay store.

## Stack

There isn't one. Three hand-written HTML files, each fully self-contained: all CSS in
a `<style>` block, all JS in a `<script>` block at the end of body. No build step, no
package.json, no dependencies except a Google Fonts `<link>`.

Keep it that way. If a change seems to call for a framework or a bundler, it doesn't.

```
index.html      the one-pager
privacy.html    privacy notice, text carried over verbatim from the old site
terms.html      terms of use, same
CNAME           written by GitHub Pages, contains bmxpartsdepot.com. Do not delete.
```

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
| cyan | `#00a4e6` | primary, links, accents |
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
- Contact is a `mailto:` link, currently `bmx-parts-depot@gmail.com`. There is no
  contact form and there should not be one; the site is static and has no backend.
- The legal pages quote `info@bmxpartsdepot.com`. That address is inherited from the
  old site copy and is not currently receiving mail (see Known issues).
- Never claim sales figures, review counts, customer numbers, or years in business.
  There is no data behind any of it and inventing it would be lying to buyers.

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
- **No MX records** exist on the domain, so mail to `@bmxpartsdepot.com` is not
  delivered anywhere. The legal pages publish `info@bmxpartsdepot.com` regardless.
  This needs sorting separately from anything web-related.
- **The contact address is unconfirmed.** The old site had `bmxpartsdepot@gmail.com`
  obfuscated in its footer. The current value is a best guess.
- **The wordmark is CSS text**, not an image. A raster logo exists (heavy italic,
  distressed, blue-to-white two-tone) and is a better fit, but has not been wired in.
  If it is: it is white on the right half, so it only works on dark backgrounds. Every
  nav and footer on the site is dark, so that is fine today.
