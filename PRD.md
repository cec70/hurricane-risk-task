# Product Requirements Document
## AI-Enabled Hurricane Risk & Crew Coordination for SGW's Electric Grid
**Prepared for:** SGW Technical Delivery Team
**Author:** Clara Crommen

---

## 1. Problem Definition & Business Context

Southeastern Grid & Water (SGW) operates critical electric grid infrastructure (substations and transmission lines) serving over 8 million residents across coastal and inland regions exposed to hurricanes. In recent years the company has faced rising operational costs, more frequent service disruptions, growing insurance premiums, and mounting regulatory pressure around climate resilience and emergency preparedness.

At present, SGW has no systematic way to work out which specific grid assets are most likely to fail in the 24–72 hours before a hurricane makes landfall. The data needed to make that judgement (GIS asset records, storm forecasts, maintenance history, environmental conditions) sits in separate systems that don't talk to each other, so pre-storm decisions about crew staging and preemptive action end up being made reactively and under time pressure, without anyone having a consolidated view of where the risk actually sits.

The knock-on effect is fairly predictable: crews and preemptive resources get allocated by experience and instinct rather than evidence, restoration after a storm takes longer than it needs to, customers go without power for longer than necessary, and both regulators and insurers factor that disruption record against SGW.

This document proposes a system that pulls together SGW's existing data sources and produces a single, ranked, explainable view of which assets are at highest risk ahead of a named storm, giving planners something concrete to act on before landfall rather than after.

**Out of scope for this phase:** water infrastructure (pumping stations, treatment facilities) and non-hurricane hazards (flooding, heatwave, wildfire). These are real pain points for SGW too, but deferred to later phases (see Section 9) so the first version can be built and proven on one hazard and one asset domain rather than several at once.

---

## 2. Key Assumptions & Unknowns

The case brief is intentionally light on client detail, so the following assumptions fill the gaps. Each is stated explicitly so it can be revisited once real discovery with SGW happens.

| Assumption | Reasoning |
|---|---|
| SGW maintains a GIS asset registry with location, asset type, customers served, and criticality metadata (e.g. whether an asset feeds a hospital) per substation/transmission asset. | Named in the case as an existing, if siloed, system. |
| SGW maintains a maintenance/asset-management system recording asset age, inspection dates, and prior fault/outage history. | Also named directly in the case ("maintenance platforms"). |
| SGW has access to, or can subscribe to, a hurricane forecast feed providing storm track, category, wind field, and storm-surge projections, refreshed roughly every six hours, matching the real-world NHC advisory cadence. | Named in the case ("weather feeds"). |
| Environmental GIS layers (vegetation/tree-cover density, flood-zone designation) exist internally or can be sourced from public or commercial GIS providers. | Reasonable for a utility already running GIS systems, though treated as a lower-confidence assumption than the three above. |
| There is enough historical outage data (past asset failures tagged to a specific storm event) to train and validate a supervised risk model. | This is the biggest unknown in the whole plan. If SGW's history turns out to be too sparse, inconsistent, or not recorded at asset level, the model would need to launch as a simpler, rule-augmented baseline until enough labelled history builds up. Flagging this now rather than assuming it away. |
| No real-time IoT or sensor telemetry currently exists on individual grid assets. | Not mentioned anywhere in the case, so assumed absent. If it did exist it would meaningfully improve the model, noted as a future enhancement in Section 9. |
| Crew location, base assignment, and availability status can be read from SGW's existing workforce-management tooling. | A reasonable assumption for any utility coordinating field crews; treated as read access only. |
| Asset and location data counts as sensitive, critical-infrastructure information, so needs access control rather than broad internal visibility. | Standard posture for this kind of data; addressed further in Section 8. |

---

## 3. Target Users & Pain Points

| User | Role in the workflow | Pain point today |
|---|---|---|
| **Grid Operations / Emergency Preparedness Planners** (primary) | Review the ranked risk list 24–72h before landfall and decide on crew pre-staging, candidates for preemptive de-energisation, and mutual-aid requests. | No single, prioritised view of asset risk; they currently have to cross-reference GIS, forecast, and maintenance data by hand, under time pressure. |
| **Field Crew Supervisors** (secondary) | Act on a crew-to-asset assignment recommendation derived from the risk ranking. | Have to work out where to send a limited number of crews with no clear, data-backed prioritisation coming from operations. |

