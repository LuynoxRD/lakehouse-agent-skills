---
name: dashboard-visual-craft
description: Makes type, spacing, alignment and non-data ink carry the ranking of the information instead of decorating it, holding a page to one type scale of at most three sizes, named spacing steps that double, one alignment edge and a default state that answers. Use when a page is styled and nothing on it reads as more important than anything else, when the headline figure and its caption render at the same size, when every panel is separated by a border and a shadow and a fill at once, when the numbers in a column are centred so their digits do not line up, when a stylesheet carries a different gap value in every rule, or when the page opens on an empty state instead of on an answer.
---

# Dashboard visual craft

## Overview

Three skills in this pack decide what a page contains: which chart form a result deserves, what
its colours encode, and where the panels sit. A page can satisfy all three and still arrive as a
dump — every element the same size, every gap a different number, numbers centred in their
columns, and four devices separating each panel from the next. Nothing in it is wrong. Nothing in
it is ranked either, so the reader does the ranking, on a page that had the answer.

**"Craft" here is four measurable things, and none of them is polish.** Type, space, alignment,
and the ink that is not data. Each has a threshold, each is checkable by reading the file, and
"it looks good to me" is not an answer to any of them — it is the answer given by whoever has
been staring at the page for an hour, to a reader who will give it eight seconds.

The underlying claim is older than any of the tools: a reader groups what is near, ranks what is
larger and heavier, compares what is aligned, and reads everything else as noise. A page that
puts those four to work says what matters without a sentence explaining what matters.

## When to Use

Use this skill once the page exists and before it is handed to anybody: the panels are placed,
the charts are chosen, the palette is decided, and what remains is whether the page reads.

Use it when a page is described as cluttered, flat, busy or "not quite right" — those are all
reports of the same four faults, made by somebody who has no vocabulary for which one.

Use it when a page was generated from a template or by a script, because a generator applies a
style uniformly, and uniform is precisely what a ranking is not.

Do **not** use it to pick a chart's form; that is the `chart-type-and-library-selection` skill.
Do not use it for what a colour means or whether text is legible against its ground: the palette,
the encoding and the contrast ratios belong to the `dashboard-color-and-visual-hierarchy` skill,
and this one never overrules a contrast measurement. Do not use it to decide where a panel goes
or what belongs on the first screen — that is the `dashboard-layout-by-widget-mix` skill, which
owns placement and reading order. This skill takes the placement as given and decides how the
page reads once it is there.

## Core Process

### Step 1: Rank the information before styling anything

Write the ranking down first, because styling without one produces a page that emphasises
whatever was written last:

1. **The answer.** The one figure or sentence the page exists to deliver. There is one.
2. **The support.** The figures and charts that make the answer believable.
3. **The apparatus.** Labels, units, sources, captions, coverage notes.

**Name the actual elements, not the categories.** "The answer is the East figure; support is the
four region rows and the bar comparison; apparatus is the coverage note, the legend and the column
headers." A ranking that names no elements has not been made, and every step below it will be
applied to a page nobody ranked.

Three levels, not five. A fourth level is nearly always a second thing at level 2 that somebody
wanted to feel important, and the cost of the extra level is paid by every level below it: with
five gradations no two are far enough apart to be told apart at a glance.

If the page has more than one answer, it is more than one page, and that is a decision for the
layout skill rather than a problem to solve with type.

### Step 2: One type scale, and it carries the ranking

The three levels get three type treatments, and the treatments come from a scale rather than
being typed per element.

- **At most three distinct sizes on the page.** The artefact check counts them and refuses a
  fourth, because a page with seven sizes has no scale, it has seven decisions nobody recorded.
- **Each step is at least 1.25× the one below it.** A "headline" 1.05× its caption is not a
  level; it is the same level, rendered slightly larger, and a reader cannot see the difference
  without putting the two side by side.
- **At most two weights.** Size and weight are two dimensions of one hierarchy. Using four of
  each gives sixteen combinations for three levels, and the surplus reads as inconsistency.
