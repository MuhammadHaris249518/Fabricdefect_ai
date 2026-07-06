# Crumb Studio AI — KPI & Readiness Plan

**Scope:** Single-page synthetic defect generation MVP
**Split:** Two parallel workstreams — (A) UI + Backend + Roboflow annotation integration, and (B) AI model fine-tuning
**Purpose of this document:** Define how each workstream measures progress, what "done" means for each, and the exact gate at which the two streams combine into a shippable product.

---

## 1. Why two workstreams

The application has two independent halves that can be built and validated in parallel:

| | Workstream A — Application | Workstream B — Model |
|---|---|---|
| Owns | Single-page UI, upload flow, Roboflow-powered annotation, backend API, image comparison, download | Fine-tuning the masked-image-generation model on cookie/biscuit defect data |
| Can be considered "done" without the other? | Yes — using a stub/placeholder generation response | Yes — evaluated offline on held-out image sets, independent of the UI |
| Blocking dependency | None (Roboflow handles annotation independently of model readiness) | None (training data doesn't require the finished UI) |
| Final step | Swap the stub generation call for the real fine-tuned model endpoint | Hand off a served model endpoint matching the agreed request/response contract |

This means Workstream A can be marked **feature-complete and demo-ready** while Workstream B is still fine-tuning — the only remaining task at that point is swapping one API call.

---

## 2. Workstream A — UI + Backend + Roboflow (this team's deliverable)

### 2.1 Functional KPIs (Definition of Ready)

Each KPI below is independently testable and independently sign-off-able, so partial progress is visible instead of one large "UI done / not done" checkbox.

---

**KPI 1 — Main Page Shell Ready**
- *Description:* The single-page application loads with the full layout in place: header/branding, upload panel, annotation area, prompt box, generate button, progress indicator, and comparison/download area — even before any image is uploaded (empty states shown correctly).
- *Acceptance criteria:*
  - [ ] Page loads with no console errors
  - [ ] All panels render in their empty/placeholder state
  - [ ] Layout holds on desktop and down to 375px width
  - [ ] No routing/navigation exists outside this one page
- *Target:* 100% of the layout present and stable before any backend integration begins
- *Status metric:* Visual QA sign-off

---

**KPI 2 — Backend: Image Upload & Acceptance**
- *Description:* The backend exposes an endpoint that accepts an uploaded image, validates it, and stores it for the session/generation pipeline.
- *Acceptance criteria:*
  - [ ] Accepts JPG/PNG only; rejects other formats with a clear error
  - [ ] Enforces a 10MB size limit with a clear error on oversized files
  - [ ] Returns a stable image reference/ID the frontend can use in later calls (annotation, generate)
  - [ ] Stores the original file (object storage or equivalent) without modification
- *Target:* 100% pass rate on valid-file tests; 100% correct rejection on invalid-file tests
- *Status metric:* Automated upload test suite (valid + invalid cases)

---

**KPI 3 — Database Connection & Session Record**
- *Description:* The backend is connected to the database and persists a minimal record per upload/generation session, even though there's no history UI in the MVP.
- *Acceptance criteria:*
  - [ ] Backend establishes a database connection on startup with a health check
  - [ ] A record is created per upload (image reference, timestamp)
  - [ ] A record is updated per generation request (prompt, mask reference, status, timestamp)
  - [ ] Connection failures are logged and surfaced as a backend health-check failure, not a silent error
- *Target:* Database health check green; one row per upload and per generation verified in test runs
- *Status metric:* Health-check endpoint + manual row inspection after test runs

---

**KPI 4 — Frontend: Image Upload UI**
- *Description:* The upload panel on the main page lets a user select or drag-and-drop an image and see upload confirmation.
- *Acceptance criteria:*
  - [ ] Click-to-browse and drag-and-drop both work
  - [ ] Thumbnail, filename, and file size shown after upload
  - [ ] Clear error message shown on rejected files (wrong type/too large), matching KPI 2's rules
  - [ ] User can remove/replace the image before proceeding
- *Target:* Pass on all upload UI test cases
- *Status metric:* Manual QA pass

---

**KPI 5 — Roboflow Annotation Interface: Embedded & Ready**
- *Description:* Once an image is uploaded, the Roboflow annotation interface loads inline on the same page (no redirect, no new tab) with that image ready to annotate.
- *Acceptance criteria:*
  - [ ] Roboflow panel loads within 3 seconds of upload completing
  - [ ] The correct uploaded image is the one loaded into Roboflow
  - [ ] Annotation tools (brush/polygon, whichever Roboflow exposes) are usable inline
  - [ ] No separate authentication step interrupts the flow for the end user
- *Target:* ≥ 99% successful load rate in testing
- *Status metric:* Load-success test log

---

**KPI 6 — Roboflow Mask Retrieval (Annotation Ready)**
- *Description:* An annotation made in Roboflow can be retrieved via the Roboflow API as a usable mask and handed to the backend generation pipeline.
- *Acceptance criteria:*
  - [ ] Mask is retrievable immediately after the user finishes annotating
  - [ ] Mask format (polygon or raster) is documented and consistent
  - [ ] Mask correctly corresponds to the region the user drew (spot-checked against source annotation)
  - [ ] Backend can consume the mask format without additional conversion errors
- *Target:* 100% of test annotations produce a valid, usable mask
- *Status metric:* Mask validation test suite

---

**KPI 7 — Annotation Editing (Edit / Clear / Reset)**
- *Description:* Before generating, the user can adjust their annotation without re-uploading the image.
- *Acceptance criteria:*
  - [ ] Edit: user can modify an existing annotation
  - [ ] Clear: user can remove the current annotation and redraw
  - [ ] Reset: user can return to a blank annotation state on the same image
  - [ ] None of these actions require a re-upload or full page reload
- *Target:* All three actions work without state loss elsewhere on the page (prompt text, etc.)
- *Status metric:* Manual QA pass

---

**KPI 8 — Prompt Input**
- *Description:* A text field where the user describes the desired defect, feeding directly into the generation call.
- *Acceptance criteria:*
  - [ ] Field validates non-empty input before allowing Generate
  - [ ] Character limit is enforced and visible
  - [ ] All six reference prompts (burned, cracked, moldy, chocolate chips, underbaked, broken edge) submit successfully end-to-end
  - [ ] Custom free-text prompts are equally accepted (not restricted to the six examples)
- *Target:* 100% of reference prompts + sample custom prompts submit without error
- *Status metric:* Prompt submission test log

---

**KPI 9 — Backend: Generate Endpoint & Contract**
- *Description:* The backend exposes a generation endpoint accepting `{image_reference, roboflow_mask, prompt}` and returns a response in the agreed shape — against a stubbed model response until Workstream B is ready.
- *Acceptance criteria:*
  - [ ] Endpoint accepts the full payload and returns a syntactically valid response every time
  - [ ] Response shape matches what Workstream B has agreed to return (so swapping the stub for the real model requires no frontend change)
  - [ ] Errors (bad mask, missing prompt, backend/model failure) return structured error responses, not raw exceptions
  - [ ] Database record from KPI 3 is updated with the generation result/status
- *Target:* API contract test suite passes 100%
- *Status metric:* Automated contract tests

---

**KPI 10 — Progress Indicator**
- *Description:* A visible loading state runs from the moment Generate is clicked until a result or error is returned.
- *Acceptance criteria:*
  - [ ] Indicator appears immediately on click, no dead pause
  - [ ] Indicator reflects real backend state where possible (not a fixed fake timer only)
  - [ ] Generate button is disabled/locked during generation to prevent duplicate submissions
  - [ ] Indicator resolves correctly on both success and failure
- *Target:* 0 reports of a stuck or silent state during QA
- *Status metric:* Manual QA + fault-injection test

---

**KPI 11 — Generated Image Preview**
- *Description:* The generated image is displayed on the page as soon as the backend returns it.
- *Acceptance criteria:*
  - [ ] Image renders correctly at full quality
  - [ ] A visible "AI Generated" indicator/tag distinguishes it from the original
  - [ ] Broken/failed generations show a clear placeholder, not a broken image icon
- *Target:* 100% correct render on successful generations
- *Status metric:* Manual QA pass

---

**KPI 12 — Original vs. Generated Comparison**
- *Description:* The original and generated images are viewable together for direct comparison.
- *Acceptance criteria:*
  - [ ] Side-by-side layout on desktop; stacked layout on narrow/mobile widths
  - [ ] Both images load at consistent scale for fair comparison
  - [ ] Independent zoom/pan (if implemented) doesn't break alignment between the two
- *Target:* Visual QA pass on desktop and mobile breakpoints
- *Status metric:* Manual QA pass

---

**KPI 13 — Download Generated Image**
- *Description:* The user can download the generated result as a high-quality file.
- *Acceptance criteria:*
  - [ ] Download produces a PNG matching the on-screen result exactly
  - [ ] File name is meaningful (not a random hash only)
  - [ ] Download works on the latest Chrome, Edge, Safari, and Firefox
- *Target:* 100% match between downloaded file and displayed result across all test browsers
- *Status metric:* Manual download-and-compare test

---

**KPI 14 — Error Handling & State Preservation**
- *Description:* If any step fails (upload, annotation retrieval, generation), the user sees a clear error and doesn't lose their progress.
- *Acceptance criteria:*
  - [ ] Failed generation preserves the uploaded image, the annotation, and the prompt text
  - [ ] Error messages are specific enough to act on (not a generic "something went wrong" with no next step)
  - [ ] User can retry without restarting the whole flow
- *Target:* 0 data-loss incidents during fault-injection testing
- *Status metric:* Manual fault-injection test



### 2.2 Non-functional KPIs

| KPI | Target |
|---|---|
| Time to first interactive (page load) | < 2.5s on a standard broadband connection |
| Roboflow annotation panel load time | < 3s after image upload |
| UI responsiveness during generation wait | No blocked interactions; cancel/reset remains usable |
| Cross-browser support | Latest Chrome, Edge, Safari, Firefox |
| Mobile layout | Usable (not necessarily annotation-optimized) down to 375px width |

### 2.3 Definition of "Ready" for Workstream A

Workstream A is marked **ready** when:
- [ ] All Functional KPIs in 2.1 pass
- [ ] All Non-functional KPIs in 2.2 are met
- [ ] The `/api/generate` endpoint is fully built against a **stubbed** model response matching the real model's expected output shape (image bytes/URL + metadata)
- [ ] The Roboflow mask export format is confirmed and documented for Workstream B to consume
- [ ] A short handoff note exists describing exactly where in the code the stub call is replaced by the live model endpoint

At this point, **the UI and backend are ready** — the only remaining integration work is pointing the existing `/api/generate` call at Workstream B's served model instead of the stub.

---

## 3. Workstream B — Model Fine-Tuning (Team B's deliverable)

### 3.1 KPIs

| KPI | Target |
|---|---|
| Mask fidelity | Generated edits stay within the provided Roboflow mask boundary in ≥ 95% of evaluation samples |
| Background preservation | Pixels outside the mask remain unchanged (PSNR/SSIM above an agreed threshold vs. the source image) |
| Prompt adherence | Generated defect visually matches the prompt category (burned / cracked / moldy / chocolate chips / underbaked / broken edge) in ≥ 90% of human-reviewed samples |
| Realism | Blind human review rates the generated region as realistic (not obviously synthetic) in ≥ 80% of samples |
| Inference latency | Single-image generation completes in an agreed target (e.g. < 8s) suitable for the UI's progress indicator |
| API contract compliance | Served model endpoint accepts `{image, roboflow_mask, prompt}` and returns the agreed response shape without modification needed on the frontend/backend side |

### 3.2 Definition of "Ready" for Workstream B

Workstream B is marked **ready** when:
- [ ] All KPIs in 3.1 are met on the held-out evaluation set
- [ ] The model is served behind an endpoint matching the contract Workstream A already built against
- [ ] A sample batch of real Roboflow-exported masks (from Workstream A) has been tested successfully

---

## 4. Integration Gate

```
Workstream A (UI + Backend + Roboflow)  ─────►  READY  ──┐
                                                            ├──► Swap stub → live model call ──► MVP SHIPPED
Workstream B (Model fine-tuning)         ─────►  READY  ──┘
```

- If **A is ready before B**: ship the app in demo mode against the stub, clearly labeled as using placeholder generation, so stakeholders can review the full flow (upload → Roboflow annotate → prompt → compare → download) immediately.
- If **B is ready before A**: validate the model against real Roboflow-exported masks as soon as they're available, ahead of full UI completion.
- **MVP is considered shipped** only once both are ready and the stub call has been replaced by the live model endpoint, with one end-to-end smoke test run (upload → Roboflow annotation → prompt → generate → compare → download) passing against the real model.

---

## 5. Reporting Cadence

| Cadence | What's reported |
|---|---|
| Weekly | KPI checklist status (2.1 / 2.2 / 3.1) per workstream, blockers, ETA to "Ready" |
| At each "Ready" declaration | Full checklist evidence (screenshots/recordings for A, evaluation report for B) |
| At Integration Gate | Joint smoke-test result and go/no-go for ship |
