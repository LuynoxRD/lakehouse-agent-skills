---
name: structured-vs-unstructured-routing
description: Decides what shape a source actually has before any analysis is chosen, separating a clean table from records whose fields differ from one another and from free text that has no columns at all. Use when a source is JSON with nested or uneven records, when a column holds sentences instead of values, when a task asks for themes or topics in written text, or when it is not yet clear whether the data is a table.
---

# Structured versus unstructured routing

## Overview

The first decision about a dataset is not how to clean it. It is what it is. A table, a pile of
records that mostly agree about their fields, and a column of sentences need three different
approaches, and the expensive mistake is treating one as another: flattening nested records by
hand until the shape is lost, or running a topic model over what was a categorical column with
forty values.

Shape is measurable. It does not need to be guessed.

```
source ──► measure the shape ──► tabular      → clean it and persist it
                             ├─► semi-structured → let the engine infer the union
                             └─► free text      → count first, cluster only if counting fails
```

## When to Use

Use this skill at the start, before profiling and before any modelling decision, whenever the
source is not obviously a rectangle: a JSON or newline-delimited JSON export, an API response, a
document dump, a support-ticket table with a long message column.

Use it when a request mentions themes, topics, sentiment or categories in text that nobody has
labelled.

Do **not** use it once the shape is settled and the data is tabular; profiling, cleaning and
persisting are the `etl-before-dashboard` skill. Querying what came out belongs to the
`duckdb-for-local-analytics` skill, and whether any of it may be sent anywhere belongs to the
`data-privacy-before-llm` skill.

## Core Process

### Step 1: Measure the shape instead of looking at it

Three numbers per column decide it, and none of them needs a model:

- **Mean and maximum string length.** Values of a few characters are codes; values of tens of
  characters are labels; values of hundreds are prose.
- **Distinct count against row count.** A low ratio is categorical however long the strings are.
  A ratio near one on short values is an identifier, not a category.
- **Vocabulary size.** Split on whitespace and count distinct tokens across the column, then
  compare that with the number of distinct values. A categorical column has both numbers small
  and close together; free text has a vocabulary many times larger than its category count would
  allow, and as many distinct values as it has rows.

For records rather than columns, count how many keys appear in **every** record and how many in
only some. That ratio is the difference between a table stored as JSON and a genuinely
semi-structured source.

Write the answer down as a decision with its numbers, the way an ambiguity in a profile is
recorded. "The `message` column averages 78 characters over a vocabulary of 2,900 tokens, so it is
free text" is a decision. "It looked like text" is not.

### Step 2: Tabular is not this skill's problem

If every record has the same fields and the values are scalars, the source is a table that
happens to be stored in another format. Read it as a table and hand it to the profiling and
cleaning process. Nothing here applies.

### Step 3: Semi-structured records: let the engine infer the union, do not flatten by hand

When fields differ between records, hand-written flattening code is where the data is lost: the
first record decides the keys, and everything the later ones added is dropped by a loop nobody
will re-read.

A query engine reading JSON does this correctly and it is worth knowing exactly how far it goes,
because it is further than most people expect:

- A field present in only some records still becomes a column, with nulls where it was absent.
- A nested object becomes a struct whose fields can be addressed directly, without flattening.
- Arrays of different lengths coexist in one column, including empty ones.

So the work is not extraction, it is **selection**: read the inferred schema, decide which fields
are worth promoting into a table of their own, and say which ones you are leaving in the nested
structure and why. A field that appears in three percent of records is a fact about the source
worth reporting, not a column to be quietly filled with nulls.

### Step 4: Free text: count before you cluster

The ladder goes in one direction and each rung has to fail before the next is worth its cost.

1. **Counting.** Pattern matches, keyword frequency, the vocabulary from Step 1. A surprising
   share of "find the themes" questions is answered by ten regular expressions and a count, and
   the answer is one anybody can check.
2. **Term-frequency vectors with a simple clustering.** No pretrained model, runs on a laptop,
   and available in the general-purpose machine learning library most projects already carry. It
   is the right rung for a few thousand documents.
3. **A topic model built on embeddings.** Only after rung two demonstrably fails.

