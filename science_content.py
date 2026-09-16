"""Central evidence metadata and carefully bounded product claims."""

from __future__ import annotations

from readiness_engine import READINESS_RULE_METADATA
from training_recommendation_engine import RECOMMENDATION_RULE_METADATA


EVIDENCE_LABELS = {
    "principle": "EVIDENCE-SUPPORTED PRINCIPLE",
    "heuristic": "PROTOTYPE HEURISTIC",
    "not_clinical": "NOT A CLINICAL THRESHOLD",
}

EVIDENCE_MAP = {
    "subjective_monitoring": {"concept": "Subjective wellness monitoring", "evidence": "Systematic review", "implementation": "Fatigue, stress, soreness and motivation form the Subjective Wellness domain.", "label": EVIDENCE_LABELS["principle"], "pmids": ["26423706"]},
    "session_rpe": {"concept": "Session-RPE training load", "evidence": "Consensus statement and review", "implementation": "Completed-session duration × session RPE; same-date sessions are summed, then mean daily load across 7 complete calendar days is compared with the preceding 21. Tracked rest days are 0 AU; missing dates remain unknown. The comparison window itself is an implementation choice, not a validated monitoring window.", "label": EVIDENCE_LABELS["principle"], "pmids": ["28463642", "29163016"]},
    "personal_hrv": {"concept": "Individual HRV trend", "evidence": "Training-monitoring literature on within-athlete HR/HRV interpretation", "implementation": "LnRMSSD is compared with the user's valid personal observations rather than population cut-offs. Measurement context and day-to-day variability are treated as real, and HRV is used as one signal among several.", "label": EVIDENCE_LABELS["principle"], "pmids": ["24578692", "34489178", "34639599"]},
    "hrv_thresholds": {"concept": "Exact HRV Green / Amber / Red thresholds", "evidence": "Not directly validated", "implementation": "The z-score bands in this prototype's rule metadata.", "label": EVIDENCE_LABELS["heuristic"], "pmids": []},
    "sleep_recovery": {"concept": "Sleep and recovery input", "evidence": "Sleep is monitored in athlete-monitoring practice; this product's exact sleep thresholds are not validated", "implementation": "Sleep duration relative to the user's own stated sleep need, plus self-reported sleep quality, form the Sleep & Recovery domain.", "label": EVIDENCE_LABELS["heuristic"], "pmids": []},
    "local_soreness": {"concept": "Local soreness as session context", "evidence": "Subjective monitoring literature supports self-reported soreness as one monitoring signal; the muscle-group compatibility rule is a product heuristic", "implementation": "Today's reported local soreness modifies which session is compatible. It is a contextual signal, never a recovery measurement or a percentage.", "label": EVIDENCE_LABELS["heuristic"], "pmids": ["26423706"]},
    "weekly_volume": {"concept": "Weekly working sets", "evidence": "Resistance-training dose-response literature", "implementation": "Current seven-day muscle-group exposure uses actual completed sets and is compared with user targets or a descriptive logged baseline. Unmapped exercises use a single explicit muscle/focus fallback per exercise.", "label": EVIDENCE_LABELS["principle"], "pmids": ["27433992", "41343037"]},
    "fractional_sets": {"concept": "Direct 1.0 / indirect 0.5 sets", "evidence": "Fractional set counting is a quantification method used in volume dose-response research; it is not a physiological equivalence", "implementation": RECOMMENDATION_RULE_METADATA["fractional_sets"]["label"], "label": EVIDENCE_LABELS["heuristic"], "pmids": ["41343037"]},
    "frequency": {"concept": "Training frequency", "evidence": "Systematic review and meta-analysis: when weekly volume is equated, frequency shows limited independent effect on hypertrophy", "implementation": "Frequency is used to distribute volume and maintain programme structure, not as a claim that more frequent training is inherently better and not as a fixed 48- or 72-hour recovery clock.", "label": EVIDENCE_LABELS["principle"], "pmids": ["30558493"]},
    "autoregulation": {"concept": "Autoregulated session demand", "evidence": "Review and meta-analysis support the broader concept, not this product's specific rules", "implementation": "Readiness primarily modifies duration, sets and RIR guidance.", "label": EVIDENCE_LABELS["principle"], "pmids": ["32813181", "33776802"]},
    "proximity_to_failure": {"concept": "RIR / proximity to failure", "evidence": "Systematic review and meta-regressions", "implementation": "Normal strength usually uses 1–3 RIR; reduced sessions use a more conservative 2–4 RIR range. These specific ranges are practical product guidance, not validated universal optima.", "label": EVIDENCE_LABELS["principle"], "pmids": ["36334240", "38970765"]},
    "overall_rule": {"concept": "Overall Green / Amber / Red combination", "evidence": "Not directly validated", "implementation": "Transparent deterministic decision rule shared with readiness_engine.py.", "label": EVIDENCE_LABELS["heuristic"], "pmids": []},
}

