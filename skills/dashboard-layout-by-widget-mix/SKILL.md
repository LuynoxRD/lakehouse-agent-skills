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

This skill decides **where** each panel sits. How the page *reads* once they are placed — type,
spacing, alignment, and marks that carry no data — is the `dashboard-visual-craft` skill, which
runs after this one: a page can pass every check here and still arrive flat.

## Core Process

### Before any of it: ask where the page is going

A page has two possible destinations, they are not interchangeable, and which one it is decides
what can still be verified afterwards. So it is settled before a file exists, not after one does.

- **A file inside the project.** Somebody has to open it by hand. It is the only form the artefact
  check in Step 7 can work on, because that check recomputes every published figure against the
  table that is still sitting beside it.
- **A page the tool publishes and hands back as a link.** It opens in one click and can be given
  to somebody who installs nothing. It has left the project, and nothing recomputes its numbers
  against the source once it has.

**Ask which one, and put both halves in the question.** Not "file or published page?", which
names two words and no consequences, but the trade-off itself: one opens in a click and travels as
a link, and gives up the recomputation against the real table; the other keeps that guarantee and
has to be opened by hand. Asking without saying what each option costs moves the decision without
moving the information the decision needs, which is worse than deciding alone — it looks like
consultation and is delegation.

They are not exclusive in the order things happen. When the answer is the published page, build it
as a project file, run Step 7 against it, and publish what passed. The guarantee is lost by
publishing a page nothing ever checked, not by publishing.

Assume neither. A pipeline that always writes a project file has chosen for the reader every time,
and the reader is the one who knows whether anybody else has to open it.

Record the answer as `layout.destination` in the manifest, as `project-file` or
`published-page`. The artefact check refuses a run that declares neither, because a rule with
no mechanism is the one a run under pressure drops — this one was skipped by a real run with
the instruction in front of it. What the check sees is that a decision was written down; it
cannot see whether anybody was asked, and it says so among the things it did not verify.

### The page you start from

Everything after this point is a procedure: inventory, rank, group, size. A procedure only helps
somebody who runs it. In a measured run, a comment reading `# SKILL: dashboard-layout-by-widget-mix`
sat directly above a generic call for a two-by-two subplot grid — four panels of identical size,
which is the exact shape Step 4 refuses by name. The skill was labelled, not executed, and the page
that shipped had no viewport meta, no width rule, a container fixed at 800×1000 pixels, a `<title>`
inherited from the plotting library's logo, and every computed figure printed to a terminal instead
of onto the page.

That is not a smaller model deciding worse. It is a smaller model **not entering the procedure**,
and a better procedure does not reach it. What does reach it is the shape the colour rules already
have: `dashboard-color-and-visual-hierarchy` is a lookup — unordered categories take distinct hues,
text takes 4.5:1 — and the same run that ignored every step here got its colours right, because
following a lookup is reading a row rather than making a decision.

So the layout arrives as a lookup too. **A template is what stops a model inventing a dashboard.**
Given a page to fill, it fills fields; given a procedure, it emits whatever its library does by
default and puts the skill's name in a comment above it. The floor stops being whatever the model
can design under pressure and becomes what the file already contains, which is the difference
between a reader getting a usable BI page and a reader getting four identical squares with no
figures on them. A stronger model loses nothing: it starts from the floor and improves on it, and
the layout note records what it changed.

So the decisions arrive already made. **Generate the page from `assets/template.html` in this
skill directory**, beside this file. It already carries:

- a viewport meta, a `<title>` that is the page's question, and a container that is both bounded
  and centred;
- colour tokens for the light and dark grounds, with the status colours kept separate from the
  accent;
- **three type sizes by role** — figure, body, label — because a fourth distinction is a weight, a
  colour or a letter-spacing change, and a delivered page that grew to eight sizes had no figure
  and no label, only text;
- the twelve-track grid, with the span and the height floor of every panel type taken from the
  Step 1 table, and two gap sizes whose difference is the grouping;
- a stated narrow-viewport rule that names the panel it drops and why;
- the filter bar, visible and clearable in one action, with the selection in the URL;
- one colour map read by every panel, and one `render()` that recomputes every panel from the
  current filter;
- a `note` under each figure and a `footer` for coverage, which is where each kind of caveat goes;
- figures in `tabular-nums`, and no pixel width anywhere.

Fill every `FILL`, delete the sections you do not need, keep it one file. It deliberately does not
choose the charting library: that is Step 4 of the `chart-type-and-library-selection` skill, and
the panels are empty containers so any library can fill them.

Reaching Step 1 with that page is the floor. The steps below are how you improve on it, and every
departure from it is named in the layout note from Step 6.

Four things that template does which the failing page did not, each traceable to a rule already stated:

- **It declares a width and a title.** A viewport meta, one media query, and a `<title>` that is
  the page's question. A chart library's HTML export supplies none of these.
- **Every panel gets its area from its type**, with a floor, and the panel that cannot be read
  narrow is dropped on purpose rather than squeezed.
