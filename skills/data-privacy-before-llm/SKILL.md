---
name: data-privacy-before-llm
description: Decides what may leave the project before any rows reach a model or a hosted service, by finding the fields that identify a person, sending a profile or a masked form instead of the values, and recording what was sent. Use before pasting rows, a sample or a file into a prompt, before calling a hosted API with data in it, or when a dataset holds names, emails, phone numbers, addresses, free-text notes or account identifiers.
---

# Data privacy before an LLM

## Overview

Putting rows in a prompt is a transfer. The moment they are in, they have left the project, and
nothing later undoes it: no deletion, no policy, no retention setting reaches back and makes the
send not have happened.

The failure is almost never a decision to leak data. It is that no decision was made at all. The
rows were there, the question needed them, and the send happened as a side effect of getting the
answer.

```
data ──► what identifies a person? ──► profile, or masked, or aggregate ──► out
                                                    │
                          raw values only after the send is stated and recorded
```

## When to Use

Use this skill before any data leaves the machine or the project: pasted into a prompt, attached
to a request, sent to a hosted API, or handed to a service that computes something over it,
including one that only returns numbers such as an embedding service.

Use it whenever the dataset holds people: customers, employees, patients, users, applicants,
respondents. Use it as well when the dataset merely *might*, which is what a free-text column
means.

Do **not** use it to decide what a run covered, which belongs to the
`honest-data-limits-disclosure` skill, or how values were cleaned, which belongs to the
`etl-before-dashboard` skill. Reaching the rows in a live system belongs to the
`safe-live-database-access` skill; this one starts once the rows are in hand and something is
about to be sent.

## Core Process

### Step 1: Read the file without sending it, because the first read is already a send

An agent that opens a file with a tool has put its contents into its own context, and that
context goes to a model on this turn and on every turn after it. Printing the file to find out
whether it may be printed is a decision taken one step too late, and it is the most common way
this skill gets skipped by the very run that is applying it.

So the inspection is bounded from the start:

- Read the header and a handful of rows, enough to see the shape, never the whole file.
- Better, let a script do the reading and print only what the inventory needs: column names,
  types, null and distinct counts, ranges, and pattern counts such as how many values in a text
  column contain an at sign, a run of digits long enough to be a phone number, or a postcode
  shape. The script sees the values; the context sees the numbers.
- A free-text column still has to be examined, and examining it puts some of it into the
  context. Do that deliberately: match patterns across the whole column with a script, report the
  counts, and read at most one or two examples chosen because they matched, not because they came
  first.

### Step 2: Find what identifies a person, not what looks sensitive

Write the inventory from what the profile printed: every column, which category it falls into,
and why.

- **Direct identifiers** name someone on their own: full name, email address, phone number,
  national or tax identifier, account or customer number, street address, exact date of birth,
  device or user identifier, full IP address.
- **Quasi-identifiers** name someone in combination. A postcode, a birth date and a sex identify
  a large share of a population between them, and none of the three looks sensitive alone. Job
  title plus employer plus city does the same in a small company.
- **Free text** is the category that defeats column-level thinking. A `note`, `comment`,
  `description` or `subject` column can hold anything a person typed, including the email address
  and the phone number that were carefully removed from their own columns.

A column list is not an inventory until the free-text columns have actually been read, at least
in sample, for what they contain.

### Step 3: Send the profile, not the rows

The default is that values do not leave. A profile does: column names, types, null counts,
distinct counts, ranges, distributions, a few *synthetic* examples that show the shape without
being anyone's data.

Most questions asked of a dataset are answerable from that. "Which column holds the revenue",
"why does this join produce duplicates", "what does this distribution suggest" need structure,
not people. Sending rows to answer them is paying a permanent cost for a convenience.

When a reason is offered for why sending is fine, answer that reason before deciding anything.
"The provider does not train on it", "it is our own data", "it is only a sample", "the customer
agreed to the terms" are each true and each about something else: what happens after a transfer,
who owns the rows, how many there are, what was consented to in general. None of them says
whether this transfer should happen, and one sentence saying so is what stops the same reason
from settling the next one silently. Answer it, then reduce the data anyway.

### Step 4: When values genuinely must go, reduce before masking

In order of preference:

1. **Aggregate.** A count per group answers most questions and identifies nobody — but only
   after the check below. Aggregating is not by itself a protection.