#: Bibliographic fields verified against PubMed, Europe PMC and Crossref on 2026-09-16.
#: See docs/V1_1_SCIENCE_REFERENCE_AUDIT.md for the per-reference evidence.
REFERENCES = (
    {"authors": "Saw AE, Main LC, Gastin PB", "title": "Monitoring the athlete training response: subjective self-reported measures trump commonly used objective measures: a systematic review", "journal": "British Journal of Sports Medicine", "year": 2016, "citation": "50(5):281–291", "pmid": "26423706", "doi": "10.1136/bjsports-2015-094758"},
    {"authors": "Bourdon PC, Cardinale M, Murray A, Gastin P, Kellmann M, Varley MC, Gabbett TJ, Coutts AJ, Burgess DJ, Gregson W, Cable NT", "title": "Monitoring Athlete Training Loads: Consensus Statement", "journal": "International Journal of Sports Physiology and Performance", "year": 2017, "citation": "12(Suppl 2):S2-161–S2-170", "pmid": "28463642", "doi": "10.1123/IJSPP.2017-0208"},
    {"authors": "Haddad M, Stylianides G, Djaoui L, Dellal A, Chamari K", "title": "Session-RPE Method for Training Load Monitoring: Validity, Ecological Usefulness, and Influencing Factors", "journal": "Frontiers in Neuroscience", "year": 2017, "citation": "11:612", "pmid": "29163016", "doi": "10.3389/fnins.2017.00612"},
    {"authors": "Schoenfeld BJ, Ogborn D, Krieger JW", "title": "Dose-response relationship between weekly resistance training volume and increases in muscle mass: A systematic review and meta-analysis", "journal": "Journal of Sports Sciences", "year": 2017, "citation": "35(11):1073–1082", "pmid": "27433992", "doi": "10.1080/02640414.2016.1210197"},
    {"authors": "Schoenfeld BJ, Grgic J, Krieger J", "title": "How many times per week should a muscle be trained to maximize muscle hypertrophy? A systematic review and meta-analysis of studies examining the effects of resistance training frequency", "journal": "Journal of Sports Sciences", "year": 2019, "citation": "37(11):1286–1295", "pmid": "30558493", "doi": "10.1080/02640414.2018.1555906"},
    {"authors": "Pelland JC, Remmert JF, Robinson ZP, Hinson SR, Zourdos MC", "title": "The Resistance Training Dose Response: Meta-Regressions Exploring the Effects of Weekly Volume and Frequency on Muscle Hypertrophy and Strength Gains", "journal": "Sports Medicine", "year": 2026, "citation": "56(2):481–505", "pmid": "41343037", "doi": "10.1007/s40279-025-02344-w"},
    {"authors": "Greig L, Stephens Hemingway BH, Aspe RR, Cooper K, Comfort P, Swinton PA", "title": "Autoregulation in Resistance Training: Addressing the Inconsistencies", "journal": "Sports Medicine", "year": 2020, "citation": "50(11):1873–1887", "pmid": "32813181", "doi": "10.1007/s40279-020-01330-8"},
    {"authors": "Zhang X, Li H, Bi S, Luo Y, Cao Y, Zhang G", "title": "Auto-Regulation Method vs. Fixed-Loading Method in Maximum Strength Training for Athletes: A Systematic Review and Meta-Analysis", "journal": "Frontiers in Physiology", "year": 2021, "citation": "12:651112", "pmid": "33776802", "doi": "10.3389/fphys.2021.651112"},
    {"authors": "Refalo MC, Helms ER, Trexler ET, Hamilton DL, Fyfe JJ", "title": "Influence of Resistance Training Proximity-to-Failure on Skeletal Muscle Hypertrophy: A Systematic Review with Meta-analysis", "journal": "Sports Medicine", "year": 2023, "citation": "53(3):649–665", "pmid": "36334240", "doi": "10.1007/s40279-022-01784-y"},
    {"authors": "Robinson ZP, Pelland JC, Remmert JF, Refalo MC, Jukic I, Steele J, Zourdos MC", "title": "Exploring the Dose-Response Relationship Between Estimated Resistance Training Proximity to Failure, Strength Gain, and Muscle Hypertrophy: A Series of Meta-Regressions", "journal": "Sports Medicine", "year": 2024, "citation": "54(9):2209–2231", "pmid": "38970765", "doi": "10.1007/s40279-024-02069-2"},
    {"authors": "Düking P, Zinner C, Trabelsi K, Reed JL, Holmberg HC, Kunz P, Sperlich B", "title": "Monitoring and adapting endurance training on the basis of heart rate variability monitored by wearable technologies: A systematic review with meta-analysis", "journal": "Journal of Science and Medicine in Sport", "year": 2021, "citation": "24(11):1180–1192", "pmid": "34489178", "doi": "10.1016/j.jsams.2021.04.012"},
    {"authors": "Manresa-Rocamora A, Sarabia JM, Javaloyes A, Flatt AA, Moya-Ramón M", "title": "Heart Rate Variability-Guided Training for Enhancing Cardiac-Vagal Modulation, Aerobic Fitness, and Endurance Performance: A Methodological Systematic Review with Meta-Analysis", "journal": "International Journal of Environmental Research and Public Health", "year": 2021, "citation": "18(19):10299", "pmid": "34639599", "doi": "10.3390/ijerph181910299"},
    {"authors": "Buchheit M", "title": "Monitoring training status with HR measures: do all roads lead to Rome?", "journal": "Frontiers in Physiology", "year": 2014, "citation": "5:73", "pmid": "24578692", "doi": "10.3389/fphys.2014.00073"},
)

LIMITATIONS = (
    "It does not diagnose overtraining or medical fatigue.",
    "It does not predict injury or estimate an exact muscle-recovery percentage.",
    "It does not guarantee optimal training or claim that a Green day is risk-free.",
    "It does not claim that HRV predicts today's performance with certainty.",
    "It does not claim that its thresholds, domain weights or monitoring windows are prospectively validated.",
    "It does not replace professional medical or coaching judgement.",
)
