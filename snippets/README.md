# Paste-in snippets

Self-contained HTML blocks for use **outside** this site, mainly inside eBay item
descriptions. Everything here carries inline styles, because eBay strips external
stylesheets and `<style>` blocks. That is why these look more verbose than the
markup used on the guide pages.

On the site itself, do not use these. Use the `::: fitbadge` and `::: ebay`
directives in the content files, which produce the same thing driven by
`assets/guide.css`.

## Files

- `fitment-badge.html` - one compatibility badge linking an eBay listing back to
  the guide section that answers the buyer's fitment question. Six variants, one
  per common question.
- `preview.html` - open in a browser to see all of them rendered.

## Using a badge in an eBay listing

1. Pick the badge matching the part you are listing.
2. Copy the block from `fitment-badge.html`.
3. In the eBay listing editor, switch the description to HTML view and paste it
   at the bottom of the description.
4. Change the `href` if a different guide section fits better.

## Rules

Links out of eBay listings are allowed only to pages that inform the buyer, not
to a competing storefront. These point at reference content with no checkout on
it, which is the point, but eBay's policy is the authority and it changes.
Check the current version of their links policy before doing this at scale.

Keep the copy factual. The badge says what the part is and where to read about
fitment. It should not promise fit, because only the buyer can measure their own
frame.
