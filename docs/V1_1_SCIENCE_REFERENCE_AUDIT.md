# V1.1 — Science & References Audit

**Audit date:** 2026-09-16
**Auditor method:** every bibliographic field was re-derived from authoritative indexes; no field was
carried over from the previous reference list without verification.
**Verification sources used per reference:**

1. PubMed / NCBI E-utilities — `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=<PMID>`
2. Europe PMC REST — `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:<PMID>%20AND%20SRC:MED&format=json&resultType=core`
3. Crossref — `https://api.crossref.org/works/<DOI>`
4. DOI resolution — `https://doi.org/<DOI>` (followed to the publisher page)

All 13 DOIs were resolved through Crossref with **no errors**; the added Buchheit DOI resolved
HTTP 200 to the official Frontiers article page.
**Scope of this audit:** references, science copy, evidence boundaries and reference formatting only.
No engine, threshold, aggregation rule, recommendation rule, router, guard or DeepSeek code was changed.

---

## 1. Reference audit table

`Status` = PASS (already correct) · CORRECTED (fixed by this audit) · ADDED · FAIL (unverifiable; removed).

### R1 — Saw 2016 · PASS

| | |
|---|---|
| Authors | Saw AE, Main LC, Gastin PB |
| Year | 2016 |
| Official title | Monitoring the athlete training response: subjective self-reported measures trump commonly used objective measures: a systematic review |
| Journal | British Journal of Sports Medicine |
| Volume / issue / pages | 50(5):281–291 |
| PMID | 26423706 |
| DOI | 10.1136/bjsports-2015-094758 |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | Subjective wellness monitoring row |
| What it supports | Self-reported wellness measures are sensitive to training response and are useful monitoring inputs. |
| What it does NOT support | That subjective measures are *always* superior to objective measures in every context; that this product's four wellness items or their cut-offs are validated. |
| Wording risk | Low. The product must not paraphrase the title as "subjective beats objective". |

### R2 — Bourdon 2017 · CORRECTED (author list completed)

| | |
|---|---|
| Authors | Bourdon PC, Cardinale M, Murray A, Gastin P, Kellmann M, Varley MC, Gabbett TJ, Coutts AJ, Burgess DJ, Gregson W, Cable NT |
| Year | 2017 |
| Official title | Monitoring Athlete Training Loads: Consensus Statement |
| Journal | International Journal of Sports Physiology and Performance |
| Volume / issue / pages | 12(Suppl 2):S2-161–S2-170 |
| PMID | 28463642 |
| DOI | 10.1123/IJSPP.2017-0208 |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | Session-RPE training load row |
| What it supports | Training-load monitoring practice, including session-RPE as an accepted practical load measure. |
| What it does NOT support | This product's specific 7-versus-21-day comparison window, the 28-day coverage requirement, or any injury-prediction claim. |
| Wording risk | Low. AU is a relative load unit, not a physiological measurement. |

### R3 — Haddad 2017 · PASS

| | |
|---|---|
| Authors | Haddad M, Stylianides G, Djaoui L, Dellal A, Chamari K |
| Year | 2017 |
| Official title | Session-RPE Method for Training Load Monitoring: Validity, Ecological Usefulness, and Influencing Factors |
| Journal | Frontiers in Neuroscience |
| Volume / article | 11:612 |
| PMID | 29163016 |
| DOI | 10.3389/fnins.2017.00612 |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | Session-RPE training load row |
| What it supports | Session-RPE (duration × session RPE) as a valid, ecologically useful load measure, with known influencing factors. |
| What it does NOT support | That AU is a direct physiological measurement, or that a single-day load change predicts harm. |
| Wording risk | Low. |

### R4 — Schoenfeld 2017 · CORRECTED (title capitalisation)

| | |
|---|---|
| Authors | Schoenfeld BJ, Ogborn D, Krieger JW |
| Year | 2017 |
| Official title | Dose-response relationship between weekly resistance training volume and increases in muscle mass: A systematic review and meta-analysis |
| Journal | Journal of Sports Sciences |
| Volume / issue / pages | 35(11):1073–1082 |
| PMID | 27433992 |
| DOI | 10.1080/02640414.2016.1210197 |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | Weekly working sets row |
| What it supports | Weekly resistance-training volume is related to hypertrophy in a dose-response manner. |
| What it does NOT support | A universal optimal weekly set number for every individual, or this product's user-target logic. |
| Wording risk | Low. |

