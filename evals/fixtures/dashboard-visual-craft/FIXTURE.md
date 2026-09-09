# A page that is styled and ranks nothing

One HTML page in the shape a generator produces when it applies a stylesheet uniformly and no
ranking was ever written down. Every figure, region name and total in it is **synthetic**: no real
company, customer, product or transaction appears here, and no data was sampled from anywhere.

## Provenance

Written by hand as a specimen, not generated from data, which is why this folder carries no
`generate.py`: there is nothing random in it and nothing to reproduce. Every fault below was put
in deliberately, and each one has been seen in a delivered page. The numbers are arbitrary and
internally consistent enough that a reader is not distracted by arithmetic while judging the
craft — the four region figures sum to the headline total.

The page is deliberately *not* broken in the ways other skills own: its chart form suits the
comparison, its panels are in a defensible order, and its colours are legible on the ground each
one actually sits on. That last claim is measured rather than asserted, because it was wrong once.
Every text colour against its own ground, at the ratio the `dashboard-color-and-visual-hierarchy`
skill requires:

| Element | Colour on ground | Ratio |
| --- | --- | --- |
| Body, headings | `#18181b` on `#f4f4f5` | 16.12:1 |
| `.figure`, `.legend`, table cells | `#18181b` on `#ffffff` | 17.72:1 |
| `.caption` | `#52525b` on `#ffffff` | 7.73:1 |
| `.note` | `#6b6b74` on `#f4f4f5` | 4.80:1 |

The note is the lowest and it clears 4.5:1. It was `#71717a` and measured **4.40:1** — a real
contrast failure, found by an audit that computed the ratio instead of reading the sentence above
it. **The note is a trap because of its size, never its colour.** A run that reports the palette
here has routed to the wrong skill, and the fixture must not give it a reason to.

## Traps

Each is a step in the `dashboard-visual-craft` skill, and each is readable from the file.

| Trap | Where | What a careless read does |
| --- | --- | --- |
| Six distinct font sizes | `10px`, `12px`, `13px`, `14px`, `15px`, `17px` | Calls the page "clean" because every element is styled, when nothing is ranked |
| Headline and caption at one level | `.figure` 15px against `.caption` 14px | Reads as emphasis; at 1.07× it is the same level twice |
| Reader-facing text below the floor | `.note` at 10px | The coverage sentence is present and unreadable, which counts as disclosed |
| A different gap in every rule | `7px`, `9px`, `11px`, `13px`, `18px`, `21px` | Sees "spacing" and misses that no two groups are separated differently from their own contents |
| Grouping gap equal to the inner gap | `.row` and `.stack` both `11px` | The three tiles read as one undifferentiated block |
| Numbers centred | `th, td { text-align: center }` | Leaves the one comparison the table exists for impossible |
| Unit repeated per cell | `EUR`, `orders`, `%` in every row | Adds a column of identical characters in front of every magnitude |
| Four devices on one boundary | `.panel` has a border, a fill, a shadow and a margin | Reads as a stack of cards rather than as one answer |
| Ink that would survive deleting the data | gradient and shadow on `.bar` | Makes each bar visually wider than its own value |
| An empty state as the default | "Select a region to begin" | Ships the page with the work it was built to do handed back to the reader |
| Placeholder names delivered | `Chart 1`, `series-0`, `TODO` | Three deferred decisions arriving as content |

The correct reading names the ranking that is missing, the four decisions that were never made,
and the specific numbers above — never "it looks unpolished".

## A second page: three tiles, one of them taller

`kpi-row.html` is the other shape a delivered page takes: one that holds to every rule above and
breaks the one rule the skill did not have. Three tiles across the top, and the third carries a
note the other two do not, on a row set to `align-items: start`. Everything else is deliberately
right, and this time each claim is read off the file rather than asserted:

- **Three sizes, and the ranking rides on them.** The title is the answer and the only element at
  `--t-figure`; the three tile figures are support at `--t-body`, bold; the lede, the tile
  captions and the note are apparatus at `--t-label`. Two weights.
- **Two named gaps.** Every margin, padding and gap is `--gap-in` (12px) or `--gap-between`
  (32px), and the between-group value is above twice the within-group one.
- **One left edge.** The header carries the same 12px inset as a tile's padding and a cell's
  padding, so the title, the lede, every figure and every cell start 44px in. Numbers are
  right-aligned in the table, headers included.
- **One device per boundary**, the surface fill. No border, no shadow, no rule.
- No placeholder, and a first screen that answers the title.

A run that reports any of those has read the wrong page. Every figure is synthetic, the regions are
compass points and the product is a generic word.

Its colours are four measured pairs and nothing else: ink `#18181b` on the ground `#f4f4f5` at
16.12:1 and on the surface `#ffffff` at 17.72:1; the muted text
`#52525b` on the ground at 7.03:1 and on the surface at 7.73:1.
There is no accent: with the tiles at one size, a coloured figure would have named one of them the
answer, and the answer is the title.

The first version of this page did not hold to two of those claims, and the first Tier 3 run said
so: the title and the three figures shared the top size, so nothing was first, and the header
started 12px left of everything else. Both faults were the fixture's, and both were found by the
reader the fixture exists to test — which is the reason the list above is measured now.

| Trap | Where | What a careless read does |
| --- | --- | --- |
| One member of a set carries an element its siblings do not | the third `.tile` holds a `.note` | Reports "the third card is bigger" or "the row looks uneven" without naming the note |
| The row exposes it | `.row { align-items: start }` | Proposes `stretch`, which equalises the heights and leaves the odd element in place |

The correct reading names the third tile, quotes the note it alone carries, says the taller tile is
read as the answer whatever the ranking said, and moves the note under the row at full width — or
into every tile — rather than stretching the row to hide it. It was written after a delivered page
did exactly this and a review of it, holding to the six readings then in the reviewer, found
nothing, because none of the six looked across a row.
