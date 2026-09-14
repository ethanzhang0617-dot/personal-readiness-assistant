# Personal Readiness Assistant V1.0 — Final Patch QA Report

Release candidate: **Personal Readiness Assistant V1.0 — Portfolio Release**  
QA date: **2026-09-14**

## Delivery gate

| Check | Result | Evidence |
|---|---|---|
| Python Compilation | PASS | `python -m compileall -q .` completed with zero syntax errors |
| Pytest | PASS | 72 / 72 passed |
| Training Load Calendar Window | PASS | Exactly assessment date −7 through −1 versus −28 through −8 |
| Multiple Sessions Per Day | PASS | Completed same-date session loads sum into one daily total |
| Rest-day Handling | PASS | Covered dates without a completed session contribute 0 AU |
| Sparse Load History | PASS | Missing dates stay unknown; 28 covered dates required for the full comparison |
| Near-zero Load Guard | PASS | No division by zero or meaningless percentage is emitted |
| Unknown Exercise Fallback | PASS | Real log path maps actual sets once to explicit muscle/focus fallback |
| Mixed Known / Unknown Exercises | PASS | Both mapped and fallback sets contribute without duplication |
| Chat Autosave Contract | PASS | Completed local chat exchange immediately queues browser persistence |
| Chat Serialization | PASS | Profile-specific messages round-trip; durable history is capped at 30 |
| Full Body Core Mismatch | FIXED | Core removed because the current prescription has no Core mapping |
| Workout Candidate Mapping Audit | PASS | Every declared strength target is achievable from its prescription mappings |
| Readiness Regression | PASS | Threshold, baseline, domain, safety and independence tests |
| Recommendation Engine | PASS | Green / Amber / Red / STOP, split, recent work, Endurance and exposure tests |
| Alternative Workout Logging | PASS | Selected alternative produces its own exercises and sets |
| Workout Prescription Consistency | PASS | View and log both consume the same `WorkoutPrescription` |
| Decision Trace | PASS | Explicit named summaries; recent training is not positional list content |
| Local Soreness | PASS | Stored in dated check-in only and absent from persistent profile fields |
| IndexedDB Storage Bridge | NOT VERIFIED end-to-end | Bridge source and Python contract are present; browser automation was blocked by the environment's sensitive-data safeguard |
| Data Serialization | PASS | Versioned profile, check-in, assessment, session, recommendation and preference round trips |
| App Reload Persistence | NOT VERIFIED end-to-end | Requires a real permitted browser IndexedDB reload test |
| Export Backup | PASS | Valid versioned JSON export tested |
| Import Backup | PASS | Validation, rejection and replace round trip tested |
| Clear Local Data | PASS | Personal runtime data clears while demos remain isolated |
| Demo / Real Data Isolation | PASS | Demo profiles are never serialized; local Today never manufactures demo inputs |
| Science & Logic Page | PASS | AppTest page load and required-content checks |
| Science / Engine Rule Consistency | PASS | Science imports rule metadata directly from both engines |
| Reference Validation | PASS | All 12 listed PMID records and bibliographic metadata checked against PubMed/current primary records |
| Qwen Real Model Load / Generation | PASS | Real `Qwen/Qwen2.5-0.5B-Instruct` CPU load and five generations completed without an API key |
| Qwen User-facing General QA | PASS with guardrail fallback | Bad RIR draft rejected; verified definition displayed |
| Qwen User-facing Contextual QA | PASS with guardrail fallback | Weekly Back value accepted; unsafe/incomplete workout drafts rejected and deterministic context displayed |
| No-AI Fallback | PASS | Product remains usable with model disabled, unavailable or rejected |
| Streamlit Startup | PASS | Real server started on a local port |
| Seven-page AppTest | PASS | Today, Check-in, Trends, Coach, Profile, Science & Logic, About |
| Remote Personal Database | NONE | No remote personal-history persistence dependency or token found |
| Known Reproducible Bugs | NONE | Within the currently verifiable environment |

## Final patch bug fix log

### BUG 1 — Training Load used observations instead of calendar days

