# “How to Trust a Liar” — Talk Planning Notes

> A living outline capturing discussion threads and options for upcoming conference presentations about MCP Commit Story.  Keep language concrete and avoid corporate buzzwords.

---

## 1. Context

- **Project**: MCP Commit Story — automated engineering journal powered by Git data, Cursor chat logs, and AI section generators.
- **Initial Architecture**: MCP server + AI agents triggered by git hooks (proved impossible).
- **Current Architecture**: Background process (event-driven) that spawns fresh AI calls after each commit.
- **Core Pain Point**: AI supplied confident but wrong guidance → required architectural pivot (see *“Building a Castle on Unstable Ground”* blog post).
- **Observability**: Comprehensive OpenTelemetry spans wrap each `invoke_ai()` call and major pipeline steps (git-hook trigger, diff collection, file write).

---

## 2. Key Lessons

1. **AI Confidence ≠ AI Accuracy** — validate every assumption.
2. **Observability for Fuzzy Execution** — traces can reveal cost, latency, and silent content failures even when AI work lives in a single span.
3. **Pivot Early, Document Everything** — crisis stories become assets for teaching and tooling demos.

---

## 3. Talk Title (Locked-in)

- **“How to Trust a Liar: Instrumenting AI Execution with OpenTelemetry”**

---

## 4. Presentation Shapes

### 4.1 Single-Talk Strategy

| Aspect | Details |
| --- | --- |
| Audience | Keynote & breakout reuse |
| Focus | Deep dive into instrumentation of AI pipeline |
| Pros | One deck to maintain; heavy cloud-native tooling content |
| Cons | Risk of losing non-practitioners during detail sections |

### 4.2 Two-Talk Strategy *(Recommended in discussion)*

| Slot | Title / Angle | Ratio (Story : Tech) | Notes |
| --- | --- | --- | --- |
| Keynote | “How to Trust a Liar: Lessons from Rebuilding an AI-Powered System” | 70 : 30 | Narrative arc (castle-on-sand crisis → recovery) + one polished trace demo |
| Breakout | “How to Trust a Liar — Deep Dive: OpenTelemetry Patterns for AI Pipelines” | 20 : 80 | Span design, cost & latency tags, FinOps dashboards, validation alerts |

### 4.3 Narrative-Only Strategy

- Keynote (and any slot) focuses on emotional journey with light tooling cameo.
- Pros: universally digestible; minimal prep.
- Cons: Technical crowd may feel underserved.

---

## 5. Possible Otel Angles (for demos)

1. **Cost & Latency Governance**
   - Custom span attrs: `prompt_tokens`, `completion_tokens`, `usd_cost`, `latency_ms`, `retry_count`.
   - Dashboard: cost per section generator, P95 latency, error heat-map.
2. **Semantic Failure Detection**
   - Tag `valid_output` on spans; alert when false > x %.
   - Shows mismatch between 200 OK and “content is junk.”
3. **Pivot Feedback Loop**
   - Use trace to demonstrate how observability shortened iteration cycles after the architecture change.

---

## 6. Open Questions

- Which conference slots will be offered (keynote only vs keynote + breakout)?
- How quickly can Datadog dashboards be demo-ready?
- Do we want to engineer a “bad prompt” example for the semantic-failure story?

---