Executive and leadership stakeholders are addressed separately in the Executive Management Briefing (Deliverable 2). This document is written for the technical delivery team building for the two operational users above.

---

## 4. Functional & Non-Functional Requirements

### Functional Requirements

- Ingest, on a scheduled basis, four data sources: hurricane forecast data, the GIS asset registry, maintenance/outage history, and environmental (vegetation/flood-zone) layers.
- Compute a **probability-of-failure** score for each grid asset using a trained model (see Section 5).
- Compute a **consequence** score per asset, calculated as customers served multiplied by a criticality factor.
- Multiply the two together to get a **composite risk score**, and rank all in-scope assets by it.
- Show planners the ranked list along with per-asset explainability (e.g. "high wind exposure, overdue maintenance, dense vegetation nearby") so the score isn't a black box.
- For the top-N highest-risk assets, generate a **crew-to-asset assignment recommendation** using current crew availability and location, via a constrained optimisation step.
- Require a human to review and approve a recommendation before it counts as actioned. Nothing is automatically dispatched or de-energised in this version (see Section 8).
- Recompute risk scores and assignment recommendations automatically whenever a new storm advisory comes in (roughly every six hours), with a manual refresh option for planners who want an update sooner.

### Non-Functional Requirements

- **Availability:** the system needs to stay up during active named-storm windows: precisely when it's needed most, and the worst possible time for it to go down.
- **Performance:** a full portfolio recompute should finish comfortably inside the six-hour refresh window, so it never lags behind the latest forecast.
- **Explainability:** every score needs to be traceable back to the factors that produced it. This underpins the human-in-the-loop model in Section 8; planners won't trust, and shouldn't trust, a number they can't interrogate.
- **Security:** role-based access control on asset location and criticality data, given its sensitivity as critical-infrastructure information (Section 8).
- **Auditability:** every recommendation generated, along with any human approval or rejection of it, gets logged, both to support regulatory review and to validate the model against real outcomes over time.

---

## 5. Proposed AI Capabilities

Two AI techniques sit behind this solution, each chosen for the specific problem it solves rather than as a general-purpose choice:

1. **Predictive ML (gradient-boosted trees)** for the probability-of-failure model. Trained on historical storm and outage data, it predicts each asset's probability of a storm-caused failure from three feature groups: weather/storm exposure (wind speed at the asset's location, storm-surge depth, distance from the forecast track), asset condition and history (age, time since last inspection, prior outages), and environmental proximity (vegetation density, flood-zone designation). Gradient-boosted trees were chosen over something simpler like logistic regression because the interesting signal here is usually in the interactions: high wind *combined with* dense vegetation *and* an overdue inspection is a different risk profile to any one of those alone, and that's exactly the kind of pattern a tree ensemble picks up naturally while still remaining fast to train and explainable through feature importance.
2. **Constrained optimisation** for crew-to-asset assignment. Once the highest-risk assets are identified, an assignment-problem solver (the Hungarian algorithm, for instance) matches available crews to those assets based on travel time/distance and availability, producing a recommended staging plan.

Deliberately absent from the core workflow: a large language model. The value here comes from prediction and optimisation, not conversation, so building an LLM in for its own sake would add complexity without adding much. A natural-language layer (turning the ranked list into a plain-English storm briefing, say) is a plausible future addition (Section 9) rather than something the MVP needs.

---

## 6. High-Level Architecture & Integrations

```
[GIS Asset Registry] ─┐
[Maintenance System]  ─┼─▶ [Data Ingestion Layer] ─▶ [Feature Pipeline] ─▶ [Risk Model
[Weather/Storm Feed]  ─┤      (read-only connectors)                        Service (GBT)]
[Environmental Layers] ┘                                                          │
                                                                                  ▼
[Crew/Workforce System] ─▶ (read-only) ──────────────────────────▶ [Optimisation  ◀── Ranked
                                                                     Service]         Risk List
                                                                          │
                                                                          ▼
                                                              [Planner & Supervisor
                                                               Dashboard]
                                                          (human review & approval)
```