- **Root cause:** The domain removed null load values and sliced the final 7 and prior 21 numeric observations. A user training four times weekly could therefore have a “7-day” window spanning considerably more than seven dates.
- **Fix:** The assessment date now anchors a fixed 28-date calendar. Recent is date −7 through −1; reference is date −28 through −8. Rows are grouped by date, same-day completed loads are summed, and tracked no-session dates contribute 0 AU. Missing dates remain unknown and block the full comparison.
- **Regression tests:** Calendar boundaries, four-sessions-per-week pattern, same-day double session, rest-day zeros, sparse coverage, and near-zero reference tests.

### BUG 2 — Empty contribution map skipped unknown-exercise fallback

- **Root cause:** `{}` satisfies `isinstance(contributions, Mapping)`, so the previous code returned an all-zero result before reaching the focus fallback. A partially mapped mixed session could also omit its unknown exercise.
- **Fix:** Stored contributions are accepted only when they contain a valid positive contribution. New sessions calculate mapped and fallback contributions per actual exercise; an unknown exercise uses its explicit primary muscle, then a clearly mappable session focus. A session-level total is used at most once when exercise rows are absent.
- **Regression tests:** `Machine Chest Press` through `log_training_session()` produces 10 Chest sets; known Bench Press plus unknown Cable Fly produces 6 Chest sets; two 5-set unknown exercises produce 10, not 20.

### BUG 3 — Chat history did not immediately queue local persistence

- **Root cause:** The conversation list changed in runtime, but `_submit_question()` did not queue a browser save after appending the user and assistant messages.
- **Fix:** A completed local exchange now immediately calls the resilient chat-save queue. Serialization/save failures set a lightweight storage notice and never suppress the answer. Runtime and durable history are profile-specific and capped at the latest 30 messages.
- **Regression tests:** Source/bridge queue contract plus serialization → hydration round trip and 30-message cap.

### BUG 4 — Full Body Strength declared Core without Core exposure

- **Root cause:** The candidate declared every global muscle group even though Squat, Bench Press and Chest-Supported Row produce no Core contribution under the executable mapping.
- **Fix:** Core was removed from this candidate. Its declared targets are now Chest, Back, Shoulders, Arms, Quads, and Hamstrings / Glutes.
- **Regression tests:** Explicit Full Body Core test and an audit of every workout candidate against achievable prescription mappings.

### BUG 5 — Coach UI retained approved-result rewriter copy

- **Root cause:** UI text predated the context-aware Coach architecture.
- **Fix:** The page now says the Coach can explain readiness/recommendations, use relevant personal context, and answer general training/recovery questions while deterministic engines retain readiness and Primary authority. The chat prompt now invites readiness, training, recovery, RIR, volume, or workout questions.
- **Regression tests:** Copy assertions plus general RIR/chest-frequency and contextual leg-alternative answer checks.

## Bug fix log

### 1. Session-only history loss

- **Bug:** User mutations lived primarily in `st.session_state`, so a new session, restart or redeploy could lose them.
- **Root cause:** No persistent browser data layer existed.
- **Fix:** Added a versioned normalized local-data document, dependency-free Streamlit component bridge and IndexedDB object store. Session state is now the runtime cache.
- **Regression test:** Serialization, hydration, export/import, clear, profile isolation and bridge contract tests.

### 2. Demo values could become a local user's unsaved “today”

- **Bug:** A local profile without a saved check-in could still be assessed from scenario-generated draft values.
- **Root cause:** `current_assessment()` always consumed the UI draft used by Demo Mode.
- **Fix:** My Local Data now reads only a saved check-in matching today's date. Without one, readiness is explicitly insufficient. Scenario controls appear only for demo profiles.
- **Regression test:** `test_local_profile_never_receives_unsaved_demo_today_inputs`.

### 3. Local soreness behaved like a permanent profile field

- **Bug:** Soreness saved in Profile could carry forward indefinitely.
- **Root cause:** Legacy `profile["local_soreness"]` and Profile controls remained.
- **Fix:** Removed it from profile creation, update, demo seeds and Profile UI. It is now stored only in the dated daily check-in.
- **Regression test:** Date-specific soreness round trip and next-day non-carryover tests.

### 4. Alternative selection logged primary exercises

