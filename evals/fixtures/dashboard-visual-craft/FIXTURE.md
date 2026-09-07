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

The page is deliberately *not* broken in the ways other skills own. Its colours are legible on
their ground, its chart form suits the comparison, and its panels are in a defensible order. A
run that reports those instead of the faults below has routed to the wrong skill.

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
