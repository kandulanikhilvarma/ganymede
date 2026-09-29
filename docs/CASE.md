# Ganymede, the case

Recovery Intelligence for lending, receivables, and investor-funded credit books.
One system, two lenses over the same decision: the Risk Lens picks who to contact
and when, the Coach Lens shapes how the conversation goes, and the outcome of that
conversation retrains both.

This document is the Day-100 deliverable the brief asked for: what was built, what
it shows, whether it is ready for a live pilot, and what is still missing.

---


> **Figures here are a snapshot.** The live site regenerates every number from the
> pipeline on each build (`python scripts/build_site_data.py`), so
> [ganymede-kandula.vercel.app](https://ganymede-kandula.vercel.app) is the
> authority if the two ever disagree.

## 1. What was built

Ten phases, each with a pass/fail gate, built strictly in sequence. Everything
below runs; nothing is a slide.

| Phase | Deliverable | Gate result |
|---|---|---|
| 1 Foundation | schema, invariants-as-code, experiment arms | 21 tests, invariants green |
| 2 Panel | 1.4M-row monthly borrower panel from Freddie Mac | verified: real dates, full roll curve, no leakage |
| 3 Risk models | L1 trajectory, L2 self-cure, reason codes | L1 AUC 0.66 beats base Brier; L2 AUC 0.76 |
| 4 Allocator | expected-value allocation under capacity | **+72.5% recovered value vs risk-ranking, half the contacts** |
| 5 Borrower state | capacity x willingness, uncertainty output | 6/6 archetypes; 98.3% route to a diagnostic question |
| 6 Conversations | conditioned generation, PTP extractor | extractor **93.4%** on gold; loop closes, no drops |
| 7 Coach Lens | two-tier hints, playbook, checklist | tier-1 0.04ms, tier-2 demotes at 4.5s |
| 8 Evals | LLM judge, Krippendorff alpha, drift | judge **91.7%** agreement, under reliability ceiling |
| 0 Spike (VAD half) | latency budget from real call audio | **300ms**, measured from 328 real turn gaps |
| 9 Agent Desk | deployed replay of a real scored call | live Artifact; hints fire, override, control arm |

70 tests pass (3 live-LLM checks opt-in). Nine clean commits.

---

## 2. The findings that matter

The code is the smaller half. These five results are the case for the product.

**Value-ranking beats risk-ranking by 72.5%, using fewer than half the contacts.**
Conventional collections sorts by probability of default and works the top. The
allocator maximises expected recovered value per agent-minute, Δ over self-cure,
weighted by exposure, under capacity. On the test queue it recovered 602M vs
349M for risk-ranking, with 2,962 contacts vs 6,172. Fewer conversations, more
money, because it skips the self-curers and the tiny-exposure accounts that
risk-ranking wastes minutes on. (Uplift is modelled, not measured, see limits.)

**Self-cure is the most valuable thing the Risk Lens does, and it needs a "do
not contact" action.** 72% of delinquent accounts cure with no contact. Calling
them costs money and annoys people who were about to pay. Making "do not contact"
a first-class scored action, not the absence of one, is where a large slice of the
efficiency comes from.

**Borrower state is unknowable from servicing data alone, so the system asks.**
Capacity is estimable from trajectory and affordability. Willingness is not,
without a conversation. On real accounts, only 2% reach a confident quadrant; the
other 97.5% route to a diagnostic question rather than a guessed strategy. This is
not a weakness, it is why the product has two lenses. The Coach Lens's first job,
on nearly every account, is the question that separates cannot-pay from won't-pay.
Teaching an agent what to ask beats telling them what to say when the model does
not know.

**The two-tier hint design is forced by physics, not chosen.** Real call audio
gives a median inter-turn gap of 479ms. LLM composition takes 500-1500ms, it
cannot fit that gap. So deterministic hints (promise-quality, compliance) render
in under a millisecond and hit the live gap; LLM strategy hints are demoted to the
next pause. Measured, not asserted.

**Drift is measured, not assumed.** Self-cure rate moved from 0.59 to 0.52
across the backtest window, inside the monitor's 0.10 alert band. An earlier
build reported a rise from 0.60 to 0.72; that came from forward labels leaking
across loan boundaries, now fixed and tested (see `docs/defects.md`, D15). The
rate monitor recomputes the move on every build, because no model keeps its
calibration through a regime it never saw.

---

## 3. Is it ready for a live pilot?

**Recommendation: yes, as a shadow-then-limited pilot, not a full rollout.**

The pieces that must exist before touching real borrowers exist: a calibrated risk
model with reason codes, an allocator that provably beats the status quo in
simulation, a coaching layer that hits the latency budget, an experiment framework
that can prove or disprove value, and a decision log that records every score,
hint, and override.

**Stage 1, shadow (4-6 weeks).** Run the Risk Lens and Coach Lens alongside live
calls without showing anything to agents. Compare the queue it would have built to
the one that was worked; log what hints it would have fired. This validates the
models on real contact data and real ASR output before any agent sees a hint.

**Stage 2, limited live (8-12 weeks).** Turn on coaching for a randomised subset
of agents, with the permanent control arm the desk already implements. Watch the
guardrails, complaint rate, broken-promise rate, repeat-contact rate, as hard
stops. Measure recovery per agent-hour against control. This is the first honest
read on whether coaching moves money.

**Do not skip the control arm to move faster.** Without it the pilot cannot
distinguish the product working from the allocator selecting recoverable
borrowers. The arm is cheap; running blind is not.

---

## 4. What is still missing

Stated plainly, because a pilot plan that hides its gaps is worse than useless.

**Real conversation data linked to outcomes.** The single biggest gap. All
conversation work rests on synthetic data conditioned on real trajectories, which
validates the plumbing but cannot prove that conversation features improve
prediction (the generator's priors would leak into any measured lift). Only real
calls joined to real payment outcomes settle it. This is a pilot deliverable, not
a modelling one.

**L3 contactability.** Best-time, best-channel prediction needs contact-event
history, who was reached, when, on what channel, with what result. Freddie Mac
has none; the haessigDB calls and the sales transcript are conversations, not
outcome-linked outreach logs. L3 waits for pilot data.

**Measured uplift.** The allocator's 72.5% edge assumes an uplift shape from the
literature (effect concentrated in the persuadable middle). The shape is
defensible; the magnitude is not a promise. The randomised control arm is what
turns modelled uplift into measured uplift.

**Production ASR on telephony.** The 300ms budget was measured on one call with an
energy VAD. Real 8kHz telephony adds 8-12% WER; a hosted streaming ASR or a
bandwidth-extension front end is likely needed. The audio layer is behind a
swappable interface for exactly this.

**Playbook grounded in real outcomes.** The strategy playbook is seeded from
practice with support count 0, every strategy is provisional until the outcome
loop promotes it. It gets real only once the pilot generates outcome-backed
support.

**A second labeller.** Every eval number rests on one person's gold labels. The
protocol buys consistency, not correctness; a blind spot in the rubric propagates
invisibly. A practitioner second-labelling the gold sets is the first quality
upgrade available.

---

## 5. The honest posture

Three things this project refused to fake, and would have been easy to:

- It does not claim conversation features beat tabular features. That needs real
  data; the code refuses to compute the number on synthetic records.
- It does not report recovery lift, PTP-kept lift, or override rate. Those need a
  pilot; they are marked pending, not estimated.
- It does not keep a published number once the code behind it is found wrong.
  The label-window fix (D15) moved every headline figure, and they moved in the open.

The measure of the work is not that every number is green. It is that every number
is one you could stake a lending decision on, and where a number can't yet be
earned honestly, the system says so and shows what it would take.
