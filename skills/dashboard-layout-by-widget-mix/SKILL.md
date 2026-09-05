---
name: dashboard-layout-by-widget-mix
description: Places what is on a page according to how many panels there are and what kind each one is, giving a table or a heatmap the area it needs and a single figure the little it needs. Use when arranging more panels than fit on one screen, when a page is a uniform grid of equally sized tiles, when deciding what belongs above the fold, or when a page has grown by accretion and nothing was ever removed.
---

# Layout by widget mix

## Overview

A page is not a container to fill. It is a sequence somebody reads, and the order and the size of
the things on it decide what gets read at all.

Two forces do all the work, and neither is a matter of taste. **Finding one panel among many
unrelated ones costs time in proportion to how many there are**, which is why grouping beats
shrinking. And **things placed close together, or made to look alike, are read as belonging
together**, which is why spacing is a stronger grouping tool than a border and why a uniform grid
says everything on it is equally important.

The mix decides the layout: how many panels, and of what kinds.

```
inventory the panels ──► rank by the page's question ──► area by content type
        │                                                        │
        └──► past what fits: group, then split ◄─────────────────┘
```

## When to Use

Use this skill when arranging a page that holds more than a couple of panels, when adding one to a
page that is already full, or when reviewing a page that people say is cluttered without being
able to say which part.

Use it when the page is a uniform grid, which is the shape a layout takes when nobody decided one.

Do **not** use it to choose what form each chart takes, which is the
`chart-type-and-library-selection` skill, or which colours anything is, which is the
`dashboard-color-and-visual-hierarchy` skill. What each panel is allowed to claim belongs to the
`insight-narrative-integrity` skill.

## Core Process

### Step 1: Inventory the panels by type, and give each type the area it needs

Area is a property of the content, not of the grid. List every panel with its type, then size it
by what that type has to show:

| Panel type | What it needs | What happens when it is squeezed |
| --- | --- | --- |
| A single figure with a label | Very little; it is read at a glance | Nothing. It is the one type that survives any size, which is why it should never take a full tile. |
| A trend over time | Enough width that the time axis is legible; height is cheap | Compressed into a square it reads as noise, and the trend was the point. |
| A ranked bar chart | Height proportional to the number of categories, so labels fit horizontally | Labels rotate, truncate, or disappear. |
| A table | Width for its columns and height for enough rows to be worth reading | It becomes a scroll box showing three rows, which is worse than a link to the table. |
| A heatmap or matrix | Area in both directions; cells must be large enough to distinguish | Cells collapse below the size at which a colour difference can be judged. |
| A block of text | A readable line length, not a full-width column | Either a line too long to track or a column too narrow to read. |

A page whose panels are all the same size has answered none of these questions.

### Step 2: Rank the panels by the one question the page exists to answer

A page answers one question. Write it down, then rank every panel by how directly it answers it:
the headline answer, the panels that support it, and the context that only matters once somebody
is already asking.

Place them in reading order: the headline answer where the reader lands first, supporting panels
next, context below. Anything that answers no part of the question is a candidate for removal, and
removing it is a real option, not a failure to fit it in.

**Write the ranking down as the panels' element ids, in order, and it becomes checkable.** This is
the only layout decision that leaves no trace in the styling: a page can be spaced, sized and
grouped correctly and still open on a panel nobody needed. Declared as `layout.panels`, the check
compares the ranking against the order the panels appear in the document, and the headline answer
being first stops being something a run reports about itself.

Document order, not visual order, and that is the stronger rule rather than the weaker one. It is
what a screen reader announces and what the tab key follows, so a page whose headline is first to
the eye and last in the markup answers the question for one audience and buries it for another.
Where a grid is tempting you to reorder visually, reorder the markup instead.

### Step 3: Past what fits, group; past what grouping fixes, split

As the number of panels rises, the cost of finding any one of them rises with it. Shrinking them
does not help, because it makes each one harder to read while leaving just as many to search.

- **Group** related panels into a small number of labelled blocks, by theme or by the dimension
  they cut. Searching four blocks and then three panels inside one is a much shorter search than
  scanning twelve.
- Do the grouping with **space and alignment** before reaching for borders and boxes. Proximity is
  read as belonging; a border is a second visual layer competing with the data.
- When grouping is no longer enough — when the blocks themselves stop fitting — **split the page**
  into tabs or separate pages by theme. Two pages that each answer a question beat one page that
  answers neither.
- Splitting is not a defeat. A page that needs scrolling past three screens has already been
  split, just badly, and by the scrollbar rather than by anybody's decision.