- **Bug:** Selecting `Shoulders + Arms` could leave `Back + Biceps` exercise defaults in the log.
- **Root cause:** Form defaults read `recommendation["primary"]["exercises"]` instead of the selected item.
- **Fix:** Added explicit `selected_workout` state and `prescription_log_defaults(selected)`.
- **Regression test:** Alternative exercise names and prescribed sets must equal the selected alternative and differ from Primary.

### 5. Displayed sets and logged sets could diverge

- **Bug:** Engine sets, template ranges and log totals were separately calculated.
- **Root cause:** No canonical prescription object.
- **Fix:** `WorkoutPrescription` now contains ID, demand, duration range, exact exercises, sets, reps and RIR. View and Log both read it.
- **Regression test:** Every displayed set count and log prescribed total is derived from the same object.

### 6. Prescribed work and actual work were conflated

- **Bug:** Weekly exposure could reflect a planned amount rather than completed work.
- **Root cause:** One generic working-set field served two meanings.
- **Fix:** Training sessions store `prescribed_sets` and `actual_sets` separately; muscle exposure uses actual exercise rows.
- **Regression test:** A 6-set prescription with 3 actual sets contributes 3, not 6.

### 7. Decision Trace positional indexing

- **Bug:** Recent Training could display a weekly-exposure factor.
- **Root cause:** `factors[-2]` assumed a list position that changed when optional factors were present.
- **Fix:** Added explicit goal, programme, weekly exposure, recent training, soreness, readiness, demand and recommendation summaries.
- **Regression test:** Legs yesterday at RPE 8 must render `Legs yesterday · high effort`.

### 8. PPL Push → Pull rotation was incorrectly penalized

- **Bug:** A Push session yesterday could make Legs beat Pull today.
- **Root cause:** Incidental Arms/Shoulders overlap was treated as a primary-region repeat.
- **Fix:** Rotation repeat checks use primary-region overlap; fractional secondary work still counts toward weekly exposure.
- **Regression test:** Push yesterday prefers Pull in a PPL programme.

### 9. Two sessions on one date overwrote daily load context

- **Bug:** The second session replaced the first session's mirrored daily load.
- **Root cause:** Daily readiness history stored only the latest session load.
- **Fix:** Unique session rows remain separate and the daily mirror aggregates completed same-day session loads.
- **Regression test:** Two same-day sessions keep distinct IDs and produce the summed daily load.

### 10. Editing a check-in could erase completed load

- **Bug:** A later same-date check-in containing null session fields could wipe the aggregated load.
- **Root cause:** Date upsert replaced the full daily row.
- **Fix:** Existing completed-session duration/load fields are retained when check-in values are null.
- **Regression test:** Same-date check-in update preserves the previously aggregated load.

### 11. Qwen behaved like a recommendation rewrite bot

- **Bug:** Every successful AI answer was prefixed with `Approved recommendation`, including general RIR questions.
- **Root cause:** Hard-coded prefix and a narrow “explain the approved result” prompt.
- **Fix:** Removed the prefix, changed the role to context-aware training coach, summarized relevant structured context and added factual validation for readiness, primary workout, RIR, weekly exposure and alternatives.
- **Regression test:** RIR contains no workout prefix; fixed personal facts are preserved; contradictions fall back.

### 12. Real Qwen produced unsafe or incorrect drafts

- **Bug:** In real QA the 0.5B model misdefined RIR and treated cardio as an unqualified replacement.
- **Root cause:** Small-model capability limits; generic contradiction detection was insufficient.
- **Fix:** Added intent-level validation. Invalid drafts are never shown as AI-enhanced answers; the verified rule-based answer is shown with a validation notice.
- **Regression test:** Incorrect RIR and alternative replacement drafts are rejected.

## Storage report

