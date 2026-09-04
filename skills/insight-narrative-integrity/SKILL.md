---
name: insight-narrative-integrity
description: Checks that a finding survives its own arithmetic before it becomes a sentence: weighted averages instead of averages of averages, comparisons that reverse when groups are pooled, unlabelled buckets kept out of rankings, and a stated base behind every percentage. Use when writing takeaways or a summary, when naming the top or best performing segment, channel or period, when reporting growth or a decline as a percentage, or when saying that something drove or caused a change.
---

# Insight narrative integrity

## Overview

An insight is arithmetic wearing a sentence. The arithmetic is where it fails, and the sentence
is what hides the failure, because prose has no place to show that the average was taken over
the wrong denominator or that the leader of a ranking is a bucket named "Other".

This skill is the last gate before a number becomes a claim. It assumes the data is clean and
its coverage disclosed; the `etl-before-dashboard` skill owns the first and the
`honest-data-limits-disclosure` skill owns the second. What is checked here is whether the
sentence follows from the numbers.

## When to Use

Use this skill whenever text is generated about aggregated data: takeaways, an executive
summary, a ranking, a period comparison, an alert, or a caption under a chart.

Use it whenever a superlative, a percentage change, or a causal word is about to be written.

Do **not** use it to check whether the data is correct; that happened earlier. It does not
replace the coverage statement, so do not restate sampling here instead of disclosing it. Do
not apply it to raw descriptive output such as a table of counts with no claim attached, unless
a sentence is being written on top of it.

## Core Process

### Step 1: Rebuild every average from its components

An average of averages is only correct when every group has the same weight, which almost never
happens with real data. Recompute from sums and counts:

```
weighted mean = sum(all values) / count(all values)
              = sum(group_sum) / sum(group_count)
```

The size of the error is not marginal. Two regions, one with 10 orders averaging 100 and one
with 90 orders averaging 20:

| Method | Result |
| --- | --- |
| Mean of the two group means, `(100 + 20) / 2` | **60.00** |
| Weighted mean, `2800 / 100` | **28.00** |

The naive figure is 2.14 times the true one, and both are plausible-looking numbers. The same
rule governs every ratio: rates, conversion percentages and per-unit costs are recomputed from
their numerators and denominators, never averaged across groups.

This is also why the `etl-before-dashboard` skill stores a sum and a count rather than a mean.
Once only the mean is stored, the correct number cannot be recovered.

### Step 2: Check whether combining the groups reverses the result

Separately from weighting, a comparison that holds inside every group can invert when the groups
are pooled, if the groups differ in size and in difficulty. Two treatments, each on 350 patients:

| Treatment | Small stones | Large stones | Overall |
| --- | --- | --- | --- |
| A | 81/87 = 93.1% | 192/263 = 73.0% | 273/350 = **78.0%** |
| B | 234/270 = 86.7% | 55/80 = 68.8% | 289/350 = **82.6%** |

A wins in both groups and loses overall, because A was used mostly on the hard cases. Neither
number is wrong. The question decides which one answers it: to choose a treatment for a patient
whose stone size is known, the group figures answer; the pooled figure describes how the
treatments were assigned, not how well they work.

So: compute the comparison inside the groups as well as overall. When the two disagree, say so
and name the variable that differs between them. Never report only the pooled number when it
disagrees with every group.

### Step 3: Refuse a ranking that contains an unlabelled bucket

A category named "Other", "Unknown", "N/A", "Uncategorized" or blank is not a competitor. It is
the residue of a categorization that did not finish, and it is usually large:

| Category | Share |
| --- | --- |
| Other | 31% |
| Direct | 12% |
| Search | 11% |
| Email | 9% |

"Direct is the top channel at 12%" is true about the named categories and misleading about the
data, because the biggest group is 2.6 times the stated leader and has no name. Exclude such
buckets from any superlative, and state their size next to the ranking. When the bucket is
larger than the leader, the honest finding is that the data is not categorized well enough to
support a ranking at all.

### Step 4: State the base of every comparison

A percentage without a base is not a fact. Every comparison names what it is against:

- **Against which period**, with both endpoints: "up 40% against the same month last year",
  not "up 40%".
- **Against which population**, when a subset is compared with a whole.
- **From what starting value.** A rise from 2 to 3 is 50% and is also two events. Give the
  absolute numbers alongside any percentage computed on small counts.
- **Over how many observations.** A segment's result is reported with its size. A conversion
  rate of 100% over 3 visits is not a conversion rate.

Percentages and percentage points are different units and are not interchangeable: 20% to 25%
is a rise of five percentage points and of 25 percent.

### Step 5: Do not promote a correlation

Aggregated data supports statements about association. It does not, on its own, support a cause.
Before writing a causal sentence, check three things and, if any fails, write the associative
form instead:

1. **Something else moved too.** A campaign, a price change, a season, a release. Almost always
   something did.
2. **Composition changed.** A metric can move with no underlying change when the mix behind it
   changes; that is Step 2 again, in time order.
3. **The direction is assumed, not shown.** Support tickets correlate with usage; neither causes
   the other in the way the sentence implies.

Write "revenue rose 12% in the same period that the campaign ran", not "the campaign raised
revenue 12%". The first is what the data says. If the causal claim matters, name the experiment
that would establish it rather than asserting it.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "Averaging the regional averages is close enough." | It was off by 2.14 times in the example above, and nothing in the output would show it. |
| "The groups are roughly the same size." | Then say the sizes. Roughly is the word that precedes a weighting error. |
| "The overall number is the one they asked for." | They asked for the answer. When the pooled figure reverses every group, the pooled figure is not it. |
| "Other is a category like any other." | It is every category that was not identified. Naming it the leader reports a labelling failure as a finding. |
| "Everyone knows 'up 40%' means year over year." | Half the readers assume month over month, and both halves are confident. |
| "Saying 'associated with' sounds weak." | It sounds exactly as strong as the evidence. The confident version is a claim the data cannot pay for. |
| "The chart shows the trend clearly." | A chart of a wrongly weighted metric is a clear picture of a wrong number. |
| "It's a summary, the detail is in the table." | The summary is what gets quoted. The table is what nobody reopens. |

## Red Flags

- A mean computed from a column that is itself a mean, or `mean(` applied to a rate column.
- A superlative whose candidate list was never printed.
- Any ranking that has not been checked for "Other", "Unknown" or blank labels.
- A percentage in the output with no base, no period, or no denominator nearby.
- A percentage computed on a denominator below about 30, with no absolute count beside it.
- Causal verbs: "drove", "caused", "led to", "because of", "resulted in", "thanks to".
- A group comparison reported only in the aggregate, when group-level figures exist.
- A finding that is exactly what the requester expected, checked no harder than the others.

## Verification

- [ ] Every average and rate in the output was recomputed from sums and counts, not from
      group-level averages.
- [ ] Each group comparison was computed within groups as well as pooled, and a disagreement
      between them is reported, not resolved silently.
- [ ] Every ranking was checked for unlabelled buckets; any such bucket is excluded from the
      superlative and its size is stated.
- [ ] Every percentage names its base, its period and its denominator.
- [ ] Findings from small denominators carry their absolute counts.
- [ ] No causal verb survives without a stated mechanism or experiment; associative wording is
      used otherwise.
- [ ] The sample size behind each claim is stated, taking coverage from the disclosure rather
      than restating it here.
