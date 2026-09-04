# Design tokens for a reporting page

One JSON file describing the colours of a reporting page: theme grounds, text tokens, accents,
four chart colour assignments and the page chrome. Everything is **synthetic**: the tokens were
invented for this fixture and belong to no product, brand or company.

## Provenance

Written by hand rather than generated; the fixture is a configuration file and there is nothing
random in it to seed. The colours were chosen so that each trap has a specific measured value.

Every ratio below was computed from the WCAG relative-luminance definition, against the file's own
`light` surface `#FFFFFF` and `dark` surface `#121212`:

| Token | On light | On dark |
| --- | --- | --- |
| `heading` `#202124` | 16.10:1 | **1.16:1** |
| `body` `#5F6368` | 6.05:1 | **3.10:1** |
| `muted` `#9AA0A6` | **2.64:1** | 7.09:1 |
| `accents.primary` `#1A73E8` | 4.51:1 | **4.16:1** |
| status green `#2E7D32` on white | 5.13:1 | — |
| status red `#C62828` on white | 5.62:1 | — |
| the green **against** the red | **1.10:1** | — |

## Traps

| What is in the file | What it does |
| --- | --- |
| `muted` used for axis labels on **both** themes | 2.64:1 on light fails the 4.5:1 threshold for normal text, while the same token reaches 7.09:1 on dark. It fails in one theme and passes in the other, so "it looks fine" depends entirely on which theme the reviewer had open. |
| `heading` and `axis_line` at `#202124`, declared for both themes | 16.10:1 on light and 1.16:1 on dark: near-invisible on the dark ground. The inverse of the muted trap, in the same file. |
| `body` at 3.10:1 on dark | Passes comfortably on light, fails normal text on dark. Three tokens, three different directions of failure. |
| `satisfaction_by_month` gives an **ordered** 1-to-5 rating a **categorical** palette | The order is destroyed. No reader can tell which of two hues is the higher rating without the legend, on every mark. |
| `target_variance_by_region` runs from -38% to +21% with zero meaning "met the target", and gets a **sequential** palette | The crossing point, which is the entire finding, is invisible. This one needs a diverging palette pinned at zero. |
| `channel_mix` assigns **eleven** distinct hues | Past roughly eight, hues stop being distinguishable and the legend becomes a lookup table traversed once per mark. |
| `sla_status_table` shows met and missed **by cell fill only**, with no legend and the cell text carrying just the response time | Colour alone. The two fills are 1.10:1 against each other, so for a reader who does not separate those hues the two states are one state and nothing else on the page distinguishes them. |
| Four accent colours, each assigned to a KPI | Emphasis is created by difference and spent by use. With four accents nothing is emphasised. |
| `grid_lines` at `#5F6368`, the same value as body text | Chrome as strong as content: the grid competes with the data it is supposed to sit behind. |
| `card_border` uses the primary accent on **every** card | The colour that is supposed to mean "look here" is on everything. |

The honest outcome computes the ratios rather than judging them, names which token fails on which
ground, matches each palette to its variable's type, and identifies the status table as meaning
carried by colour alone rather than as a contrast question.