- **The floor is a floor, not a target.** Body text is at least 14px and nothing a reader must
  read is below 12px. **Apparatus belongs at that floor, not raised toward the body.** A page
  whose caption, legend and footnote were each enlarged "for legibility" has three levels of
  information rendered at two, and the ranking from Step 1 is gone — the most common way this
  step is applied backwards, because each individual enlargement looks like a fix. If apparatus
  is genuinely unreadable at the floor, the answer is fewer words in it, not a larger size.
- **Numbers in a column use figures that align.** Where the typeface offers tabular or lining
  figures, use them: proportional digits make a column of numbers ragged, which defeats the one
  comparison a column exists to support.
- **The typeface is a decision, and it is named once.** State it as a token, `--font-body`,
  with a second only when a second face does a job the first cannot. A system stack is a
  legitimate choice for a file that must open anywhere with no network, and the starting page
  uses one for exactly that reason. A web font is a network dependency: the page declares it
  with a real fallback stack, because offline it renders in the fallback and nobody is told
  which.

State the scale once, as named tokens at the top of the file — `--t-figure`, `--t-body`,
`--t-label` — rather than as values sprinkled through the rules. Named once, the ranking is
visible in the source and a fourth size cannot be added by accident. The starting page in the
`dashboard-layout-by-widget-mix` skill's `assets/` already carries exactly these three.

### Step 3: Three spacing steps, and each is twice the one below

Space is what tells a reader which things belong together, and it does it before any label is
read. It only works if the gaps differ enough to be read as different.

- **Three steps, not five values.** One gap that attaches a label or a caption to its own
  element, one gap inside a group, one gap between groups. Name all three — `--gap-micro`,
  `--gap-in`, `--gap-between` — the same way the sizes are named, and let every gap, margin
  and panel padding on the page be one of them.
- **Each step is at least twice the one below it.** Below that ratio two steps read as one
  value applied unevenly, and whatever the page meant to group is invisible. 6, 12 and 32 are
  three steps; 8, 12 and 32 are two steps with an extra name, and a third value derived by
  `calc()` from the second is the second, whatever it is called.
- **A label belongs to whatever it is nearest.** A caption sitting equidistant between two panels
  belongs to neither, and the reader assigns it to the wrong one. Tighten it against its own
  panel rather than adding a line to say which one it describes. That is what the smallest
  step is for.
- **A control's own inset is not a step.** The padding inside a chip, a button or an input
  sizes the control and groups nothing; it is named once, in the control's own rule, and it is
  not counted.
- **Space is the first separator to reach for**, before a border, a rule or a fill. It costs no
  ink and it cannot be mistaken for a boundary that means something.

A page whose stylesheet carries a different number in every gap declaration has no grouping. It
has whatever spacing each rule was written with, on the day it was written. The starting page
in the `dashboard-layout-by-widget-mix` skill's `assets/` carries the three steps, and every
gap in it is one of them.

### Step 4: One alignment edge, and numbers align on the decimal

Alignment is what makes comparison possible, and misalignment is read as disorder even by
somebody who cannot say what is wrong.

- **Text is left-aligned to a shared edge.** Every block on the page starts at the same left edge
  unless it is deliberately doing something else. Centred paragraphs have a ragged left edge, and
  the eye returns to a different place on every line.
- **Numbers are right-aligned, and decimals align on the point.** This is the whole reason a
  column of numbers is a column: the digits line up by magnitude, so a longer number is visibly a
  larger one. **A centred column of numbers cannot be compared and should be treated as a
  defect**, not a style choice.
- **A column header aligns with its column's content**, which means the header over a numeric
  column is right-aligned too.
- **The unit goes in the header, once.** Repeating it in every cell adds a column of identical
  characters that the eye has to skip past on the way to the digits.

### Step 5: Remove the ink that encodes nothing

Every mark on the page either carries information or competes with the marks that do. The
discipline's own long-standing rule is to spend ink on data; the practical form of it here is a
test rather than a preference.

**The test: take it away. If nothing about the data became harder to read, it was decoration.**

Applied to what actually accumulates on a generated page:

- **One device per boundary.** A panel is separated by a border, *or* a background fill, *or* a
  shadow, *or* space. Not two, and certainly not four. Each additional device draws a second
  boundary in the same place, and the page reads as a stack of cards rather than as one answer.
