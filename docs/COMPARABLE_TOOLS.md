# G128 — Comparable tools, and what this product should look like

> **Operator, 2026-08-20c:** *"a full-scale analysis of comparable tools (whether they are
> energy-related, financial, accounting, real estate, or other applications) to provide a better
> layout for each feature, ensure professionalism, and to simply better understand HOW we should
> be showing all of our data — it looks like an intern made this, and we need to turn this from a
> simple project into an actual service that users would pay for."*

⚠ **Read `docs/REFERENCE_TOOL_GAP.md` first, and note that it answers a different question.** That
audit is about *screening mechanisms* — which filters the operator's own two tools carry that we
do not. This one is about *presentation*: given the data we hold, how should it be laid out. Its
#1 recommendation (radius-from-a-point search) was **DECLINED** by the operator, so it is a source
of ideas and not a plan.

⚠ **This had to come after G123.** G123 stripped 49 static prose blocks to Insights and hid 11,964
runtime explanation blocks behind one policy. Designing before that would have been designing
around text that was about to be deleted.

---

## 1. THE DIAGNOSIS, MEASURED RATHER THAN FELT

"It looks like an intern made this" is a judgement, but the thing underneath it is countable.

| page | headings | tables | cards | controls | what that means |
|---|---:|---:|---:|---:|---|
| `si.html` | **38** | **40** | **53** | 0 | ⛔ the worst case. Thirty-eight separate questions on one scroll |
| `market.html` | 19 | 17 | 17 | 6 | four unrelated subjects: demand, generation, reliability, price |
| `community.html` | 12 | 16 | 18 | 6 | receipts, posture, ordinances and the legislature |
| `grid.html` | 14 | 14 | 16 | 7 | two RTOs × two directions × costs × constraints |
| `data.html` | 11 | 12 | 18 | 1 | inventory, provenance and honesty, interleaved |
| `index.html` | 5 | 0 | 0 | **98** | the console. Controls are the content |
| `screener.html` | 1 | 2 | 0 | **48** | one job, done in one accordion |

**The pattern is not ugliness. It is that six of eight pages are ANTHOLOGIES.** They are ordered by
how the data was built, not by a question anyone arrives with. `si.html` opens with *"Why this many
and not more? — the whole funnel, with every loss named"*, which is a **build diary**, not a
finding. A reader who wants to know *which owners might sell me land* has to scroll past four
sections of methodology to reach it — and that section is fifth.

⛔ **Two pages call themselves different things in the nav and in the title bar** — `index.html` is
"Map console" in the nav and "Indiana Siting Intelligence" in the title; `grid.html` is "Power &
grid" against "Grid & Capacity". Small, and exactly the kind of thing that reads as unfinished.

---

## 2. THE COMPARABLES, AND THE ONE PATTERN EACH IS WORTH COPYING

Four industries, as the operator specified. Each entry is the *pattern*, not the product.

### Financial terminals — Bloomberg, FactSet, PitchBook
⭐ **The pattern: a fixed HEADER BAR of the four or five figures that identify the record, then
everything else below it.** A Bloomberg security page opens with last / change / bid / ask in a
band that never moves, whatever tab you are on. You always know what you are looking at.
⭐ **Second pattern: tabular numerals, right-aligned, one row per fact.** A column of numbers you
can compare by eye without reading them is the single highest-value typographic decision in a
dense product, and it costs one CSS property.
⚠ **What NOT to copy:** the density of a terminal assumes a trained daily user. Our reader is an
energy professional but a *first-time* one.

### Real estate — CoStar, LoopNet, Crexi, Reonomy
⭐ **The pattern: the RECORD IS THE PRODUCT, and it has a fixed order.** Every CoStar property page
runs identity → location → size → tenancy → financials → comparables, in that order, every time.
A user learns the shape once and then navigates by muscle memory.
⭐ **Second pattern: the address and a map thumbnail are always above the fold.** A property record
that does not immediately say *where* is not a property record. **This is exactly what G125 just
fixed** — the popup and dossier now open with a Where block.
⭐ **Third: near-miss handling.** LoopNet shows "3 more within 10% of your criteria" rather than
silently dropping them. **This is what G129 just implemented**, at 259 sites.