Rung two fails in ways you can name, and naming them is what stops the escalation from being a
preference:

- The top terms of a cluster do not describe anything a person would call a topic.
- One cluster is obviously two subjects that share vocabulary.
- A cluster is defined by the most common word in the corpus rather than by a subject.
- Changing the number of clusters changes the story entirely.

An escalation is **proposed before it is performed**, and the order is the point:

1. **Say what the cheaper rung produced and how it fell short**, in specifics from this data, not
   in general terms about the method.
2. **Say what the heavier rung costs, before anything is installed or created.** Name the
   dependencies it adds, say that it pulls a pretrained model which has to be downloaded, and
   give the rough size of the tree. A cost mentioned after the install is a report, not a
   decision, and the person paying for it never got to say no.
3. **Say how it will be brought in.** Through the project's own package manager, so it is
   recorded and reproducible, or as an environment created for this run and discarded afterwards.
   **Never a bare global installation command:** an install line that lands in whatever
   interpreter happens to be first on the path is a change to somebody's machine that outlives
   the question it answered.
4. **Say where the text will be processed**, on this machine or at a service.

Only then set anything up. Every one of those four is a sentence, and together they are the
difference between an escalation somebody agreed to and one they discovered afterwards.

### Step 5: Embeddings run locally unless somebody decides otherwise, out loud

Turning text into vectors does not require sending it anywhere. Sentence-embedding models run on
a CPU, with no API key, and the documents never leave the machine. That is the default here.

Moving to a hosted embedding service, for volume or for quality, is a legitimate decision and a
transfer of every document embedded. It is stated before it happens, with what is being sent and
where, and it goes through the `data-privacy-before-llm` skill first. Never make that call
silently because the hosted path was fewer lines.

**Say where the text will be processed whenever embeddings enter the proposal, including when the
answer is that nothing leaves the machine.** Following the local default is not the same as
reporting it. To a reader who has seen both arrangements, silence about where the documents go
reads as the hosted one, and the person who would have objected never gets the chance.

### Step 6: State the shape you decided and what it cost

The answer names the shape, the numbers behind it, which rung of the ladder was used, and what
would move it to the next one. A run that jumped straight to the top rung has to say why the
cheaper ones would not have worked, and a run that stayed at the bottom has to say what would
change that.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "It is JSON, so it is unstructured." | Most JSON is a table with extra punctuation. Count the keys that appear in every record before deciding. |
| "I will flatten it first and then look." | The flattening is the decision, made before you looked. Whatever the first record lacked is gone. |
| "The column has words in it, so it needs a topic model." | A column of forty repeated words is categorical. Vocabulary size distinguishes them in one line. |
| "Clustering is more thorough than counting." | It is less checkable. A count can be audited by anyone; a cluster has to be argued for. |
| "The topic model is one install away." | It is a pretrained model download and a heavy dependency tree. That is a cost the person paying for it should hear about first. |
| "Embeddings through the API are better." | Possibly, and they are also every document leaving the machine. That is a decision, not an implementation detail. |
| "The nested field only appears sometimes, so I dropped it." | How often it appears is a finding. Report the share; do not delete the evidence. |

## Red Flags

Stop when any of these is true:

- A flattening loop is being written before the inferred schema has been read.
- A topic model is being proposed and no counting was tried.
- A column is being treated as free text and its distinct count is under a hundred.
- A clustering result is being reported and nobody can name what a cluster is about.
- Text is going to a hosted service for embeddings and the answer does not say so.
- A field present in a minority of records was dropped rather than reported.
- The shape of the source was decided by looking at the first few rows.

## Verification

- [ ] Every column or field is classified as tabular, semi-structured or free text, with the
      lengths, distinct counts and vocabulary sizes that decided it.
- [ ] For records, the share of keys present in every record against those present in some is
      stated.
- [ ] Nested or uneven records were read through an inferred schema rather than a hand-written
      flattening pass, and the fields left nested are named.
- [ ] For text, the cheapest rung that answered the question is the one used, and if a heavier
      one was used the failure of the lighter one is described.
- [ ] Any escalation names its cost, including a model download, before it is proposed.
- [ ] If embeddings were computed, the answer says whether that ran locally or through a hosted
      service.
