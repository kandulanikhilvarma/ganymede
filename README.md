<div align="center">

# 🌘 Ganymede

### Recovery Intelligence for lending, receivables, and investor-funded credit books

**Predict the wobble. Shape the call. Keep the book.**

### [→ ganymede-kandula.vercel.app](https://ganymede-kandula.vercel.app)

[![License: MIT](https://img.shields.io/badge/License-MIT-0e8f80.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-3572A5.svg)
[![ci](https://github.com/kandulanikhilvarma/ganymede/actions/workflows/ci.yml/badge.svg)](https://github.com/kandulanikhilvarma/ganymede/actions/workflows/ci.yml)
![Invariants](https://img.shields.io/badge/design%20invariants-I1--I14-c07f1c.svg)

![Ganymede. Predict the wobble, shape the call, keep the book.](site/assets/img/og.png)

</div>

---

## What it is

One system, two lenses over the **same decision**.

- **Risk Lens.** Who to contact, when, and what to offer. It answers *where does an agent-minute earn the most*.
- **Coach Lens.** What to say once the conversation starts. It answers *how does this call end in money*.

They are one product because they close a single loop. Risk picks the conversation, Coach shapes it, and the outcome of that conversation is the label that retrains both. Split them and each half degrades into something worse: a queue nobody knows how to work, or advice with no idea who it is talking to.

---

## Try it

Four things on the site respond to you rather than just describing themselves.

| | What to do | What it shows |
|---|---|---|
| [**Allocator studio**](https://ganymede-kandula.vercel.app/queue?cap=5) | Drag the capacity slider | Both queues re-rank. Every position on that slider is a real allocator run, not an interpolation between two. The address follows the slider, so `?cap=5` links a scenario |
| [**Agent desk**](https://ganymede-kandula.vercel.app/desk) | Press play, then switch to the control arm | Hints firing at real turn boundaries, and the counterfactual with coaching switched off |
| [**Evidence**](https://ganymede-kandula.vercel.app/evidence) | Move the latency slider, then open "Show the numbers" | How many real turn boundaries a hint at that speed would actually fit inside, and the table behind every chart |
| [**Start here**](https://ganymede-kandula.vercel.app/) | Scroll the walkthrough | One borrower from trajectory bend to retrained model, in six decisions |

---

## The site

Everything below is explorable rather than only readable.

| | |
|---|---|
| [**Start here**](https://ganymede-kandula.vercel.app/) | The argument, and one borrower walked end to end |
| [**How it works**](https://ganymede-kandula.vercel.app/system) | Architecture, data lineage, and all fourteen invariants |
| [**Evidence**](https://ganymede-kandula.vercel.app/evidence) | Every chart with its method, and a drag-the-budget latency histogram |
| [**Allocator studio**](https://ganymede-kandula.vercel.app/queue) | Move the capacity slider; both queues re-rank on real runs |
| [**Agent desk**](https://ganymede-kandula.vercel.app/desk) | Work a real scored queue: hints, promise capture, override, control arm |
| [**The argument**](https://ganymede-kandula.vercel.app/case) | Why it recovers more per agent-minute, and how it reaches the floor |
| [**Glossary**](https://ganymede-kandula.vercel.app/glossary) | Arrears, self-cure, PTP, roll curve, uplift, defined where they are used |
| [**About**](https://ganymede-kandula.vercel.app/about) | Who built it, and why it is called Ganymede |

**No number on that site is typed by hand.** `scripts/build_site_data.py` regenerates `site/data/*.json` by calling the pipeline directly, and every value ships with the kind of evidence behind it: `measured`, `backtested`, `simulated`, `seeded`, or `pending`. A figure with no provenance cannot render at all, and CI fails if the committed JSON drifts from what the code now produces.

---

## The results that make the case

Backtested, simulated, or measured. No invented numbers.

### Value-ranking beats risk-ranking, and most where it matters

The allocator maximises **expected recovered value per agent-minute**: uplift over self-cure, weighted by exposure, under a capacity constraint. At 15% of full-coverage capacity it recovers **+72.5%** more than risk-ranking using roughly half the contacts. At 2% capacity the edge is **+240%**. At 60% it converges to **+4.1%**, because with enough agents to call everybody the ordering stops mattering.

![Allocator against risk-ranking: 72% more recovered value with under half the contacts](docs/img/allocator.png)


| Agent capacity | Allocator | Risk-ranking | Edge | Contacts used |
|---|---:|---:|---:|---|
| 2% | 106.2M | 31.2M | **+240.4%** | 395 vs 822 |
| 5% | 237.9M | 85.6M | **+177.9%** | 987 vs 2,057 |
| 15% | 602.3M | 349.2M | **+72.5%** | 2,962 vs 6,172 |
| 30% | 1.03B | 745.6M | **+38.8%** | 5,925 vs 12,344 |
| 60% | 1.68B | 1.61B | **+4.1%** | 11,850 vs 24,688 |

Two real rows carry the argument on their own.

| Account | Exposure | p(worsen) | Self-cure | Allocator funds it | Risk-ranking funds it |
|---|---:|---:|---:|---|---|
| `F25Q20015405` | €1,929,000 | 0.15 | 0.96 | at 54% capacity | **never** |
| `F24Q40000483` | €1,289 | 0.80 | 0.32 | **never** | at 11% capacity |

Risk-ranking sorts by probability, so it calls the €1,289 account early and never reaches the €1.93M one anywhere in the sweep. The minutes a contact costs are worth more than the whole uplift on the small account. [Move the slider yourself.](https://ganymede-kandula.vercel.app/queue)


### The risk score is calibrated, so the number means what it says

L1 predicts whether an account worsens over the next 90 days. A collections agent reads that number and acts on its face value, so calibration is the gate rather than AUC.

![L1 reliability curve, closely tracking the diagonal](docs/img/reliability.png)

### The two-tier hint design is forced by physics

Measured from **328 real inter-turn gaps** in a 10-minute call. The median gap is 479 ms and the enforced budget is 300 ms, which is the p25 of 292 ms rounded up. **75%** of real turn boundaries are wide enough for a hint at that budget, against only **48%** for a 500 ms model call. So deterministic hints render in under a millisecond and land live, while model-composed strategy hints wait for the next pause rather than racing the budget.

![Inter-turn gap histogram with the 300ms tier-1 budget and 479ms median marked](docs/img/gap_hist.png)

### Drift is measured, not assumed

Self-cure rate moved from 0.59 to 0.52 across the backtest window, inside the monitor's 0.10 alert band. An earlier build reported a rise from 0.60 to 0.72. That came from forward labels leaking across loan boundaries, now fixed and pinned by a test ([D15](docs/defects.md)). Every headline number on this page moved with that fix, and moved in the open.

![Self-cure rate across the time split, 0.59 to 0.52](docs/img/selfcure_drift.png)

---

## Architecture

**Where Ganymede acts.** Conventional collections enters at `Delinquent`. Ganymede enters one state earlier, and `Drifting → Current` with no contact is the transition most systems never notice they are being paid for.

```mermaid
stateDiagram-v2
    [*] --> Current
    Current --> Drifting: trajectory bends (L1)
    Drifting --> Current: self-cure (L2)
    Drifting --> Delinquent: payment missed
    Delinquent --> InTreatment: allocator selects, agent contacts
    InTreatment --> PromiseOpen: PTP captured (L4)
    PromiseOpen --> Cured: promise kept
    PromiseOpen --> Delinquent: promise broken
    Delinquent --> ChargedOff: options exhausted
    Cured --> [*]
    ChargedOff --> [*]
```

**System flow.** Servicing panel and contact events feed the models, the allocator turns scores into an assignment, the desk surfaces hints, and every decision is logged and resolved back into training.

```mermaid
flowchart TB
  PANEL["Borrower trajectory panel"] --> BS["Borrower state<br/>capacity x willingness"]
  CE["Contact events (voice, email, SMS)"] --> BS
  PANEL --> M1["L1 trajectory"]
  PANEL --> M2["L2 self-cure"]
  CE --> M4["L4 PTP-kept"]
  BS --> M4
  M1 --> ALLOC["Allocator<br/>expected value per agent-minute"]
  M2 --> ALLOC
  M4 --> ALLOC
  ALLOC --> ARM{"Experiment arm"}
  ARM -->|treatment| DESK["Agent desk"]
  ARM -->|control| DESK
  BS --> COACH["Coach Lens<br/>two-tier hints"]
  DESK --> COACH
  DESK --> LOG[("Decision log")]
  LOG --> OUT["Outcome resolver"]
  OUT --> M1
  OUT --> M4
  OUT --> DRIFT["Drift monitors"]
```

**One call, in order.** The latency numbers are the measured ones, not targets.

```mermaid
sequenceDiagram
    autonumber
    participant B as Borrower
    participant V as VAD
    participant C as Coach Lens
    participant A as Agent
    participant L as Decision log
    B->>V: speaks, then stops
    V->>C: turn boundary, pause of 200 ms or more
    C->>A: tier-1 hint in under 1 ms, lands inside the gap
    Note over C,A: tier-2 needs 500 to 1500 ms,<br/>so it waits for the next pause
    A->>B: asks the question that separates cannot-pay from will-not-pay
    B->>A: commits to an amount, a date, a method
    A->>L: promise captured, with experiment arm and propensity
    L->>L: resolve against what actually arrived
    L-->>C: kept or broken, and both lenses retrain on it
```


---

## How a number earns its badge

Every figure the site renders passes through this, and one with no answer cannot render at all.

```mermaid
flowchart TD
  Q{"Where did this number come from?"}
  Q -->|"observed directly in real data"| M["measured"]
  Q -->|"real data, held-out time split"| B["backtested"]
  Q -->|"real data plus a modelled assumption"| S["simulated"]
  Q -->|"practice, with zero outcome support"| SE["seeded"]
  Q -->|"needs live data to earn"| P["pending, deliberately not estimated"]
```

Of the eighteen headline figures: **9 measured**, **3 backtested**, **2 simulated**, **4 pending**.

<details>
<summary><b>The four it refuses to estimate</b></summary>

<br>

| Figure | Why it is not reported |
|---|---|
| Recovery lift in production | Cannot be estimated from simulation. The control arm measures it or nobody does |
| Agent override rate | Needs agents using the system |
| PTP-kept lift from coaching | Needs the randomised slice running |
| Conversation features beating tabular | Blocked by invariant I1. `evals/metrics.py` refuses to compute lift on synthetic records, because the generator's own priors would leak into the answer |

Each of these could have been estimated into something impressive. That is exactly why they are not.

</details>

---

## Design invariants

Fourteen failures found in review were converted from a postmortem list into **invariants enforced in code**. A defect is closed when something automated fails if it comes back, never before. A few:

| # | Invariant | Enforced by |
|---|---|---|
| I1 | Synthetic data never supports a predictive-lift claim | `evals/metrics.py` refuses lift on synthetic records |
| I2/I3 | Every decision carries an experiment arm and a propensity | non-optional in `schema.py`, retrain aborts if missing |
| I9 | Accounts ranked by expected value, never by probability | `allocator.py` is the only queue producer |
| I10 | "Do not contact" is a first-class scored action | in the `Action` enum, self-cure precision tracked |
| I13 | No timing feature from a source without calendar dates | `features.py` raises on a source tagged false |

<details>
<summary><b>All fourteen</b></summary>

<br>

| # | Invariant | Enforced by |
|---|---|---|
| I1 | Synthetic conversations never support a predictive-lift claim | `evals/metrics.py` refuses lift on any set containing a synthetic record |
| I2 | Every conversation carries an experiment arm, assigned before it starts | `arm` is non-nullable in `schema.py`, and the check fails if a later edit makes it optional |
| I3 | Every decision logs the acting policy and its propensity | Non-nullable `propensity`, and the retrain aborts if any row in the window lacks one |
| I4 | The latency budget is measured, never chosen | Lives in `config.py`, sourced from the gap distribution. Reading it before it is set fails loudly |
| I5 | No strategy is promoted below minimum support, and every hint shows its count | `playbook.py` gates promotion, the renderer requires a support field |
| I6 | Nothing in the label path ships without a gold set and an accuracy bar | The PTP extractor was blocked from downstream use until it cleared 0.80 |
| I7 | Strategy branches on borrower state, never on risk score alone | `compose.py` requires a `BorrowerState`. Uncertain state yields a question, not a guess |
| I8 | `ContactEvent` is channel-agnostic, and nothing assumes voice | Schema-level, so email and SMS are not a rewrite |
| I9 | Accounts are ranked by expected value, never by probability | `allocator.py` is the only queue producer. No sort-by-score path exists |
| I10 | "Do not contact" is a first-class action with money attached | In the action enum with a value in the objective, self-cure precision tracked |
| I11 | Conversation outcome outranks hint usefulness, and hints are capped | Rate limiter in `compose.py`, `metrics.py` reports outcome first |
| I12 | Input, score and outcome distributions are monitored | `monitors/drift.py` computes PSI and rate drift, and every site build publishes the rate check with its alert flag |
| I13 | No timing feature from a dataset without calendar dates | `panel.py` tags each source, `features.py` raises on one tagged false |
| I14 | The riskiest open assumption is tested now, not later | Phase order reviewed at every gate. This is why the latency spike preceded the coaching layer |

</details>

[What each one actually caught →](https://ganymede-kandula.vercel.app/system)

---

## The interface is generated too

The same discipline runs through the front end, because a design system and a headline figure are both places a known defect can quietly return.

- **Colour is semantic, not decorative.** Ice is the system's own signal, ember carries the magnitude of a *prediction*, and green and red are spent only on realised outcomes. A probability never gets three colours, because that invents category boundaries the model never produced.
- **The ramps are generated in OKLCH** by `scripts/gen_palette.py`, which fails the build if any of fourteen named contrast pairs drops below its floor, or if the risk ramp stops darkening monotonically and therefore stops encoding magnitude.
- **The artwork is drawn from the data.** The hero backdrop is real borrower trajectories out of the panel. The moon is procedural, seeded, and coloured from tokens. There are no stock images and the site makes no third-party request at all.
- **Three typefaces, vendored.** Fraunces for the argument, Geist and Geist Mono for the readout, self-hosted by `scripts/fetch_fonts.py`, which also writes the preload tags so they cannot go stale when a family changes.

---

## Repository structure

<details>
<summary><b>The tree</b></summary>

<br>

```
ganymede/            the Python package
  schema.py          frozen contracts; invariants encoded in the types
  invariants.py      I1-I14 as runnable checks
  panel.py           Freddie Mac -> unified monthly borrower panel
  features.py        trajectory windows + cross-signal features
  risk.py            L1 trajectory + L2 self-cure, calibration, reason codes
  allocator.py       expected-value allocation, capacity sweep, frontier
  state.py           capacity x willingness classifier
  generate.py        conversations conditioned on real trajectories
  outcomes.py        promise <-> payment resolver
  llm.py             LLMEngine (OpenRouter), role-based model routing
  audio/             VAD + ASR interface
  coach/             playbook, hint composer, checklist, PTP extractor
  evals/             LLM judge, Krippendorff alpha, metric table
  monitors/          drift (PSI + rate)
site/                the deployed site: no framework, no bundler, no build step
  *.html             nine pages and a 404
  assets/            generated tokens, shared CSS, vendored fonts, the mark
  assets/js/         charts, provenance-resolved figures, procedural artwork
  data/              generated from the pipeline, never hand-edited
scripts/
  build_site_data.py pipeline -> site/data/*.json, with provenance
  gen_palette.py     OKLCH ramps -> tokens.css, with contrast gates
  fetch_fonts.py     vendors the typefaces and rewrites the preload tags
  make_og.py         the social card, drawn from real trajectories
  make_charts.py     the README figures
docs/                per-phase results, the written case, figures
tests/               invariant, component and site-integrity tests
```

</details>

---

## Quickstart

Python 3.11 or newer. From a clean clone:

```bash
pip install -e ".[dev,llm,charts,audio]"
```

Six gates, each passes or fails. CI runs all six on Python 3.11 and 3.13:

```bash
ruff check .                                  # lint
python -m ganymede.invariants     --check     # I1-I14
python -m pytest -q                           # unit, eval and site-integrity tests
python scripts/gen_palette.py     --check     # 37 contrast pairs + ramp monotonicity
python scripts/fetch_fonts.py     --check     # vendored faces + preload freshness
python scripts/build_site_data.py --check     # site figures against the pipeline
```

On a clean clone the last gate skips the stages whose inputs are not redistributed (the panel and the call audio) and says so.

And the pipeline itself, which needs the source data present:

```bash
python -m ganymede.panel     --verify    # data pipeline
python -m ganymede.risk      --backtest  # calibration beats base rate
python -m ganymede.allocator --simulate  # value-ranking beats risk-ranking
```

Serve the site locally with `python -m http.server 4173 --directory site`.

Copy `.env.example` to `.env` for the LLM paths. Nothing else reads it:

| Variable | Needed for | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | generation, coaching, judging | none; those paths raise without it |
| `GANYMEDE_LLM_BACKEND` | choosing the LLM client | `openrouter` (the only one) |
| `GANYMEDE_LIVE_LLM` | the three live-LLM tests, which cost API calls | unset, so they skip |

The audio, modelling, and site paths run without any of them.

---

## The argument, in short

**Shadow first, then a randomised slice, then the floor.** Everything needed before the system touches a real borrower already exists: a calibrated risk model with reason codes, an allocator that beats the status quo, a coaching layer inside the latency budget, an experiment framework that can prove or disprove value, and a decision log of every score, hint and override. The full write-up is at [`/case`](https://ganymede-kandula.vercel.app/case) and in [`docs/CASE.md`](docs/CASE.md).

Three things this project refuses to fake, all of which would have been easy. It does not claim conversation features beat tabular features, because the code will not compute that number on synthetic records. It does not report recovery lift, promise-kept lift or override rate, because those need live data and carry a pending badge rather than an estimate. It does not dress a regime-shift calibration miss as a pass, and it does not bury it either.

---

## Data and attribution

Code is **MIT** (see [LICENSE](LICENSE)). Data is **not redistributed** here. The repository references public datasets under their own terms:

- **Freddie Mac Single-Family Loan-Level**, the trajectory backbone with real dates and real delinquency transitions, used under Freddie Mac's data terms.
- **Home Credit Default Risk**, feature enrichment, under the dataset's Kaggle terms.

Model outputs are advisory, and every decision is logged with its experiment arm and propensity, which is what makes the system auditable after the fact.

---

<div align="center">

**Nikhilvarma Kandula**

[LinkedIn](https://www.linkedin.com/in/nikhilvarmakandula) ·
[Email](mailto:kandulanikhilvarma@gmail.com) ·
[kandula.studio](https://kandula.studio)

</div>