- **The figures are on the page**, in `tabular-nums` so digits line up in a column, each with the
  population it covers. A number computed and printed to a terminal has not been published.
- **Nothing sets a pixel width.** The container that was `width:1000px` is the reason that page
  overflows every phone.

Three numbers the procedure below leaves open, so they are fixed here:

| Decision | Default | When to move it |
| --- | --- | --- |
| Panels before grouping | **6** | Never up. Below six, one labelled group is still correct and costs nothing. |
| Panels before splitting into tabs or pages | **20** | Down, when the panels answer two questions rather than one. |
| Type sizes | **3**, by role: figure, body, label | Never. A fourth size is a weight, a colour or a letter-spacing change. |
| Words in a panel note | **25**, about two lines at the measure above | Up only for a caveat that changes the reading, and then it moves into the body text. |

**Where a caveat goes, so the page reads like a dashboard and not an audit log.** The pack requires
that a figure carry its population and its limits, so a page with none of that is not the fix; a
page carrying all of it inside the sentences is what reads as a report about the data rather than
an answer.

**Which kinds of caveat there are is the `insight-narrative-integrity` skill's**, because it owns
the prose. What this skill owns is the place on the page each kind lands, and the template has a
slot for each:

| The kind that skill names | Where it goes here |
| --- | --- |
| Changes how this figure is read | The `note` under that figure, in label type. Never further away. |
| Coverage or provenance | One line in the `footer`, in business words: the period and the population. Not a filename — the reader cannot open one — and not the pipeline's own account of itself, which goes in the reply. |
| A definition somebody may not share | Beside its first use, once. |

**Never a tooltip as the only carrier.** The `dashboard-color-and-visual-hierarchy` skill already
refuses an encoding that exists only on hover, and a caveat is an encoding.

**Write it for the reader who opens the page, not for the one who ran the pipeline.** Most people
who open a dashboard never ran PROFILE through DISCLOSE, do not know those words, and should not
have to: the number and its population are the answer they came for, and the answer is what sells,
not the process behind it. A waitlist page whose footer reads "3 test submissions and 1 duplicate
resubmission were excluded in CLEAN, see cleaning-log.md" is accurate and unreadable to the
business reader it was built for — `CLEAN` is this pack's own stage name, `cleaning-log.md` is a
file the reader has no way to open, and a paragraph explaining that a redact decision was made
about a field nobody asked about answers a question the page never raised.

The line is drawn by audience, not by trimming words. Every FILL below has a home on one side:

| Belongs on the page | Belongs in the reply, or in `docs/data/*.md` |
| --- | --- |
| What a figure means and its population — "9 of 25 leads (36%)" | How it was produced — cleaning rules, row counts removed, script and file names |
| A caveat that changes how a figure is read — "a small base, 3 leads" | The pipeline's own provenance — build dates, stage names, which script ran |
| Why a category is its own group — "1 lead did not answer" | The name that group has in the code, or the word "bucket" itself |
| An answer to a question the reader actually asked | An unprompted paragraph justifying a redact decision nobody raised |

Four tells, checkable rather than a matter of taste: a pipeline stage name in capitals (`PROFILE`,
`CLEAN`, `MODEL`, `QUERY`, `VISUALIZE`, `ASSEMBLE`, `NARRATE`, `DISCLOSE`, `REDACT`) sitting as page
text; the literal word "bucket"; the name of one of this pack's own artefact files
(`cleaning-log.md`, `figures.json`, `verify-output.sh` and the like); or a sentence explaining a
decision about data that was never shown, unprompted. None of these words is wrong to know — they
are wrong on this page. Say them in the reply that hands the page over, and in the disclosure note
beside the curated table, where a reader who wants that detail already knows to look.
`scripts/verify-output.sh` checks for the first three; the manifest's `page_copy_exceptions` names
a real business term that happens to collide with one (a product literally called Model, say),
because the check cannot tell the two apart on its own.

Two more belong to the same idea, and the same check now refuses them. **A path into the project
printed as page text** — `data/curated/orders.parquet`, `docs/data` — is the plumbing one level
down from an artefact filename: true, and unopenable by whoever is reading. And **a page written
in more than one language**, which nobody decides and everybody ships: a template in one language
filled with copy in another, leaving half the readers able to read half the page. A specimen
inside `<code>` or `<pre>` is quoted rather than said, so neither rule reads it.

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

**A green result is not the page being fine, and the check says so on every run.** It reads the
file; it never renders it. Clipped text, two labels sitting on top of each other, a chart whose
own axis labels rotate onto their side when the container narrows, a board pinned against one
edge with the viewport empty beside it: none of that is visible to anything that parses markup.
A real page passed every check here and shipped with two of those.

So the last act is to open it, at named widths, and write down what you saw:

- Declare the widths the page has to work at as `layout.viewports`. The default set is
  **375, 768 and 1440**. The narrow one is not optional; it is where labels rotate, where a
  segment gets too thin for the text inside it, and where both of the real failures happened.
