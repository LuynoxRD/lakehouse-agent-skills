---
name: chart-type-and-library-selection
description: Picks the chart form that an already prepared result and its shape call for, then the rendering library the destination calls for, rather than the one that was easiest to reach. Use when it is not obvious which kind of plot a result needs, when choosing between a bar, line, scatter, area or pie, when a value has to be plotted over time, when a relationship between measures calls for a scatter rather than bars, when a result has more categories or a longer tail than the chosen form can carry, when a series has gaps or points that are not in order, or when deciding what to render a plot with for a report, a slide or a web page.
---

# Chart type and library selection

## Overview

A chart is a claim rendered as a shape, and the shape decides how accurately anyone can read it.
That is not a matter of taste: the accuracy with which people judge encodings has a known order,
and it is the same order every time.

**Position along a common scale** is read most accurately, then **position on separate scales**,
then **length**, then **angle and slope**, then **area**, and last **colour and volume**. Every
chart choice is a decision about how far down that list to push the number that matters.

A pie chart asks the reader to compare angles. A bar chart asks them to compare positions along a
shared axis. The data does not change; the accuracy of reading it does.

```
question → what is being compared → the encoding that reads most accurately → the form
                                                                                │
                                            destination and volume → the library
```

## When to Use

Use this skill whenever a result is about to become a picture, and whenever an existing chart is
being reused for new data whose shape has changed underneath it.

Use it when a chart is failing in a way people describe as cosmetic: too many slices, categories
too small to label, a line that looks smooth across a period with no data.

Do **not** use it to decide what colours the chart uses or whether it can be read on both
backgrounds, which is the `dashboard-color-and-visual-hierarchy` skill, nor how several charts sit
together on a page, which is the `dashboard-layout-by-widget-mix` skill. What the chart is allowed
to claim belongs to the `insight-narrative-integrity` skill, and whether the data underneath was
cleaned belongs to `etl-before-dashboard`.

## Core Process

### Step 1: Say what is being compared, in one sentence

Before choosing anything: what does the reader need to compare, and how precisely? "How the five
channels rank by revenue" and "whether revenue and units move together" are different questions
and no single form answers both.

Write the sentence down, one per chart, and keep it next to the chart in whatever you hand back.
A chart chosen without it is a chart chosen by habit, and a list of the forms you picked is not
the same thing: the forms say what you did, the sentences say what each chart is for, and the
second is what somebody checks the chart against later.

### Step 2: Let the data's shape rule out forms before preference chooses one

Measure, then choose. These are disqualifications, not preferences:

| Shape of the data | What it rules out |
| --- | --- |
| More than about five categories | A pie or donut. Angle comparison collapses, and the slices become too thin to label. |
| A long tail, where a few categories hold most of the total | Any form that gives every category equal visual weight. Sort the bars and say how much the tail holds. |
| Two continuous variables | A bar chart. The question is a relationship, so it needs two positional axes. |
| A time series with gaps | A line drawn straight through the gap. A line asserts continuity, so a missing period must break it or be marked. |
| Points that are not ordered by the axis variable | A line at all. A line between unordered points draws a path that does not exist. |
| Parts that do not sum to the whole | A stacked form. Stacking claims the segments compose a total. |
| Many overlapping points | A plain scatter without transparency, sampling or binning; the dense region is unreadable and its density is the finding. |

### Step 3: Choose the form that puts the important comparison highest on the accuracy order

Once the disqualified forms are gone, prefer the one that encodes the key comparison as position,
then length, and only then anything else.

- **Ranking or comparing amounts across categories:** horizontal bars, sorted by value. Labels
  fit, and length on a common baseline reads accurately. The baseline starts at zero, because
  length is the encoding and a truncated axis multiplies the apparent difference.
- **A quantity over time:** a line, with the axis in time order and gaps left broken.
- **A relationship between two quantities:** a scatter, with the dependent variable on the
  vertical axis.