2. **Pseudonymise.** Replace each identifier with a stable token so rows still join, and keep the
   mapping inside the project. The mapping never goes in the prompt; if it does, the
   pseudonymisation was decoration.
3. **Mask.** Truncate, hash or redact what is left.

**Small counts are their own control, and it applies to a single dimension.** Before an aggregate
is published or sent, check every group's size and suppress or combine the ones below a stated
floor. The floor is written down once and applied to every panel on the page; a group that gets a
looser standard than its neighbours is the one worth asking about.

The common mistake is to reason that a count is safe because it was not crossed with anything.
It does not hold. If somebody knows their own record is in a group of two, the published count
tells them there is exactly one other person, and everything they already know about the
population narrows who that is — no join with a second attribute required. That is why statistical
disclosure control treats small-cell suppression as a control in its own right rather than as a
consequence of not cross-tabulating.

Combining is usually cheap and is the first move: two adjacent periods, two neighbouring
categories, or a residual bucket that is named as one. Say which groups were combined and why,
because a reader comparing two pages will otherwise see the categories change and not know it was
deliberate.

Say what the technique protects against. Masking the direct identifiers while leaving the
quasi-identifiers intact does not anonymise a row; it removes the label from a record that can
still be matched back. Calling that "anonymised" is the claim this step exists to prevent.

### Step 5: Local by default when text has to be embedded

Turning text into vectors does not require sending it anywhere. Sentence-embedding models run
locally on a CPU, with no API key and no data leaving the machine, and that is the default for
this pack.

Moving to a hosted embedding service, for volume or for quality, is a legitimate choice and a
transfer of every document embedded. It is stated before it happens, in the answer, with what is
being sent and where. Never call out silently because the hosted path was easier to write.

### Step 6: Record what left, before it leaves

Append to `docs/data/disclosure.md`: which columns, how many rows, in what form, to which service,
when, and what the transfer was for. Write it as part of doing the send, not afterwards.

A record written afterwards is a reconstruction. The point of the record is that the decision was
visible at the moment it was taken, so somebody can disagree with it while it still matters.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "It is only a sample." | A sample of people is people. Twenty rows is twenty individuals, and it is the sample that gets pasted because it is small enough to paste. |
| "The provider does not train on this data." | That is a statement about what happens after the transfer. The transfer is what needed a decision. |
| "The data is internal." | Internal describes who may read it, not where it may go. Sending it outward is exactly the boundary the word was drawing. |
| "I removed the names." | Names are the easy part. The birth date, the postcode and the free-text note are still there, and together they still point at a person. |
| "It is anonymised." | Against whom, by what technique? If the answer is not ready, the word is doing work the data does not support. |
| "The user pasted the rows themselves, so it is their call." | It is. Saying what was in them is still yours, because they may not have read the free-text column either. |
| "Masking every column makes the analysis useless." | Then the analysis needs an aggregate, not raw rows. Useless output is the signal that the wrong shape was chosen, not permission to send everything. |
| "It would take longer to profile it than to send it." | True, and the profile is the part that is reusable. The send is the part that cannot be taken back. |
| "I have to read the file before I can tell whether it is sensitive." | Reading it into the context is the send. Read the header, then let a script report what is in the rest. |

## Red Flags

Stop when any of these is true:

- Rows containing a direct identifier are about to appear in a prompt.
- A file that may hold personal data is about to be printed whole in order to look at it.
- A file is about to be attached to a request without having been opened and inventoried.
- A column was called anonymised and no technique is named.
- A free-text column is being sent and nobody has read a sample of what is in it.
- Text is being embedded through a hosted service and the answer does not say so.
- Rows have been sent and no record exists of which ones or why.
- The masking removed the identifiers but kept the postcode, the birth date and the sex.

## Verification

- [ ] The file was inspected without being printed whole: the inventory was built from a
      profile, a header and a bounded sample, not from the contents in the context.
- [ ] Every column is classified as direct identifier, quasi-identifier, free text or neither,
      with a reason.
- [ ] Free-text columns were sampled and read before any decision about sending them.
- [ ] What was sent is the profile, an aggregate or a masked form, and the choice is stated.
- [ ] Any pseudonymisation mapping stayed inside the project and appears nowhere in a prompt.
- [ ] If text was embedded, the answer says whether that ran locally or through a hosted service.
- [ ] `docs/data/disclosure.md` records what left, how many rows, in what form, where to and why.
