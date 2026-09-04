---
name: dashboard-color-and-visual-hierarchy
description: Chooses the palette a variable's own type requires and keeps every mark and label readable, by never letting colour carry meaning on its own and by holding text to a measured contrast ratio on both grounds. Use when assigning colours to categories or to an ordered scale, when a status column is shown as a green or red fill and nothing else marks the state, when a design leans on colour alone to carry its message, when a page has so many accents that nothing stands out, or when checking that a palette survives a light and a dark background.
---

# Colour and visual hierarchy

## Overview

Colour is the least accurate encoding a chart has and the one people reach for first. That is
survivable when colour is decoration. It is not survivable when colour is the message: an ordered
scale rendered in unordered hues, two states that differ only by being red or green, a label
nobody can read against the background it landed on.

Three questions settle almost every colour decision, and all three have measurable answers:

1. What **type** is the variable — unordered, ordered, or ordered around a middle?
2. Is colour the **only** thing carrying the meaning?
3. What is the **contrast ratio**, against the ground this will actually be shown on?

## When to Use

Use this skill when assigning colours to anything that means something: categories, a scale, a
status, a highlight. Use it when reviewing a design that already exists, which is when the
mismatches are cheapest to find and most likely to be there.

Use it whenever a design will be shown on both a light and a dark background, because a colour
that works on one can fail on the other and nothing warns.

Do **not** use it to choose the chart's form, which is the
`chart-type-and-library-selection` skill, or to arrange several widgets on a page, which is the
`dashboard-layout-by-widget-mix` skill. It does not decide what the chart may claim; that is the
`insight-narrative-integrity` skill.

## Core Process

### Step 1: Match the palette to the variable's type

There are three palette types and picking the wrong one destroys information before anyone reads
a number.

| Variable | Palette | What the wrong choice does |
| --- | --- | --- |
| **Unordered categories** — channel, region, product | Distinct hues at similar lightness | A sequential palette invents an order the data does not have, and readers rank the categories by shade. |
| **Ordered, running one way** — a rating, a count, a rate | One hue, varying lightness from low to high | Distinct hues destroy the order: the reader cannot tell which of two colours is larger without the legend, on every single mark. |
| **Ordered around a meaningful middle** — profit and loss, change against a target, an index | Two hues meeting at a neutral centre, with the middle pinned to the value that matters | A sequential palette hides the crossing point, which was the whole finding. |

A categorical palette also has a ceiling. Past roughly seven or eight hues, the colours stop being
distinguishable and the legend becomes a lookup table the reader traverses for every mark. That is
a signal to group the small categories or to change the form, not to find more colours.

### Step 2: Colour never carries meaning alone

Whatever colour says, something else has to say too: position, shape, a direct label, a pattern,
or the value written on the mark.

The reason is measurable. Take a status green and a status red that each read comfortably against
a white background, at contrast ratios of 5.13:1 and 5.62:1. Against **each other** they are
1.10:1. To a reader who does not separate those hues, two states that differ only by being red or
green are the same mark, and nothing on the screen says otherwise.

So: a legend is not enough for a colour-only encoding, and neither is a tooltip that appears on
hover, because both make the reader do work to recover what the mark should have carried.

### Step 3: Measure the contrast, against the ground it will be shown on

The thresholds come from the accessibility standard and they are numbers, not impressions:

- **4.5:1** for normal text.
- **3:1** for large text, which means at least 18 point, or 14 point bold.
- **3:1** for interface components and for graphical objects that carry meaning, which includes a
  line, a bar edge or an icon the reader has to distinguish.

Compute the ratio rather than judging it. A grey that looks soft and professional at `#9AA0A6`
gives **2.64:1** on white, well under the threshold, and it is the most common failure in a design
that has otherwise been thought about.

### Step 4: Check both grounds, because one token can pass on one and fail on the other

The same `#9AA0A6` that gives 2.64:1 on white gives **7.09:1** on a near-black background. It
fails in light and passes in dark, which is why "it looks fine" is a statement about whichever
theme the person happened to be using.

Every colour that carries meaning is measured against both grounds. Where a single value cannot
pass on both, that is a token that needs two values, one per theme, not a compromise that is
slightly wrong everywhere.

### Step 5: One emphasis, and everything else quiet

Visual hierarchy is created by difference, so it is spent by use. A page where four things are
highlighted has nothing highlighted.

- Choose **one** accent colour and let it mean "look here". Everything that is not the point is
  neutral: greys, and the ink of the data itself.
- Rank the page's contents before styling them. The one number the page exists for gets the
  emphasis; supporting figures are readable and unremarkable; context is quiet.
- Grid lines, axis lines and borders are context. If they compete with the data, lighten them
  until they stop.

### Step 6: Write the palette down with its measurements

The design ships with a short table: each colour, what it encodes, its palette type, and its
measured ratio against both grounds. That table is what makes the next change checkable instead of
a matter of taste, and it is the thing nobody can reconstruct six months later.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "Red and green are universally understood." | They are, by people who separate those hues. Measured against each other they are 1.10:1, so for everyone else the two states are one state. |
| "The legend explains the colours." | A legend turns every mark into a lookup. That is the cost colour was supposed to save. |
| "It looks fine on my screen." | Your screen has one theme, one brightness and one pair of eyes. The ratio is a number and it takes a second to compute. |
| "The muted grey looks more professional." | At 2.64:1 on white it is not muted, it is unreadable for a share of the people you are writing for. |
| "We need eleven colours because there are eleven categories." | Eleven hues are not distinguishable. The chart needs grouping or a different form; the palette is not the problem to solve. |
| "Dark mode is just an inversion." | It is a different ground, so every ratio changes, some upward and some downward. Measure both. |
| "Everything important should stand out." | Then nothing does. Emphasis is a scarce resource and it is spent by use. |
| "The brand colours are fixed." | The brand colour can stay and still not be the one carrying meaning on a chart. Fixed does not mean it has to encode the data. |

## Red Flags

Stop when any of these is true:

- An ordered variable is drawn in unordered hues, or categories are drawn in a single-hue ramp.
- Two states differ only by colour, with no label, shape or position separating them.
- A diverging palette's midpoint is not at a value that means anything.
- More than about eight categorical colours are in play.
- A contrast ratio has not been computed for any text or mark that carries meaning.
- The design was checked on one background only.
- More than one accent colour is competing for attention on the same view.
- A colour was chosen because it matched, and nobody can say what it encodes.

## Verification

- [ ] Every colour-encoded variable is named with its type, and the palette matches that type.
- [ ] No meaning is carried by colour alone; each colour-encoded distinction also has a label, a
      shape, a position or a value.
- [ ] Contrast ratios are computed, not judged, for text and for marks that carry meaning, against
      the actual background.
- [ ] Text meets 4.5:1, large text and meaningful graphical objects meet 3:1, or the exception is
      stated with its reason.
- [ ] Both the light and the dark ground were measured, and any token that cannot pass on both has
      a separate value per theme.
- [ ] One accent carries the emphasis and everything else is neutral.
- [ ] The palette table ships with the design: colour, what it encodes, palette type, and measured
      ratios.
