# 17 — How an AI agent should design any user interface

## 0. The one sentence

**An interface is a tool somebody uses, not a document somebody reads.** Its job is to let a person do the
thing they came to do with the fewest decisions, the least reading and the least hesitation. Every word,
every box and every option either serves that or is in the way.

---

## 1. The failure mode this document exists to stop

An agent building a screen has read the whole codebase. It knows the edge cases, the reasons behind each
default, what the data means and what it does not. **It wants to pass all of that on, and the screen is
where it is currently typing.**

The result is always the same shape:

- paragraphs explaining how something works, above the thing itself;
- captions under every field, saying what the field's own label already says;
- caveats about what a number does not mean;
- labels borrowed from the code rather than from the user's own language;
- a layout that looks right with the one example in front of it and falls apart on real data.

**The reader does not share that context and did not come to acquire it.** Write for somebody who knows
their own job, does not know your system, and has thirty seconds.

---

## 2. Start with the job, not the data

Before writing anything, answer these three in one line each:

1. **Who is on this screen?**
2. **What are they trying to do?** One primary job, named as a verb.
3. **What do they do next?** The one action that ends the visit.

A screen with no answer to (2) becomes a wall of everything the system knows. A screen with four answers to
(2) should usually be more than one screen.

**Then design the primary path first** and let everything else be secondary, smaller, or behind a click.
One screen, one obvious main action.

---

## 3. The test every element must pass

Anything on the screen has to be one of:

1. **content** — the thing the person came for;
2. **a control** — something they can change or trigger;
3. **status** — a short fact about state they act on: a count, a stage, a version, a warning that applies;
4. **orientation** — where they are and how to get out: a title, navigation, a back path.

**If it is none of the four, delete it.** Not smaller, not dimmed, not collapsed — deleted. The three things
that fail this test most often are an explanation of how it works, a justification of why it is like that,
and a caveat about what it is not.

---

## 4. Words

### 4.1 The budget

Most screens need: a **title**, **labels**, **button text**, and **short status**. Anything beyond that
starts at "delete" and must earn its way back.

Aim for the shortest text that is still **exact**. Shortening by becoming vague is not an improvement — it
trades reading time for hesitation, which is worse.

### 4.2 Write labels as the user's question, not the system's field

| Bad — the code's name | Good — the user's question |
|---|---|
| "Entity type selector" | "What are you looking for?" or just the options |
| "Transaction state filter" | "Status" |
| "Submit query parameters" | "Search" |
| "Configure notification preferences" | "Notifications" |

### 4.3 Buttons say what happens

A button is a **verb**, or the **destination**. `Save`, `Send invite`, `Delete account`, `Export CSV`.
Never `OK`, `Submit`, `Continue` when something more specific is true — and never a noun on its own.

In a confirmation, the buttons repeat the choice rather than answering a question: `Delete 12 files` and
`Cancel`, not `Yes` and `No`.

### 4.4 Do not caption what the label already says

A field labelled *Email* does not need "Enter your email address". A helper line is for something the label
genuinely cannot carry: a format constraint, a consequence, a limit. If there is nothing like that, there is
no helper line.

### 4.5 Never explain your architecture

Which service, which cache, which store, which job answered is your problem, not theirs. The exception is
when it **changes what the person may conclude or do** — the data is incomplete, stale, or partial. That is
a warning, it is rare, and it is drawn only when it applies. A caveat shown on every load is wallpaper.

### 4.6 The tone rules

- **No apologising.** "Sorry, something went wrong" tells nobody anything. Say what happened and what to do.
- **No congratulating.** "Great job!" for filling a form is noise.
- **No hedging.** "This may sometimes take a while" — say roughly how long, or say nothing.
- **No marketing inside a tool.** Tools are used, not sold.
- **Sentence case** for everything. Title Case Everywhere Reads Like A Headline.

---

## 5. Layout and space

### 5.1 Put controls next to what they control

A control at the far right of a wide screen, changing a table at the far left, is a control nobody sees. Put
the primary toggle **beside the title**, and filters **directly above the thing they filter**.

Reading starts top-left. So do the controls.

### 5.2 Proximity is meaning

Things that belong together sit together; things that do not are separated by real space. A gap in the
middle of a group says "these are unrelated" — so an accidental gap is a lie about your own content.

### 5.3 Design for real data, not for the example

This is where most layouts break. For every piece of dynamic text, ask:

- what does this look like at **1 character**, and at **200**?
- what if it is **missing**?
- what if there are **zero** of them, or **ten thousand**?
- what about a different language, a right-to-left script, an emoji, a very long unbroken word?