**The deliverable is exactly one file, unless splitting it was a decision you write down.** This
is the firm form of everything above, and it is where a run most often stops early: a page of six
panels becomes six files of one chart each, and the reader is handed the assembling that the
layout was for. Six files cannot share an axis, cannot be compared side by side, and cannot carry
a filter between them. They are six charts.

Each one also carries its own copy of whatever draws it. A real run delivered five files of four
megabytes where the drawing library is the same bytes five times over: twenty megabytes to show
what one page would have shown in one. If a split is genuinely right, it is stated with its
reason, and the library is still loaded once rather than once per page.

### Step 4: Do not make a uniform grid the default

A grid of identical tiles is the most common layout and it is a decision not to decide. It gives a
single figure the same weight as a twenty-column table, tells the reader that everything matters
equally, and wastes most of its area on the panels that needed the least.

Let the tiles differ. A row of small figures across the top, one wide panel for the trend that
carries the page, and full-width area for the table underneath is a layout. Twelve equal squares
is a container.

### Step 5: Lay out by rules, not by coordinates

Express the layout as weights and flow — this panel takes twice the width of that one, this row
holds the summary figures — rather than as absolute positions. Absolute positions break the first
time a panel is added, and every panel is eventually added.

Say what happens as the viewport narrows: which panels reflow, which stack, and which are hidden
because they cannot be read below a certain size. A panel that becomes unreadable at a narrow
width should disappear deliberately rather than shrink into illegibility.

#### The shape those rules take

Everything above is a decision. This is what the decision looks like written down, and it is the
part a run most often skips: a page laid out by stacking every panel full width, one after
another, has made none of the choices in Step 1 while looking like it did.

A track-based grid is the mechanism, because it expresses **weights** rather than positions. One
row of columns, each panel spanning as many as its content needs:

```css
:root {
  --gap-within: 12px;   /* inside a group */
  --gap-between: 32px;  /* between groups — visibly larger, and that difference IS the grouping */
  --measure: 68ch;      /* a readable line length for any block of prose */
}
.board { display: grid; grid-template-columns: repeat(12, 1fr); gap: var(--gap-within); }
.group + .group { margin-top: var(--gap-between); }

/* Spans come from the Step 1 table: area is a property of the content. */
.kpi    { grid-column: span 2; }                        /* a figure read at a glance */
.trend  { grid-column: span 12; min-height: 320px; }    /* width is the time axis */
.ranked { grid-column: span 6;  min-height: 360px; }    /* height holds the category labels */
.matrix { grid-column: span 6;  min-height: 360px; }    /* area in both directions */
.table  { grid-column: span 12; min-height: 420px; }
.prose  { grid-column: span 6;  max-width: var(--measure); }

@media (max-width: 800px) {
  .board { grid-template-columns: repeat(4, 1fr); }
  .kpi { grid-column: span 2; }                         /* two across instead of six */
  .trend, .ranked, .table, .prose { grid-column: span 4; }
  .matrix { display: none; }                            /* cells below this width cannot be judged */
}
```

Four rules the shape encodes, each one traceable to a reason already stated:

- **Different spans, because area is a property of the content.** Twelve equal tiles is the
  container this skill refuses; the spans above are Step 1's table turned into numbers.
- **Two gap sizes, not one.** Proximity is what the reader uses to tell groups apart, so the gap
  between groups has to be visibly larger than the gap inside one. A single uniform gap groups
  nothing.
- **A minimum height per panel type, not a shared one.** A trend and a table fail in different
  ways when squeezed, so they get different floors.
- **A stated narrow-viewport behaviour, including what is hidden.** The panel dropped at a narrow
  width is dropped on purpose, and the page says so where the panel was rather than leaving a
  reader to wonder what they are missing.

A page with a `max-width` on the container and nothing else has one width and a lot of empty
margin either side of it; that is not a responsive layout, it is a fixed one that fits.

### Step 6: State the layout decisions next to the page

Record the question the page answers, the ranking that produced the order, the grouping and why,
and anything that was left out. The next person to add a panel then has something to add it
against, instead of putting it in the first empty tile.

### Step 7: Open the assembled page and check it is one document

Assembly is where a layout stops being a plan and becomes a file, and the faults it introduces
are invisible in every earlier artefact. The most common one has a single cause: a plotting
library asked for a figure's HTML returns a **complete document** by default, headers and all,
and embedding that inside a page nests one document inside another. A real assembled page held
fourteen of them. It still displayed, because browsers recover from nested `<html>`; what did not
recover was the fourteen copies of the figure writer's own `html, body { height: 100% }`, which
applied to the real document and broke the layout this skill had just decided.