### R5 — Schoenfeld 2019 · CORRECTED (title was truncated in the product)

| | |
|---|---|
| Authors | Schoenfeld BJ, Grgic J, Krieger J |
| Year | 2019 |
| Official title | How many times per week should a muscle be trained to maximize muscle hypertrophy? A systematic review and meta-analysis of studies examining the effects of resistance training frequency |
| Journal | Journal of Sports Sciences |
| Volume / issue / pages | 37(11):1286–1295 |
| PMID | 30558493 |
| DOI | 10.1080/02640414.2018.1555906 |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | Frequency row |
| What it supports | Frequency analysis context; when total weekly volume is equated, frequency has limited independent effect on hypertrophy. |
| What it does NOT support | That training a muscle more often is automatically superior, or that any specific split is optimal. |
| Wording risk | This was the highest-risk reference: the previous truncated title ("…muscle hypertrophy? A systematic review and meta-analysis") invited an over-simple reading. The full title makes the volume-equated scope explicit. |

### R6 — Pelland 2026 · PASS

| | |
|---|---|
| Authors | Pelland JC, Remmert JF, Robinson ZP, Hinson SR, Zourdos MC |
| Year | 2026 |
| Official title | The Resistance Training Dose Response: Meta-Regressions Exploring the Effects of Weekly Volume and Frequency on Muscle Hypertrophy and Strength Gains |
| Journal | Sports Medicine |
| Volume / issue / pages | 56(2):481–505 |
| PMID | 41343037 |
| DOI | 10.1007/s40279-025-02344-w |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | Weekly working sets row; fractional sets row |
| What it supports | Volume and frequency dose-response modelling; fractional set counting as a quantification approach used in volume research. |
| What it does NOT support | That a 0.5 secondary set is physiologically equal to half a direct set; that the app's per-user targets are proven. |
| Wording risk | Medium if the product ever states 0.5 as a biological fact. Current copy labels it a transparent approximation. |

### R7 — Greig 2020 · CORRECTED (author list completed)

| | |
|---|---|
| Authors | Greig L, Stephens Hemingway BH, Aspe RR, Cooper K, Comfort P, Swinton PA |
| Year | 2020 |
| Official title | Autoregulation in Resistance Training: Addressing the Inconsistencies |
| Journal | Sports Medicine |
| Volume / issue / pages | 50(11):1873–1887 |
| PMID | 32813181 |
| DOI | 10.1007/s40279-020-01330-8 |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | Autoregulation row |
| What it supports | Autoregulation is a meaningful but inconsistently defined and implemented approach in resistance training. |
| What it does NOT support | This product's specific readiness→session-demand rules. |
| Wording risk | The paper documents inconsistency in the field, so it must not be cited as validating one particular autoregulation scheme. |

### R8 — Zhang 2021 · CORRECTED (author list completed)

| | |
|---|---|
| Authors | Zhang X, Li H, Bi S, Luo Y, Cao Y, Zhang G |
| Year | 2021 |
| Official title | Auto-Regulation Method vs. Fixed-Loading Method in Maximum Strength Training for Athletes: A Systematic Review and Meta-Analysis |
| Journal | Frontiers in Physiology |
| Volume / article | 12:651112 |
| PMID | 33776802 |
| DOI | 10.3389/fphys.2021.651112 |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | Autoregulation row |
| What it supports | Autoregulation methods can be at least as effective as fixed loading for maximum-strength outcomes in athletes. |
| What it does NOT support | That readiness-driven muscle-group selection is validated; the paper concerns load autoregulation for strength. |
| Wording risk | Medium — the population is athletes and the outcome is maximum strength. |

### R9 — Refalo 2023 · PASS