- **A distribution:** a histogram or a box plot; a mean and a bar hide the shape entirely, and
  the shape was the question.
- **Composition, when it genuinely sums to a whole and has few parts:** a stacked bar rather than
  a pie, because a shared baseline is still position.
- **A matrix of two categorical dimensions:** a heatmap, accepting that colour is last on the
  accuracy order, so the cells carry their values as text when they must be read exactly.

State which comparison you optimised for, because that is the decision.

**When the requested form is one the shape rules out, build the one that works, not just a
recommendation of it.** An alternative that is described and not produced leaves the person
holding only the version that misleads, and an artefact beats a suggestion every time. If the
requested form is produced as well, it carries on its face what it costs the reader. Collapsing
the data until it fits the requested form is not a compromise either: it answers a different
question than the one that was asked.

### Step 4: Choose the library by destination and volume, not by familiarity

The form is decided by the data. The library is decided by where the chart has to work:

- **What renders it:** a notebook, a static report, a web page, a printed document. A library that
  produces an interactive widget is a broken image in a PDF.
- **How many points it has to draw.** Above roughly tens of thousands of marks, a library that
  emits one element per point in a document becomes unusable in the browser; that is the point
  where aggregation, binning, or a canvas-based renderer stops being optional.
- **Whether interaction carries meaning or decoration.** Tooltips that hold the exact values are
  meaning. Animation on load is decoration, and it costs the reader time on every visit.
- **What the project already has.** A second charting library is a dependency, a second visual
  language and a second set of defaults to override. Adding one is a decision worth stating.

Name the destination, then the library, then why. "It is what I know" is the answer this step
exists to replace.

### Step 5: Label so the chart survives being separated from its context

Every chart travels: it gets screenshotted, pasted, and shown without whatever was said next to
it. So the chart itself carries the units, the period, the filter that produced it, and the table
it was built from.

If a period is missing from the data, the chart says so on its face rather than in a caption that
will not travel with it.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "A pie chart is more intuitive for shares." | It is more familiar. Reading it means comparing angles, which is measurably less accurate than comparing lengths, and it degrades fast past a few slices. |
| "Starting the axis at zero wastes space." | The length is the encoding. Cutting the baseline changes the ratio the reader sees, which is the one thing the chart was for. |
| "The line looks better without the break." | It looks better because it is asserting data that does not exist. |
| "There are only twelve categories, a pie is fine." | Twelve slices means twelve angles and twelve labels that do not fit. Sorted bars cost nothing and read exactly. |
| "The library is the one I always use." | Then the destination never entered the decision, and the chart will be checked against it later by somebody else. |
| "Interactivity makes it richer." | Interaction that carries values is useful. Interaction that carries motion is a delay the reader pays for every time. |
| "It is just an exploratory chart." | Exploratory charts are the ones that get pasted into messages, where nothing says they were exploratory. |

## Red Flags

Stop when any of these is true:

- A pie or donut has more than five slices.
- A bar chart's value axis does not start at zero.
- A line crosses a period for which there is no data.
- A line joins points that are not ordered by the axis variable.
- A stacked chart's segments do not sum to something meaningful.
- A chart is being built and the sentence describing what is being compared was never written.
- The library was chosen before the destination was named.
- A chart carries no units, no period and no source table.

## Verification

- [ ] The comparison the chart is for is written down in one sentence, before the form was
      chosen.
- [ ] The forms ruled out by the shape of the data are named, with the measurement that ruled
      them out, such as the category count or the presence of gaps.
- [ ] The chosen form encodes the key comparison as position or length, or the reason for going
      lower on the accuracy order is stated.
- [ ] Any bar chart's value axis starts at zero and any time axis is in order with gaps broken.
- [ ] The library is named together with the destination that decided it, and any new dependency
      is stated as one.
- [ ] The chart carries its units, its period, the filter behind it and the table it came from.