Then: truncate long values with the full value available on hover or on tap, never let one item set the
height of a whole row, and never let a container be sized by its happiest case.

### 5.4 Tables get their own rules, because they break most

- size the table to its **content**, and let a scroll container handle overflow — a table stretched to the
  window hands the slack to whichever column has no fixed width and grows a hole in the middle of the row;
- **fix the width of any column that always truncates** — an id, a hash, a code;
- **fix the width of a column of chips or badges**, wide enough for the most any row carries;
- keep the header visible while scrolling;
- right-align numbers and use tabular figures so digits line up;
- let the user choose **how many rows per page** and **sort by any meaningful column**.

### 5.5 Responsive means two real checks, not a breakpoint list

Open it very wide, and open it narrow. Wide: does a control drift away from its content, does a gap appear,
does a line of text become unreadably long (keep prose under about 75 characters a line)? Narrow: does
anything overlap, clip, or need horizontal scrolling that is not a table?

### 5.6 Images and media are content, not decoration

Show them big enough to serve their purpose. A thumbnail so small that the subject cannot be recognised is
costing space and giving nothing. If the displayed version is a compressed or cropped derivative, give
access to the original — and never present the derivative as if it were the original.

Always reserve the space an image will occupy so the page does not jump when it loads.

---

## 6. Choosing the right component

| Job | Use | Avoid |
|---|---|---|
| compare many records on the same fields | a table | cards, which hide the comparison |
| browse a few rich items | cards or a list | a table with two columns |
| pick one of 2–4 known options | segmented control / radio | a dropdown |
| pick one of many | a searchable select | a long radio list |
| pick several | checkboxes or multi-select | several toggles that interact |
| an irreversible or costly action | a button with a confirm | a toggle that acts instantly |
| a short, non-blocking result | an inline message | a modal |
| a focused sub-task | a modal or a side panel | a new page for two fields |
| a substantial sub-task | its own page with a URL | a modal nobody can link to |
| extra detail on one element | a tooltip or a disclosure | a paragraph beside it |
| status of a background job | a persistent indicator | a toast that disappears |

**Two rules underneath the table.** Use the same component for the same job everywhere in the product; and
prefer the boring, expected pattern over a clever one — people arrive with habits, and a novel control
spends their attention on learning rather than on doing.

---

## 7. Every state, not just the good one

A screen has at least five, and an agent typically builds one.

| State | What it must do |
|---|---|
| **loading** | hold the layout steady — skeletons in the shape of the content, not a spinner that collapses the page. Nothing for very fast things |
| **empty — nothing yet** | say how to create the first one, and offer that action |
| **empty — nothing matched** | say which filter to relax, and offer to clear it |
| **partial** | show what arrived and mark what did not |
| **error** | what happened, in the user's terms, and the one thing to do next. Keep their input. Offer a retry |
| **success** | confirm briefly and get out of the way |

### 7.1 How to render absence

| Situation | Draw |
|---|---|
| a value this record does not have | a dash |
| something that was never measured or run | a dash — **never a zero**, and never a neutral "ok" |
| a background reading that failed | nothing, and log the reason where a developer looks |
| an optional section with no content | nothing at all |

**A zero and an absence are different facts.** Rendering "unknown" as `0` states something false with
confidence, which is worse than leaving it blank.

### 7.2 Do not draw an empty state that says nothing

A large panel reading "No results yet" occupies exactly where the answer will appear and tells the person
what they can already see. Keep an empty state only when it changes what they do next.

---

## 8. Forms and input

- **Ask for as little as possible.** Every field is a reason to abandon.
- **Sensible defaults**, so the common case is already filled in.
- **Validate on leaving a field, not on every keystroke** — and never move, disable or re-order things while
  somebody is typing.
- **Errors sit on the field**, say what is wrong and what is acceptable, and never discard what was entered.
- **Mark whichever is rarer** — optional or required — not both.
- **An expensive action is explicit.** If a keystroke would trigger a slow or costly operation, put it
  behind a button or Enter. Cheap and instant filtering can be live.
- **Say what will happen before it happens** for anything destructive, and name the thing in the button.
- **Never lose work.** Preserve input across errors, navigation and reloads where you reasonably can.

---

## 9. Speed, as it is experienced

- Make the **first meaningful thing** appear fast; the rest can follow.
- **Reserve space** for anything that loads late, so nothing shifts under a moving cursor.
- Under ~100 ms feels instant and needs no indicator; beyond about a second, show progress; beyond several
  seconds, say what is happening and let people keep working.