| | |
|---|---|
| Authors | Refalo MC, Helms ER, Trexler ET, Hamilton DL, Fyfe JJ |
| Year | 2023 |
| Official title | Influence of Resistance Training Proximity-to-Failure on Skeletal Muscle Hypertrophy: A Systematic Review with Meta-analysis |
| Journal | Sports Medicine |
| Volume / issue / pages | 53(3):649–665 |
| PMID | 36334240 |
| DOI | 10.1007/s40279-022-01784-y |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | RIR / proximity-to-failure row |
| What it supports | Proximity to failure is a relevant programming variable for hypertrophy. |
| What it does NOT support | That 1–3 RIR (or 2–4 RIR) is a validated universal optimum. |
| Wording risk | Medium if product ranges are presented as validated thresholds. Current copy calls them practical product guidance. |

### R10 — Robinson 2024 · CORRECTED (author list completed)

| | |
|---|---|
| Authors | Robinson ZP, Pelland JC, Remmert JF, Refalo MC, Jukic I, Steele J, Zourdos MC |
| Year | 2024 |
| Official title | Exploring the Dose-Response Relationship Between Estimated Resistance Training Proximity to Failure, Strength Gain, and Muscle Hypertrophy: A Series of Meta-Regressions |
| Journal | Sports Medicine |
| Volume / issue / pages | 54(9):2209–2231 |
| PMID | 38970765 |
| DOI | 10.1007/s40279-024-02069-2 |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | RIR / proximity-to-failure row |
| What it supports | Dose-response modelling of estimated proximity to failure for strength and hypertrophy. |
| What it does NOT support | RIR-prescription ranges for a specific individual or a specific session |
| Wording risk | "Estimated" proximity to failure is a modelling construct; the product's RIR instruction is user self-report. |

### R11 — Düking 2021 · CORRECTED (author list completed)

| | |
|---|---|
| Authors | Düking P, Zinner C, Trabelsi K, Reed JL, Holmberg HC, Kunz P, Sperlich B |
| Year | 2021 |
| Official title | Monitoring and adapting endurance training on the basis of heart rate variability monitored by wearable technologies: A systematic review with meta-analysis |
| Journal | Journal of Science and Medicine in Sport |
| Volume / issue / pages | 24(11):1180–1192 |
| PMID | 34489178 |
| DOI | 10.1016/j.jsams.2021.04.012 |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | Individual HRV trend row; endurance intensity-modulation statement |
| What it supports | HRV-based monitoring and adaptation within **endurance/aerobic** training. |
| What it does NOT support | Muscle-group selection (chest/back/legs), resistance-training volume decisions, or injury prediction. |
| Wording risk | HIGH if generalised beyond endurance. Product copy confines it to aerobic intensity modulation. |

### R12 — Manresa-Rocamora 2021 · PASS

| | |
|---|---|
| Authors | Manresa-Rocamora A, Sarabia JM, Javaloyes A, Flatt AA, Moya-Ramón M |
| Year | 2021 |
| Official title | Heart Rate Variability-Guided Training for Enhancing Cardiac-Vagal Modulation, Aerobic Fitness, and Endurance Performance: A Methodological Systematic Review with Meta-Analysis |
| Journal | International Journal of Environmental Research and Public Health |
| Volume / issue / article | 18(19):10299 |
| PMID | 34639599 |
| DOI | 10.3390/ijerph181910299 |
| Verified by | PubMed · Europe PMC · Crossref |
| Product use | Individual HRV trend row |
| What it supports | HRV-guided training can influence cardiac-vagal modulation, aerobic fitness and endurance performance. |
| What it does NOT support | Resistance-training or muscle-group decisions; the exact thresholds used here. |
| Wording risk | HIGH for the same reason as R11. |

### R13 — Buchheit 2014 · ADDED

| | |
|---|---|
| Authors | Buchheit M |
| Year | 2014 |
| Official title | Monitoring training status with HR measures: do all roads lead to Rome? |
| Journal | Frontiers in Physiology |
| Volume / article | 5:73 |
| PMID | 24578692 |
| DOI | 10.3389/fphys.2014.00073 |
| Verified by | PubMed · Europe PMC · Crossref · DOI resolution (HTTP 200 → Frontiers article page) |
| Product use | Individual HRV trend row (within-athlete interpretation) |
| What it supports | HR/HRV monitoring is most useful interpreted within the individual, with attention to measurement conditions, variability and the broader monitoring context. |
| What it does NOT support | This product's exact z-score bands, or that HRV alone determines training content. |
| Wording risk | Low, provided it is cited for interpretation principles rather than thresholds. |