### Accounting and audit — Xero, NetSuite, workpaper tools
⭐ **The pattern: every figure is click-through to its source, and provenance is a discipline, not
a footnote.** ⭐ **We are already ahead here** — `.prov` lines name the BigQuery table, the row
count and the build time on every panel. That is the single most professional thing in this
product and it should become *more* prominent, not less.
⚠ But: an audit tool separates the **statement** from the **workpaper**. Ours interleaves them.
`si.html`'s funnel is a workpaper. It belongs behind the statement, not in front of it.

### Energy — Orennia, Enverus, Aurora, Pearl Street
⭐ **The pattern: a SCORE with its components exposed, never a black box.** We do this
(`scoreSite` publishes every part and leaves unmeasurable parts out of the denominator).
⭐ **Second: the map and the table are ONE surface with a shared selection**, not two pages.
⚠ **What NOT to copy: Orennia estimates 91.9% of PJM bus positions.** Matching that means matching
an estimate. Our refusal to place a bus below a confidence threshold (G126) is a *feature*.

---

## 3. THE ONE THING EACH PAGE IS FOR

This is the decision G128 asks for. One sentence each; anything that does not serve it is a
candidate for Insights or for deletion.

| page | the ONE question | what must move |
|---|---|---|
| **Insights** | *I am new — what does this tool hold and what can it tell me?* | now also the home of every relocated "why" (G123) |
| **Map console** | *Where are the candidate sites, and what is around them?* | nothing; it is the most focused page we have |
| **Site screener** | *Give me a ranked shortlist against my criteria.* | nothing; one job, done well |
| **Power & grid** | *Can this site get power, and what will the interconnection cost?* | the constraint/branch tables are a workpaper → Insights |
| **Market & cost** | *What will power cost here, and who sells it?* | demand and generation-mix are context → Insights |
| **Community & local rules** | *Will this county let me build?* | the receipts browser is provenance → keep, demote |
| **Owner signals** | *Which owners might sell, and how strongly do we believe it?* | ⛔ the funnel, the exclusions and the coverage ledger are all workpaper. The ANSWER should be first |
| **Data & sources** | *Can I trust this, and where did it come from?* | nothing; being an anthology is correct here |

---

## 4. WHAT WAS EXECUTED IN THIS PASS

⚠ Deliberately typographic and structural rather than a content re-cut. G123 had just moved 49
blocks and hidden 11,964 more; re-ordering eight pages' sections in the same session would have
made every regression untraceable to a cause.

1. **A shared record grammar in `style.css`** — the financial-terminal patterns, applied globally:
   tabular numerals (`font-variant-numeric: tabular-nums`) so digits align in a column; numeric
   cells right-aligned; tighter, consistent row rhythm; sticky table headers so a 500-row scroll
   keeps its column names; zebra striping on long tables.
2. **A standard page header** — every page states its name, its ONE question, and its headline
   figure in the same place, in the same shape.
3. **Nav and title reconciled** on the two pages where they disagreed.
4. **The Where block** (G125) — address and coordinate above everything else on the popup and the
   dossier, which is the real-estate record pattern.
5. **Mode badges on every filter** (G129) — GATE or PREF, so a reader can tell a zero-result search
   from a filtered-out one.

## 5. WHAT IS DELIBERATELY LEFT

⛔ **Re-ordering `si.html`, `market.html`, `grid.html` and `community.html` so the answer precedes
the workpaper.** This is the largest remaining win and it is a *content* decision per page — which
of 38 sections on `si.html` is the answer, and which is the diary. It needs the operator's eye, and
doing it blind in the same session as G123 would be two large uninstrumented changes at once.

⚠ **13 runtime `.sowhat` blocks** could not be relocated because each wraps a live `id` the page's
script writes into (`<div class="sowhat" id="wd-answer">measuring…</div>`). The VALUE is what G123
wants to keep; only the sentence around it should go, and separating them is a per-block edit that
belongs with the re-ordering above.

⛔ **Everything in `REFERENCE_TOOL_GAP.md` §2 remains blocked on data, not layout.** Upgrade tier,
lead time and upgrade risk cannot be drawn because we cannot answer them, and drawing the control
without the data would be worse than the gap.

**The disclosure rules survive all of it** — the cap line, the three-state wording, the vendor
badge, the 2020 vintage, the estimate flag. A more professional tool is not one that hides what it
does not know.