- **Show what you already have** rather than a blank page waiting for everything.
- Make repeated actions cheap — do not re-fetch what has not changed.

---

## 10. Accessible by default

Not an extra pass. The floor:

- **every control reachable and operable by keyboard**, in a sensible order, with a visible focus ring;
- **every input has a real label** — placeholder text is not a label, it disappears exactly when needed;
- **contrast** that holds for body text and for the small grey text agents love;
- **never colour alone** to carry meaning — pair it with a word, a shape or an icon;
- **touch targets** big enough to hit, with space between them;
- **images have alt text** that says what matters, and decorative ones are marked as decorative;
- **respect the system's settings**: reduced motion, text size, dark mode;
- **announce changes** that happen away from the cursor — a result count, an error, a saved state.

---

## 11. Honesty

An interface should never state more certainty than it has.

- do not show placeholder or sample data as though it were real;
- do not round a number until it says something different;
- do not hide a failure behind a cheerful message;
- do not present an estimate as a measurement;
- if something is stale, partial or approximate **and it changes a decision**, say so — once, where it
  applies, in one short line.

---

## 12. Consistency

- one component per job, product-wide;
- one vocabulary — a thing keeps its name across every screen, message and email;
- spacing, type and colour from the system's scale, not per-screen values;
- the same action in the same place on every screen of the same kind.

An interface where each screen was designed fresh is one where nothing learned on one screen transfers to
the next.

---

## 13. The pass to run before shipping any screen

Do it literally. It takes minutes and catches most of this document.

1. **Say out loud what this screen is for, in one sentence.** If you cannot, it is more than one screen.
2. **Read every sentence on the screen.** Delete each that is not a label, a control, or a fact acted on.
3. **Count the words above the first piece of real content.** More than ~10 means the header is a paragraph.
4. **Open it very wide.** Do controls drift from their content? Does a gap open mid-row? Are lines of prose
   too long?
5. **Open it narrow.** Anything overlapping, clipped, or scrolling sideways?
6. **Render the longest realistic value** in every dynamic slot. Then the shortest. Then none.
7. **Look at every button.** Does it say what will happen?
8. **Look at every helper line.** Does it add something the label cannot carry?
9. **Check loading, empty, partial, error** — not only success.
10. **Tab through it** with no mouse. Can you complete the main job?
11. **Search the screen for internal names** — services, tables, fields, jobs. Replace or delete.
12. **Ask whether a first-time user would know what each label means** with no explanation.

---

## 14. The anti-patterns, named

So they can be recognised quickly in a review.

| Name | What it looks like |
|---|---|
| **the lecture** | a paragraph above the content explaining how the system works |
| **the caveat wall** | warnings shown every time, so nobody reads the one that matters |
| **the glossary in place** | defining columns or terms on the screen instead of in a tooltip |
| **the code's vocabulary** | labels named after fields, classes, endpoints or internal modes |
| **the example-shaped layout** | perfect with the one sample value, broken with real data |
| **the stretched table** | a hole in the middle of every row on a wide screen |
| **the far-away control** | a filter pinned opposite the thing it filters |
| **the confident zero** | "not measured" rendered as `0` |
| **the apology** | "Sorry, something went wrong." |
| **the decorative thumbnail** | an image too small to tell what it is |
| **the hidden action** | the thing people want to do exists, but nowhere on the screen |
| **the frozen default** | page size, sort or range hard-coded where the user should choose |
| **the empty empty-state** | a big panel saying "nothing yet" where the answer will go |

---

## 15. What minimal does not mean

Minimal is about **removing words and decisions**, not capability.

- **not** hiding actions people need — a hidden affordance is a missing feature;
- **not** removing the controls that give people command of their own view;
- **not** stripping labels until things are ambiguous;
- **not** shrinking content below the size at which it can be read or recognised;
- **not** deleting a warning that genuinely changes a decision.

**Remove the sentences. Keep the power.**

---

## 16. Where the deleted text goes

Nothing here says the explanations are worthless — only that the screen is the wrong place for them.

| What it is | Where it belongs |
|---|---|
| how a feature works | help documentation, linked once |
| why a decision was made | the design or implementation record |
| what a field means | that field's tooltip or helper line, in one line |
| what an API returns | the API's own schema description |
| a rare but important caveat | the response itself, drawn only when it applies |
| onboarding for a complex flow | a first-run tour people can dismiss for ever |

---

## 17. When in doubt

**Build the content, add the controls, and stop.**

Then take one more thing away and see whether anybody misses it.