So the last act of assembly is to read the file:

```
bash scripts/verify-output.sh --manifest docs/data/figures.json   --html <the page that ships> --project .
```

It fails on more than one doctype, a repeated `<html>`, `<head>` or `<body>`, a duplicated
charset, an unclosed or stray tag, a page that does not decode as UTF-8, and on any number in the
page's own text that no declared figure produces. It also reads the layout back out of the file
in the only three ways a file can be read on that: a missing viewport meta, a stylesheet with no
responsive mechanism at all, and a blank title. With `--project` it also **looks for the pages
rather than trusting the ones it was handed**, and fails when several were delivered with no
stated reason, or when the same inline script sits in more than one of them. That last one catches the fault assembly is
uniquely prone to: a count typed into a header or a subtitle by hand, sitting a few centimetres
from a computed tile that disagrees with it.

When the figure writer offers it, ask for a fragment rather than a document, and check the
resulting file rather than assuming the option took effect.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "A uniform grid looks clean." | It looks consistent. It also says every panel matters equally, which is never true, and it starves the panels that needed area. |
| "Everything on the page was requested by someone." | Then the page answers several questions and should be several pages. A request is a reason to include something somewhere, not everywhere. |
| "Users can scroll." | They can. What they cannot do is know what is below, so anything past the first screen is read only by someone already looking for it. |
| "Making the panels smaller fits more in." | It leaves just as many things to search through, each one harder to read. |
| "Tabs hide information." | Tabs name it. Twelve unlabelled panels on one screen hide it far more effectively. |
| "The table is important, so it gets a big tile." | Importance decides position and order. Area is decided by what the content physically needs to be legible. |
| "We can tidy the layout later." | Layout is what people use, and later is when there are twenty panels instead of twelve. |
| "The page opened in the browser, so the assembly is fine." | Opening proves the browser recovered. Nested documents, duplicated stylesheets and a header that disagrees with its own tile all survive that test intact. |
| "That figure in the header is just context, not a metric." | It is a number on the page, so it is read as one. Context that nothing computed is the easiest kind of wrong to ship. |

## Red Flags

Stop when any of these is true:

- Every panel on the page is the same size.
- A table or a heatmap is in the same tile size as a single-figure panel.
- The page holds more than about a dozen panels with no grouping.
- Nobody can state in one sentence the question the page answers.
- Panels are positioned at absolute coordinates.
- A trend chart is square, or a bar chart's category labels are rotated to fit.
- The page requires scrolling past several screens and has never been split.
- A panel was added to the first free space rather than to a group.
- The deliverable is more than one file and nothing says why.
- Each delivered file carries its own copy of the drawing library.
- A figure was embedded by pasting the output of a call whose default is a whole document.
- A count sits in a header, a subtitle or a footer without a query behind it.
- The page was declared finished on the strength of having been opened, not read.
- The panel a reader lands on first is not the one that answers the page's question.
- The markup order and the visual order disagree, so the page reads differently by keyboard.
- Every panel is a full-width block stacked on the one above it. That is the uniform grid in its
  other shape, and it means Step 1 was never applied.
- One gap size is used everywhere, so nothing is grouped by proximity.
- The page has a `max-width` and no other rule about width, which is a fixed layout centred.

## Verification

- [ ] Every panel is listed with its type and the area that type needs, and the sizes on the page
      reflect that rather than a uniform grid.
- [ ] The question the page answers is written in one sentence, and the panels are ordered by how
      directly they answer it.
- [ ] That order is declared as `layout.panels` and matches the order the panels appear in the
      document, headline answer first.
- [ ] Panels are grouped into a small number of labelled blocks, using space and alignment before
      borders.
- [ ] If the page still does not fit, it is split by theme into tabs or separate pages, and the
      split is stated rather than left to the scrollbar.
- [ ] The layout is expressed as weights and flow rules, with the narrow-viewport behaviour of each
      panel stated, including any that are deliberately hidden.
- [ ] Panels of different content types have different spans and different minimum heights, and
      each one traces to what that content needs rather than to the grid.
- [ ] The gap between groups is larger than the gap inside a group, and both are named once
      rather than repeated per panel.
- [ ] The page carries a viewport meta, at least one rule that responds to width, and a title
      naming the question it answers.
- [ ] Anything removed from the page is named, with the reason.
- [ ] The deliverable is one file. If it is not, the split is written down with its reason, and
      the drawing library is loaded once rather than once per page.
- [ ] `scripts/verify-output.sh` was run against the assembled file with `--project`, and its
      output is quoted showing zero errors. The assembled page is one document, and every number in its own text
      is one a declared figure produces.