1. **Why previous data could disappear:** `st.session_state` is tied to an active Streamlit session and is not a durable browser database.
2. **How IndexedDB works now:** The custom component asynchronously loads/saves one versioned normalized state document in the current app origin's IndexedDB.
3. **Persisted data:** Local profiles, dated check-ins, readiness history, completed training sessions, deterministic recommendation history, browser preferences and an optional profile-specific chat history capped at the latest 30 messages.
4. **Role of `st.session_state`:** Fast active runtime cache and UI state; not the only persistent source of truth.
5. **After Streamlit restart:** The browser bridge requests the IndexedDB document and hydrates the Python runtime on the next browser session.
6. **Remote database:** None.
7. **Automatic GitHub writes:** None.
8. **Different browser:** No automatic restoration.
9. **Different device:** No automatic restoration.
10. **Clearing site data:** Can permanently remove the local history.
11. **Export Backup:** Produces a user-controlled `personal-readiness-backup.json` with schema version and all local collections.
12. **Import Backup:** Parses UTF-8 JSON, validates schema/collections/profile references/unique session IDs, then requires confirmation before replace.
13. **Schema version:** Current version is 1; unsupported newer documents are rejected safely so a future migration can be added deliberately.
14. **Demo isolation:** Ethan/Alex/Jessica are generated in runtime only and excluded from serialization/export. My Local Data never receives unsaved demo scenario values.

## AI architecture report

- Fixed answer residue was removed from both prompt and output assembly.
- AI receives profile goal/level/split; readiness and four domains; contributors; baseline confidence; Primary and Alternatives; Avoid Today; session demand; rationale; last 5–7 sessions; current 7-day exposure; targets; today's local soreness; and the last 6–10 chat messages.
- Long raw histories are not inserted.
- `What is RIR?` is answered directly and no hard-coded workout prefix is added.
- Weekly-set questions use the recorded exposure value; invalid model numbers are rejected.
- Alternatives remain explicitly labelled and cannot silently replace Primary.
- Readiness/recommendation engines do not depend on Qwen.

## Science & Logic report

The first-level page contains: system overview, inputs, personal baseline, four domains, exact overall logic, recommendation hierarchy, evidence-versus-heuristic table, example decision, limitations and linked references.

Evidence-supported principles include subjective wellness monitoring, session-RPE load, individual HRV trends, weekly training volume, frequency as programming distribution, autoregulation, proximity-to-failure context and HRV-guided endurance intensity modification. Product heuristics include exact Green/Amber/Red z-score and ratio thresholds, the overall domain-combination rule, index mapping, 1.0/0.5 operational set accounting and exact RIR/duration bands. None of these exact operating thresholds is presented as clinically validated.

Weekly volume is used because set volume is a meaningful programming variable, without claiming one universal optimum. Frequency organizes/distributes that work rather than acting as a recovery clock. Fractional sets estimate multi-joint contribution transparently; they are not exact physiology. Readiness primarily changes session demand so the product does not pretend an autonomic signal mechanically selects a muscle group. In Running-focused/Endurance contexts, autonomic status adjusts hard versus lower-intensity aerobic demand. Safety flags conservatively override normal training without making a diagnosis.

The product does not diagnose overtraining or medical fatigue, predict injury, estimate exact recovery percentages, guarantee optimal/safe training, claim certain HRV-to-performance prediction, or replace medical/coaching judgement.

## Verified references

All PMID links are listed on the Science & Logic page and were checked during release QA: **26423706, 28463642, 29163016, 27433992, 30558493, 41343037, 32813181, 33776802, 36334240, 38970765, 34489178, 34639599**.

## Free deployment audit

| Item | Result |
|---|---|
| Primary Frontend | Streamlit Community Cloud |
| Persistent Personal Data | Local browser IndexedDB |
| Remote Personal Database | NO |
| Supabase | NO |
| Firebase | NO |
| GitHub Data Persistence | NO |
| Commercial AI API | NO |
| AI Model | Qwen2.5-0.5B-Instruct |
| AI API Key | NO |
| User Backup | JSON Export / Import |
| Cross-device Sync | NO |

## Privacy audit

| Item | Result |
|---|---|
| Persistent readiness history | Local browser |
| Persistent training history | Local browser |
| Persistent local soreness | Local browser, dated check-in |
| Persistent profile | Local browser |
| Persistent remote personal database | None |
| Temporary application processing | Yes, as required for product functionality |
| Automatic remote backup | No |
| Automatic device sync | No |
| User-controlled export | Yes |
| User-controlled deletion | Yes |