Every connection into SGW's existing systems (GIS, weather feed, maintenance, crew/workforce) is **read-only**. The system doesn't write anything back into SGW's other tools; recommendations live in its own dashboard, and people act on them using whatever process they already use. That keeps the integration surface small, and it lines up with the recommend-only governance stance in Section 8: this system's job is to produce a recommendation worth trusting, not to carry out the action itself.

- **Risk Model Service** runs the trained gradient-boosted-trees model as a batch scoring job, triggered on the six-hour refresh cadence or on demand.
- **Optimisation Service** takes the top-N ranked assets plus current crew data and solves the assignment problem.
- **Dashboard** has two views: a planner view (ranked list, map, per-asset explainability) and a supervisor view (assignment recommendations), both built for human review, not autonomous action.

---

## 7. Data Requirements & Dependencies

| Source | Fields needed | Dependency risk |
|---|---|---|
| GIS Asset Registry | Asset ID, type, lat/long, customers served, criticality flag, install date | Low: fairly standard utility GIS data |
| Maintenance System | Asset ID, inspection dates, prior fault/outage records | Medium: depends on how complete and consistent the records are |
| Hurricane Forecast Feed | Storm track, category, wind field, storm-surge projection, advisory timestamp | Low: well-established data formats |
| Environmental Layers | Vegetation/tree-cover density, flood-zone designation, by location | Medium: may need sourcing externally if SGW doesn't already hold this |
| Crew/Workforce System | Crew ID, base location, availability status | Low–Medium: depends on how up to date SGW's crew data is kept |
| Historical Outage Data | Asset ID, storm event, whether and how the asset failed | **High: the single biggest dependency risk.** The model is only as good as the volume and quality of this history, and it needs validating early rather than assumed. |

---

## 8. Security, Governance & Human-in-the-Loop

The risk model and the optimiser both produce recommendations, not decisions. A named human (a planner for risk-driven calls, a supervisor for crew assignments) has to review and sign off before anything is acted on. Nothing in this version dispatches a crew or de-energises a line automatically. Given this system touches decisions about critical infrastructure and has no track record yet, that's the right level of caution to start with.

A few things support that human-in-the-loop model rather than just asserting it:

- **Explainability.** Every risk score comes with its top contributing factors, so a planner can sanity-check why an asset was flagged rather than taking a number on faith. That matters both for day-to-day adoption and for holding up under a post-storm regulatory review.
- **Access control.** Asset location and criticality data is treated as sensitive, so access is role-based (planners, supervisors, and administrators see different things) rather than broadly visible.
- **Audit trail.** Every recommendation, who saw it, and what was approved or rejected gets logged, supporting both compliance and future model validation against actual outcomes.

Longer term, once the model has an operational track record, a confidence-tiered approach could let high-confidence, low-stakes recommendations apply automatically while anything uncertain or high-impact still needs sign-off. That's deliberately not part of this version: introducing autonomy before the system has earned any trust would be the wrong order of operations for something touching critical infrastructure.

---

## 9. Success Metrics, MVP Scope & Delivery Priorities

**Primary success metric:** reduction in customer-outage-hours (customers affected multiplied by hours without power) during named storm events, measured against a pre-tool baseline. This is the metric that most directly reflects what the risk-scoring system actually delivers (better pre-positioning ahead of landfall), and it speaks to two of SGW's stated pain points at once: service disruptions and rising insurance premiums.

**Supporting metrics:**
- Model validation: precision/recall of the risk model's top-N predictions against historical outage labels.
- Adoption: the proportion of eligible planners actually using the ranked list ahead of a storm. An accurate model nobody looks at is still a failed rollout.

**Delivery roadmap:**

| Phase | Scope |
|---|---|
| **Phase 1 (MVP)** | Risk scoring only, for hurricanes and electric grid assets (substations and transmission lines). Read-only dashboard for planners. Human-in-the-loop throughout. |
| **Phase 2** | Add crew-to-asset assignment optimisation once Phase 1's risk scores have built up an operational track record. |
| **Phase 3+** | Extend to other hazards (flooding, heatwave, wildfire) and asset domains (water treatment, pumping stations); consider network-topology-aware consequence modelling (cascading downstream impact) and confidence-tiered autonomy. |

Phase 1 is scoped narrowly on purpose. It proves out the hardest and least-tested part of the system (a predictive model informing decisions about critical infrastructure) before layering automation on top of it or expanding into more hazards and asset types.