- **Gridlines are apparatus and belong at apparatus weight**, if they are there at all: light,
  behind the data, never competing with the series.
- **Chart junk is anything that would survive deleting the data**: a gradient, a bevel, a drop
  shadow on a bar, a third dimension on a two-dimensional measure. A shadow on a bar makes the
  bar wider than its value.
- **A border around the whole page is a boundary the window already provides.**
- **Siblings share a shape.** A tile that carries an element its siblings do not stands taller
  than they do, and the taller tile is read as the answer whatever Step 1 decided: a ranking
  nobody made, delivered by a paragraph. Tiles in a row, label-and-value pairs down a list,
  badges on sibling panels are taken as a set before any of them is read, because what looks
  alike is read as alike, and a set holds only while every member has the same slots — the
  same elements, in the same place, at the same size. Whatever one member carries that its
  siblings do not either leaves the row or goes into every member; a note that qualifies one
  tile's finding sits under the row at full width, where it qualifies the row. `align-items:
  start` on the row exposes the difference; `stretch` hides it without fixing it, because the
  extra element is still the only one of its kind in the set.

### Step 6: The state the page opens in

The page's default state is the state most readers will ever see, because most of them will not
touch anything. It has to be an answer.

- **The page at rest answers the question in its own title.** If the title says which region grew
  and the first screen says "select a region", the page has asked its reader to do the work it
  was built to do.
- **No empty state ships as a default.** A filter opens on a real selection — all of it, or the
  most recent period — not on nothing.
- **Nothing that reads as a placeholder ships**: `Chart 1`, `Untitled`, `TODO`, filler text, a
  legend entry called `series-0`. Each is a decision that was deferred and then delivered.
- **A control that changes the page announces its current state.** A reader who did not set a
  filter has no way to know one is set unless the page says so.

This step is about the state the page opens in, never about where things sit. What belongs on the
first screen at all is the layout skill's question, and it is answered before this one.

### Step 7: Record the four decisions where they can be checked

The scale, the three spacing steps, the alignment rule and the separation device are four
decisions.
Written as named tokens at the top of the page, they are four lines that anybody can read and that
a check can count. Left as values inside individual rules, they are invisible, and the fifth size
arrives with nobody noticing.

The artefact check counts distinct font sizes on the delivered page and refuses more than three.
That is one of the four made mechanical; the other three are read from the file by a person, which
is why they are written down rather than remembered.

### Step 8: When there is no time, triage — never rewrite

A page is usually reviewed on the way out the door, and the person holding it has minutes. That
decides what gets fixed. It never decides what gets reported.

- **Never rewrite the delivered file unasked.** The page is theirs and they have read it.
  Replacing it whole, however much better the result, hands them a page they have not read
  minutes before they send it — and the faults you removed were not the ones about to hurt them,
  while the ones you introduced have not been read by anybody.
- **Split the faults into two lists, explicitly.** What changes in minutes: the alignment of a
  numeric column, a default filter, a placeholder name, three of the four devices around a panel,
  a unit moved into a header. What does not: a comparison the page has no data for, or a ranking
  that requires somebody to decide what the answer is.
- **Order each list by what the reader loses**, not by how hard it is to fix. A centred column of
  numbers costs a comparison; a fourth font size costs a little clarity. They are not the same
  size of fault and a list that treats them as one is a list nobody can act on in five minutes.
- **Say what ships with it.** If they send it as it is, the answer names the faults that went out
  with it, in the words a reader would use, so the decision was made rather than made by default.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "It looks fine to me." | You have looked at it for an hour and you know what every panel means. The reader gives it eight seconds and knows none of it. "Fine to me" is a statement about the author. |
| "I will polish it at the end." | There is no end. The page ships from the state it is in when somebody asks for it, and the styling that is deferred is the styling that never happens. |
| "It is only internal." | Internal pages are the ones that get screenshotted into decisions, because nobody thinks to question a page that was not presented. |
| "More whitespace is always better." | Uniform whitespace is the same failure as uniform type: it groups nothing. The ratio between two gaps is what carries the grouping, not the amount. |
| "The design system handles it." | A system supplies tokens. Which token carries which level of *this* page's information is the decision it cannot make for you. |
| "The note belongs in the tile it qualifies." | Then that tile is no longer a sibling of the other two, and it is read first because it is bigger. Put the note under the row, at full width, where it qualifies the row. |
| "The third gap is only a calc() of the second." | Then it is the second, applied unevenly, with a name that distinguishes nothing. A step earns its name by being at least twice the one below it. |
| "The extra border makes it clearer." | It makes it bounded. Clarity came from the space that was already separating the panel; the border added a second boundary in the same place. |
| "Centring the numbers looks tidier." | It looks tidier and it removes the comparison. A column of numbers exists so magnitudes line up, and centring is the one alignment that guarantees they do not. |
| "The default filter is empty so the reader can choose." | Most readers choose nothing. An empty first screen hands the reader the work the page was built to do, and they will not do it. |
| "The generator applies the styles consistently." | Consistently is the problem. A generator has no ranking, so it gives the answer and the footnote the same treatment, and the page arrives flat. |
| "It is one extra font size." | It is the fourth. Three levels can be told apart at a glance; four cannot, and every level below the new one gets closer to its neighbour. |
| "The caption is small, so I will bring it up to body size." | Then it is body, and the page has two levels where it wrote down three. The floor exists so apparatus stays legible while staying apparatus. Fewer words, not larger ones. |
| "There is no time, so I will just fix the whole page myself." | The page is theirs and they have read it. A rewrite minutes before sending hands them a page nobody has read, to fix faults that were not the ones about to hurt them. |

## Red Flags

- More than three distinct font sizes in the delivered file.
- The headline figure and its caption render at the same size, or within 1.25× of each other.
- The stylesheet carries a different gap value in nearly every rule.
- The gap between two groups is the same as the gap inside them.
- Two named spacing steps within twice of each other.
- A column of numbers is centred, or its decimals do not align.
- A unit is repeated in every cell of a column instead of sitting in the header once.
- A panel is separated by more than one of: a border, a fill, a shadow, a rule.
- A bar or a slice carries a gradient, a bevel, a shadow or a third dimension.
- One tile in a row carries an element its siblings do not, and stands taller than they do.
- The first screen shows an empty state, a placeholder title, or a legend entry named by index.
- Any reader-facing text below 12px.
- The page was generated and nobody looked at the generated file, only at the generator.
- Apparatus was enlarged toward body size to make it legible, leaving two levels where three were
  written down.
- A delivered page was rewritten whole because it had craft faults, without anybody asking for
  that.

## Verification

- [ ] The three levels — answer, support, apparatus — are written down **naming the actual
      elements of this page**, and every element belongs to exactly one of them.
- [ ] No apparatus was enlarged toward body size; the floor was applied as a floor.
- [ ] Where there was no time, the faults were split into what changes in minutes and what does
      not, each list ordered by what the reader loses, and the delivered file was not rewritten
      whole unless that was what was asked for.
- [ ] The delivered file carries at most three distinct font sizes and at most two weights, and
      each step of the scale is at least 1.25× the one below it.
- [ ] No reader-facing text is below 12px, and body text is at least 14px.
- [ ] At most three spacing steps are used, all named, each at least twice the one below, and
      every gap, margin and panel padding on the page is one of them.
- [ ] Every caption is nearer to the panel it describes than to any other panel.
- [ ] Text blocks share one left edge; numeric columns are right- or decimal-aligned, and their
      headers align with them.
- [ ] Each unit appears once, in its column header.
- [ ] Each panel boundary uses one device only, and every remaining mark survived the test of
      being removed.
- [ ] Every repeated group — tiles in a row, pairs down a list — has the same slots in every
      member, and nothing one member carries is missing from the others.
- [ ] The typeface is named once as a token, and a web font, if there is one, declares the
      stack it falls back to.
- [ ] The first screen, before any interaction, answers the question in the page's title: no
      empty state, no placeholder name, no legend entry named by index.
- [ ] The scale, the three spacing steps, the alignment rule and the separation device are named
      once at the top of the file rather than repeated inside individual rules.
- [ ] The delivered file was opened and read, not the generator that wrote it.