- Record one observation per width in `layout.observed`, saying what you looked for. The check
  refuses a responsive page with no observations, and refuses an observation that says nothing:
  "fine" is not an observation, "labels upright, no segment text overlapping" is.
- At the wide end, look for the page sitting against an edge. A container with a maximum width
  and no automatic inline margin does exactly that, and the check catches that one statically.

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
| "A file in the project is the obvious default." | It is the default of the check, not of the reader. The check needs a file it can find beside the table; that is a fact about the check, and passing it off as the reader's requirement is how somebody is handed a path they have no way to open. |
| "Asking about the format is a detour; the page is what matters." | The format decides who can open the result and what can still be recomputed about it. Both are properties of the page. Choosing them silently is not saving the reader a question, it is answering one on their behalf. |
| "The page opened in the browser, so the assembly is fine." | Opening proves the browser recovered. Nested documents, duplicated stylesheets and a header that disagrees with its own tile all survive that test intact. |
| "That figure in the header is just context, not a metric." | It is a number on the page, so it is read as one. Context that nothing computed is the easiest kind of wrong to ship. |
| "Saying what was cleaned is being transparent." | Transparent to whom. The reader who opens the page did not ask how it was made; that answer goes in the reply, where the person who did ask is the one reading it. |
| "It's more accurate to name the exact stage." | Accurate and unreadable both describe this sentence. `CLEAN` is precise to the person who ran the pipeline and meaningless to everyone else, which is most readers. |
| "Mentioning the file is helpful, in case someone wants to check." | A reader of a page has no way to open `cleaning-log.md`; naming it on the page helps nobody, it only proves the sentence was written for the pipeline's own audit trail. |

## Red Flags

Stop when any of these is true:

- A page is being written and nobody was asked where it goes. The destination was inherited from
  whatever the previous step happened to produce.
- The destination was asked as two bare words, with neither what each one gains nor what it gives
  up stated in the question.
- Every panel on the page is the same size.
- A comment names this skill above code the skill's own steps refuse. A label is not a decision,
  and the two-by-two grid of identical panels is what the label usually sits on.
- The page uses more than three type sizes, so nothing is the figure and nothing is the label.
- A figure was computed and printed to a console rather than written onto the page.
- The page sets a width or height in pixels on a container.
- Every caveat is inside the sentence it qualifies, so the page reads as an audit log.
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
- The page was declared responsive and never opened at a narrow width.
- A container has a maximum width and nothing centring it.
- The panel a reader lands on first is not the one that answers the page's question.
- The markup order and the visual order disagree, so the page reads differently by keyboard.
- Every panel is a full-width block stacked on the one above it. That is the uniform grid in its
  other shape, and it means Step 1 was never applied.
- One gap size is used everywhere, so nothing is grouped by proximity.
- The page has a `max-width` and no other rule about width, which is a fixed layout centred.
- One of this pack's own stage names (`PROFILE`, `CLEAN`, `MODEL`, `QUERY`, `VISUALIZE`,
  `ASSEMBLE`, `NARRATE`, `DISCLOSE`, `REDACT`) sits as plain text on the page.
- The word "bucket" appears on the page, instead of what the group actually is.
- The page names one of its own artefact files (`cleaning-log.md`, `figures.json`,
  `verify-output.sh`) as something the reader could open.
- The page volunteers a paragraph justifying a redact decision — a field that exists but is not
  shown — that nothing on the page prompted a reader to ask about.

## Verification

- [ ] Where the page goes was asked before it was written, not assumed, and the question carried
      what each destination gains and what it gives up.
- [ ] The answer is recorded as `layout.destination` in the manifest, and `verify-output.sh`
      passed with it there.
- [ ] The page starts from the default above, and every departure from it is named in the layout
      note with its reason.
- [ ] Three type sizes, by role: figure, body, label. A fourth distinction is a weight, a colour
      or a letter-spacing change.
- [ ] Every caveat is placed by what it does: one that changes how a figure is read sits under
      that figure, coverage and provenance sit in the footer, and none of them is hover-only.
- [ ] Nothing on the page names a pipeline stage in capitals, the word "bucket", or one of this
      pack's own artefact filenames — that detail is in the reply and in `docs/data/*.md`, or it
      is named in `page_copy_exceptions` as a real business term. `verify-output.sh` checks this.
- [ ] The page is in one language, whole, and it is the reader's. `verify-output.sh` reports a
      second language's words sitting in the same page text.
- [ ] No path into the project is printed as page text. The reader cannot open it, and the check
      refuses it unless `page_copy_exceptions` says the page is genuinely about that file.
- [ ] No paragraph on the page justifies a redact decision nobody asked about; a field that is
      not shown is simply not shown.
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
      output is quoted showing zero errors, including the list of what it did not verify.
- [ ] The page was opened at every declared width and the observations are recorded, because
      zero errors from a parser says nothing about what the page looks like. The assembled page is one document, and every number in its own text
      is one a declared figure produces.
