# Executive Briefing
## AI-Enabled Hurricane Risk Prioritisation for SGW's Electric Grid
**Prepared for:** SGW Senior Leadership & Decision-Makers
**Author:** Clara Crommen

---

## 1. Strategic Business Value

SGW's electric grid, substations and transmission lines serving over 8 million residents, sits directly in the path of an increasingly costly problem: hurricanes cause outages, outages cost money and customer goodwill, and today SGW has no reliable way to know, ahead of a storm, which specific assets are most likely to fail. Crew staging and preemptive action happen reactively, based on experience rather than evidence, because the data that would support a proactive decision (GIS records, storm forecasts, maintenance history) is scattered across systems that don't talk to each other.

The proposal here is a decision-support tool that closes that gap. In the 24 to 72 hours before a hurricane makes landfall, it produces a single, ranked view of which grid assets are at highest risk, so planners can decide where to pre-stage crews and what to preemptively de-energise before the storm hits, not after.

This is a genuinely proactive capability, not another dashboard. It directly supports three things SGW's leadership already cares about: fewer and shorter outages, a stronger position with regulators on climate resilience and emergency preparedness, and a more defensible story to insurers about how SGW manages storm risk. It's also built on techniques (predictive risk modelling and resource-allocation optimisation) that are well established in utility operations elsewhere, not experimental technology.

---

## 2. Financial Implications & ROI

SGW doesn't yet have data in our hands to produce a firm return figure, so what follows is an illustrative model: the assumptions are stated plainly, and the real numbers should be revisited once SGW's actual outage history and cost data are available. Even so, the shape of the value is worth walking through.

**Illustrative calculation, per significant storm event:**

| Input | Assumption | Source of assumption |
|---|---|---|
| Customers affected | 300,000 | A moderate-to-significant hurricane hitting a portion of SGW's 8M-customer territory |
| Average outage duration | 30 hours | Typical for a major grid-impacting storm, absent better prioritisation |
| Resulting customer-outage-hours | 9,000,000 | 300,000 × 30 |
| Reduction from better prioritisation | 15% | Conservative estimate of the effect of getting crews and preemptive action to the right assets sooner |
| Customer-outage-hours avoided | 1,350,000 | 9,000,000 × 15% |
| Benchmark cost per customer-outage-hour avoided | $10 | Rough midpoint drawn from published utility outage-cost studies; varies significantly by customer mix (residential vs. commercial vs. critical facilities) |
| **Estimated avoided cost, per event** | **≈ $13.5 million** | 1,350,000 × $10 |

Over a typical hurricane season with several storms affecting the territory to varying degrees, this points towards a meaningful multi-million-dollar avoided-cost range per year, even before accounting for two harder-to-quantify but real benefits: a stronger resilience record to present to insurers (with potential premium relief over time) and reduced regulatory exposure from demonstrating a proactive, data-driven emergency-preparedness process.

**Cost side:** a precise build cost needs a short scoping exercise, but the main cost categories are predictable: initial model development and validation against SGW's historical data, integration work to connect existing GIS, weather, and maintenance systems (read-only, so no changes required to those systems themselves), and ongoing model maintenance as new storm and outage data comes in. None of this requires new infrastructure investment on SGW's side beyond what a modern utility already runs.

---

## 3. Delivery Roadmap

| Phase | Timing | What happens |
|---|---|---|
| **Phase 1: Build & Validate** | Months 0 to 4 | Build the risk-scoring model against SGW's historical hurricane and outage data; pilot the dashboard with the planning team ahead of the next hurricane season. |
| **Phase 1: Live Operation** | One full hurricane season | Risk scoring runs live, informing planner decisions. This season is deliberately used to build an operational track record before anything further is automated. |
| **Phase 2: Crew Optimisation** | Following season | Add the crew-to-asset assignment recommendation on top of a now-proven risk model. |
| **Phase 3: Expansion** | Ongoing | Extend to other hazards (flooding, heatwave, wildfire) and other asset domains (water treatment, pumping stations), once the approach is proven on hurricanes and the electric grid. |

**Biggest dependency:** the quality and completeness of SGW's historical outage data. This is the one thing worth validating before committing to the Phase 1 timeline above, since it's the input the risk model depends on most, and a short discovery sprint to check it should happen first.

The phasing itself is deliberate, not just cautious. Phase 1 proves the highest-value, least-tested part of the system (a model informing decisions about critical infrastructure) before either automating further or expanding scope, so trust is earned in stages rather than assumed upfront.

---

## 4. Governance & Compliance

Two design choices here are aimed squarely at the fact that this system touches decisions about critical infrastructure:

- **Nothing acts on its own.** In this version, the system produces recommendations; a human planner or supervisor always reviews and approves before any crew is dispatched or line de-energised. This is the appropriate starting posture for AI with no operational track record yet, and it removes a whole category of "who's accountable if the AI got it wrong" concern from the outset.
- **Every recommendation is explainable.** Planners can see why an asset was flagged, not just that it was. That matters for day-to-day trust and adoption, and it matters just as much if a decision ever needs to be defended in a post-storm regulatory review.

On top of that, asset and location data is treated as sensitive critical-infrastructure information with role-based access control, and every recommendation, along with any human approval or rejection, is logged, supporting both compliance reporting and future validation of the model against real outcomes. As the model earns a track record, there's a credible future path towards allowing high-confidence, low-stakes recommendations to apply automatically; that's intentionally not part of this first version.

---

## 5. Scalability

The approach is built to extend rather than to be rebuilt. The architecture reads data from SGW's existing systems without modifying them, so onboarding a new data source, a new hazard, or a new asset type is an extension of the existing pipeline rather than a new project. Once proven on hurricanes and the electric grid, the same underlying approach extends naturally to:

- **Other hazards:** flooding, heatwave, and wildfire risk, using the same probability-times-consequence framework with hazard-specific inputs.
- **Other asset domains:** water treatment facilities and pumping stations, which face similar prioritisation problems during severe weather.
- **Geographic expansion:** additional regions or service territories, should SGW's footprint grow.

Because Phase 1 deliberately proves the model on a single, well-understood hazard and asset type first, expansion in Phase 3 is a scope decision rather than a technical one; the underlying system is designed for it from day one.