---

## 2. Corrections summary

| Item | Change |
|---|---|
| Schoenfeld 2019 title | **CORRECTED** — truncated product title replaced with the official full title |
| Schoenfeld 2017 title | **CORRECTED** — "a systematic review" → "A systematic review" |
| Bourdon 2017 authors | **CORRECTED** — "Bourdon PC et al." → full 11-author list |
| Greig 2020 authors | **CORRECTED** — "Greig L et al." → full 6-author list |
| Zhang 2021 authors | **CORRECTED** — "Zhang X et al." → full 6-author list |
| Robinson 2024 authors | **CORRECTED** — "Robinson ZP et al." → full 7-author list |
| Düking 2021 authors | **CORRECTED** — "Düking P et al." → full 7-author list |
| DOIs | **ADDED** — every reference now carries its Crossref-verified DOI |
| Buchheit 2014 | **ADDED** — verified and cited for within-athlete HR/HRV interpretation |

Reference count: **12 before → 13 after** (1 added, 0 removed, 7 corrected, 0 unverifiable).

No fake reference, PMID mismatch or DOI mismatch was found. Every PMID resolved to the expected
paper in both PubMed and Europe PMC, and every DOI resolved in Crossref to a matching title.

---

## 3. Claim classification

27 meaningful claims were reviewed in `science_content.py`, `app.py` (Science & Logic),
`ui_components.py` and `README.md`.

| Class | Count | Examples |
|---|---|---|
| **A — directly supported by published evidence** | 8 | session-RPE as a load measure; weekly volume dose-response; autoregulation as an approach; proximity to failure as a programming variable; HRV-guided endurance intensity modulation; within-athlete HR/HRV interpretation; subjective wellness as a monitoring input; volume-equated frequency showing limited independent effect |
| **B — evidence-informed interpretation** | 6 | using LnRMSSD against a personal baseline as one readiness signal; using sleep vs personal need as a readiness input; using a session-RPE load trend to modify session demand; using weekly set exposure to prioritise muscle groups; mapping readiness to session demand; using local soreness as session-compatibility context |
| **C — product heuristic** | 13 | every threshold band, the domain aggregation rule, the Readiness Index mapping, the 7/21-day load windows, the 28-day coverage rule, session-demand mapping, RIR ranges, fractional set weighting, exposure window and target application, the recommendation order, the avoid-today rules, safety STOP routing |
| **D — unsupported / overclaimed** | **0** | — |

