# An operations page that grew by accretion

One JSON file describing a reporting page as it exists today: fourteen panels, six kinds, every
one of them the same size, positioned absolutely. Everything is **synthetic**: the panel titles
and counts were invented for this fixture and describe no real product or company.

## Provenance

Written by hand rather than generated; the fixture is a layout configuration and there is nothing
random in it to seed. The numbers on each panel — how many categories a bar chart has, how many
columns a table has, how many cells a heatmap has — were chosen so that the mismatch between
content and area is arithmetic rather than opinion.

The page declares a 12-column grid with 80-pixel rows. Every panel is `w: 3, h: 3`, which is a
quarter of the width and 240 pixels tall, whatever it contains.

## Traps

| What is in the file | What it does |
| --- | --- |
| Six `single_figure` panels each taking a quarter of the width | The one panel type that is read at a glance takes as much room as anything else, and together they consume the entire first screen. |
| A `table` with **14 columns and 480 rows** in a quarter-width, 240-pixel tile | Fourteen columns do not fit in a quarter width and 240 pixels shows perhaps three rows. At this size the panel is worse than a link to the table. |
| A `heatmap` of **24 by 24** cells in the same tile | 576 cells in that area gives cells too small for a colour difference to be judged, which is the only thing a heatmap encodes. |
| A `bar_chart` with **24 categories** at 240 pixels high | Ten pixels per category. The labels rotate, truncate or vanish. |
| Two `line_chart` panels of **336 points** in a square tile | A trend compressed to a square reads as noise, and the trend is what the panel is for. |
| A `text` panel of **210 words** in a quarter-width column | Either an unreadably narrow column or a tile that scrolls. |
| Fourteen panels, **no grouping at all** | Finding any one of them means scanning all fourteen. The file even records why: every panel was added to the next free cell as it was requested. |
| `layout.mode` is `absolute`, with explicit coordinates for all fourteen | The next panel added breaks the arrangement, and every panel is eventually added. |
| `narrow_viewport` is `"not defined"` | Nothing says what reflows, what stacks, or what should disappear rather than shrink into illegibility. |
| No statement anywhere of what question the page answers | Orders, delivery times, refunds, support tickets and courier availability are at least three questions sharing one page. |

The honest outcome sizes each panel by what its content needs rather than by the grid, puts the
single figures in a compact row instead of a screenful, gives the table and the heatmap real area
or moves them off the page, groups the rest into a few labelled blocks, replaces the absolute
coordinates with flow rules, says what happens on a narrow viewport, and names what it would
remove or split.
