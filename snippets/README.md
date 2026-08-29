# Paste-in snippets

Self-contained HTML blocks for use **outside** this site, mainly inside eBay item
descriptions. Everything here carries inline styles, because eBay strips external
stylesheets and `<style>` blocks. That is why these look more verbose than the
markup used on the guide pages.

On the site itself, do not use these. Use the `::: fitbadge` and `::: ebay`
directives in the content files, which produce the same thing driven by
`assets/guide.css`.

## Files

- `fitment-badge.html` - seven fitment note blocks, one per common buyer
  question. They answer the question in the listing. They contain no links and
  no domain name, on purpose. See the rule below.

## The link rule: do not link out of an eBay listing

eBay's links policy permits links in an item description **only** to:

- other eBay pages (Messages, other items, Stores pages, Follow Seller)
- product videos
- eBay-approved freight shipping services
- legally required information

A link to bmxpartsdepot.com is none of those. Stated enforcement is listing
removal, a warning, restricted activity, or account suspension. The same policy
also bars a store name that reads as a web address, including one containing
`.com`.

An earlier version of `fitment-badge.html` linked each block back to a guide
section. That was a mistake and it has been removed. Do not restore it. If the
policy ever changes, read the current version first:

https://www.ebay.com/help/policies/listing-policies/links-policy?id=4248

## Why these blocks are still worth pasting

They are not a traffic play any more. They earn their place in the listing:

- fewer "will this fit my bike" messages before a sale
- fewer returns from buyers who guessed wrong on a bore or an axle size
- real BMX vocabulary in the description, which eBay's own search indexes
- an invitation to message, which is a permitted and useful thing to ask for

## Using a block

1. Pick the block matching the part you are listing.
2. Copy it from `fitment-badge.html`.
3. In the eBay listing editor, switch the description to HTML view and paste it
   at the bottom of the description.

## Rules

Keep the copy factual. The block says what the part is and what the buyer should
measure. It must not promise fit, because only the buyer can measure their own
frame.

Do not add a link, a domain name, a logo carrying a domain, or a watermark
carrying one.