No claim of class D was found. Existing copy already used limiting language ("not a recovery
percentage, fatigue probability or injury probability"), and the audit preserved that.

---

## 4. Product Heuristic Inventory

Every row below is an explicit product decision. None of them is a validated threshold.

| # | Heuristic | Informing evidence | Exact rule directly validated? |
|---|---|---|---|
| H1 | HRV / LnRMSSD z-score bands (Green ≥ −0.5, Amber < −0.5, Red < −1.0) | Buchheit 2014; HRV monitoring reviews | **No** — bands are a prototype choice |
| H2 | Resting-HR z-score bands | HR monitoring practice | **No** |
| H3 | Sleep duration ratio bands (Green ≥ 0.90, Amber ≥ 0.80, Red < 0.80 of personal need) | Sleep monitoring practice | **No** |
| H4 | Sleep-quality mapping | Subjective monitoring practice | **No** |
| H5 | Subjective "badness" normalisation and its bands | Saw 2016 (concept only) | **No** |
| H6 | Domain aggregation and Green/Amber/Red combination; "fewer than 3 classifiable domains → INSUFFICIENT DATA" | none directly | **No** |
| H7 | Readiness Index mapping (Green 100 / Amber 60 / Red 25, averaged) | none directly | **No** — communication score only |
| H8 | Training-load windows: last 7 complete calendar days vs preceding 21; 28 covered dates for a full comparison; near-zero reference guard | session-RPE literature for load; window is an implementation choice | **No** |
| H9 | Session-demand mapping (Green → Normal, Amber → Reduced/autoregulated, Red → rest/lower demand, STOP → none) | autoregulation literature (concept) | **No** |
| H10 | RIR guidance (normal 1–3 RIR; reduced 2–4 RIR) | Refalo 2023; Robinson 2024 (concept) | **No** — practical product ranges |
| H11 | Fractional set weighting (direct 1.0, mapped secondary 0.5) + single explicit fallback per unmapped exercise | Pelland 2026 uses fractional set counting as a quantification approach | **No** — transparent operational weighting, **not** a physiological equivalence |
| H12 | Exposure window (last 7 days including today) and weekly target application | Schoenfeld 2017; Pelland 2026 (concept) | **No** |
| H13 | Recommendation order, avoid-today rules and safety STOP routing | none directly; conservative product design | **No** |

---

## 5. Claim → source matrix

| Product claim | Reference(s) | Relationship |
|---|---|---|
| Self-reported wellness is a useful monitoring input | R1 | Directly supports the concept; does not validate the product's items or bands |
| Session-RPE (duration × RPE) is an acceptable load measure | R2, R3 | Directly supports the method; does not validate the 7/21-day windows |
| Training load in AU is a relative monitoring unit | R2, R3 | Directly supports; AU must never be described as a physiological measurement |
| HRV is one monitoring signal, best read within the individual | R13, R11, R12 | Broadly informs; R11/R12 are endurance-scoped and do not cover muscle-group selection |
| HRV-guided training changes endurance intensity prescription | R11, R12 | Directly supports within endurance; does not generalise to resistance sessions |
| Weekly resistance-training volume matters (dose-response) | R4, R6 | Directly supports the concept; does not validate a universal set target |
| Fractional set counting is a defensible quantification approach | R6 | Supports the *counting method*; explicitly does not support 0.5 as a biological equivalence |
| Frequency distributes volume; volume-equated frequency effect is limited | R5 | Directly supports the volume-equated reading; does not support "more frequency is better" |
| Autoregulation is a valid approach in resistance training | R7, R8 | Broadly informs; does not validate this product's mapping |
| Proximity to failure is a programming variable | R9, R10 | Broadly informs; does not validate 1–3 or 2–4 RIR as optima |
| Readiness modifies session demand rather than muscle-group choice for endurance users | R3, R11, R12 | Evidence-informed interpretation |
| Local soreness is session context, not a recovery measurement | R1 | Broadly informs only |
| Every threshold band, weight, window and ordering rule in the app | — | **No direct source.** Documented as product heuristic (see inventory) |

---

## 6. User-facing Evidence boundaries (final copy)

Added to the top of the **Science & Logic** page:

> **Evidence boundaries**
>
> This prototype is evidence-informed, not clinically validated. Published research informs which
> monitoring signals are collected and how they are interpreted: self-reported wellness, session-RPE
> training load, resistance-training volume and frequency, autoregulation, proximity to failure, and
> HRV-guided training.
>
> The application's own readiness thresholds, domain aggregation rules, Readiness Index scale,
> training-load comparison windows, session-demand mapping, RIR ranges and recommendation order are
> transparent product heuristics. They are deliberately inspectable and adjustable, and they have not
> been prospectively validated as clinical, performance-prediction or injury-prediction thresholds.
>
> The table further down states, for each concept, whether the literature supports the broader
> principle or whether the exact rule is a prototype heuristic.

---

## 7. Remaining scientific limitations

1. The literature cited supports **concepts**. Nothing in it prospectively validates this product's
   thresholds, windows, weights or recommendation order.
2. HRV-guided training evidence (R11, R12) comes from **endurance/aerobic** populations. Its role in
   this product is deliberately limited to modifying aerobic intensity, never muscle-group selection.
3. The wellness and soreness inputs use **single-item self-report**; the cited review supports
   self-report as a monitoring class, not these specific items or scales.
4. RIR is **self-estimated** by the user; the dose-response work cited models *estimated* proximity to
   failure, so RIR guidance remains practical coaching guidance rather than a measured variable.
5. Fractional secondary-set weighting is an **operational counting convention**. It should never be
   presented as a physiological ratio.
6. The product's own defaults (28-day baseline window, 14-day limited threshold, 7/21-day load windows,
   28-day coverage rule) are **implementation choices** with no direct supporting citation.
7. Readiness Index is a **communication score**; it is not a recovery percentage, a fatigue
   probability or an injury probability.
8. No reference in this list has been used to support a medical, diagnostic or injury-prediction claim.