## Honest verification boundary

Real browser IndexedDB save → close/reload → restore was **not verified in this environment** because the browser automation layer blocked localhost access to avoid exposing potentially sensitive readiness/training data. The JavaScript bridge, Python contract, normalized state, validation, serialization, import/export, clear and hydration behaviours were tested; a manual browser persistence check remains the deployment acceptance step.

## Final technical explanation

- **A — Load windows:** Recent mean uses assessment date −7 through −1; reference mean uses assessment date −28 through −8. These are exactly 7 and 21 complete calendar days.
- **B — Two sessions on one date:** Each completed session remains a unique session record. Its `duration × session_RPE` load is summed with other completed sessions on that date before the calendar comparison.
- **C — Rest days:** A covered date with no completed session contributes 0 AU. It remains in the denominator of the 7- or 21-day daily mean.
- **D — Sparse history:** Missing dates are unknown. Fewer than 14 covered dates is `INSUFFICIENT`; 14–27 is `LIMITED` coverage but still insufficient for the full comparison; all 28 are required to classify the load domain.
- **E — Near-zero reference:** Reference means below 1 AU return insufficient data with no z-score or percentage change.
- **F — Unknown exercise fallback:** Use an exercise/session explicit primary muscle when present, otherwise a clearly mappable `primary_focus`, otherwise a single declared muscle when unambiguous.
- **G — Empty map:** `{}` or a map without a valid positive contribution no longer triggers an early return; deterministic fallback executes.
- **H — Mixed exercises:** Known exercises use the mapping table. Each unknown exercise contributes only its own actual sets through fallback, so neither loss nor session-total duplication occurs.
- **I — Chat persistence:** After both user and assistant messages are appended, a local profile immediately queues the current versioned state for IndexedDB. Failure leaves the answer usable and displays a storage notice.
- **J — Full Body targets:** Chest, Back, Shoulders, Arms, Quads, and Hamstrings / Glutes. Core is intentionally excluded.
- **K — Candidate consistency:** No declared target muscle lacks an achievable contribution under the current prescription mapping.
- **L — Coach copy:** The page identifies a context-aware Training Coach that can explain current decisions and answer general training/recovery questions; deterministic engines retain readiness and Primary authority.
- **M — Science synchronization:** Training Load calendar windows, tracked-rest/unknown-date distinction, near-zero guard, unknown-exercise fallback and fractional-set boundary are documented from shared rule metadata and matching page copy.
- **N — Full test count:** 72.
- **O — Passed:** 72.
- **P — Known reproducible bugs:** None within the verified environment. Real browser IndexedDB reload remains not verified, not represented as a pass.

## Mobile-first release QA — 2026-09-14

| Check | Result | Evidence |
|---|---|---|
| Mobile visual hierarchy | PASS | Native macOS Google Chrome responsive checks at 375 × 812, 390 × 844, 393 × 852 and 430 × 932; Today, Check-in, Train, Trends, Coach and More routes remained readable and operable. |
| Tablet and desktop continuity | PASS | Native system-browser checks at 768 × 1024 and 1440 × 900; desktop sidebar navigation remains available. |
| Mobile navigation | PASS | Fixed five-item bottom navigation routes to Today, Check-in, Train, Trends and Coach; More exposes Profile, Science & Logic and About. |
| Real portfolio screenshots | PASS | Seven native Chrome full-page captures were exported at 393 × 852 from demo data only. No Codex internal-browser image was used. |
| Regression suite | PASS | 72 / 72 tests passed after the UI update. |
| Python compilation | PASS | `app.py`, `styles.py` and `ui_components.py` compile successfully. |
| IndexedDB reload persistence | NOT VERIFIED end-to-end | No new local profile was created in the shared browser solely for this check. Existing bridge, hydration and serialization tests pass; a manual save → reload acceptance check remains appropriate before deployment. |
| Qwen runtime | NOT RE-RUN in this UI pass | The optional architecture is unchanged; prior real-load/generation verification above remains the existing evidence. |
| Known reproducible functional bugs | NONE within verified flows | No reproducible defect was observed in the tested mobile, tablet or desktop flows. |
