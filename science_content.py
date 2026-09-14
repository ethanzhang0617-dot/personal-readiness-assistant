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
    "session_rpe": {"concept": "Session-RPE training load", "evidence": "Consensus statement and review", "implementation": "Completed-session duration × session RPE; same-date sessions are summed, then mean daily load across 7 complete calendar days is compared with the preceding 21. Tracked rest days are 0 AU; missing dates remain unknown.", "label": EVIDENCE_LABELS["principle"], "pmids": ["28463642", "29163016"]},
    "personal_hrv": {"concept": "Individual HRV trend", "evidence": "Training-monitoring literature", "implementation": "LnRMSSD is compared with the user's valid personal observations.", "label": EVIDENCE_LABELS["principle"], "pmids": ["34489178", "34639599"]},
    "hrv_thresholds": {"concept": "Exact HRV Green / Amber / Red thresholds", "evidence": "Not directly validated", "implementation": "The z-score bands in this prototype's rule metadata.", "label": EVIDENCE_LABELS["heuristic"], "pmids": []},
    "weekly_volume": {"concept": "Weekly working sets", "evidence": "Resistance-training dose-response literature", "implementation": "Current seven-day muscle-group exposure uses actual completed sets and is compared with user targets or a descriptive logged baseline. Unmapped exercises use a single explicit muscle/focus fallback per exercise.", "label": EVIDENCE_LABELS["principle"], "pmids": ["27433992", "41343037"]},
    "fractional_sets": {"concept": "Direct 1.0 / indirect 0.5 sets", "evidence": "Fractional-set research methodology", "implementation": RECOMMENDATION_RULE_METADATA["fractional_sets"]["label"], "label": EVIDENCE_LABELS["heuristic"], "pmids": ["41343037"]},
    "frequency": {"concept": "Training frequency", "evidence": "Systematic review and meta-analysis", "implementation": "Frequency distributes volume and maintains programme structure; it is not a recovery clock.", "label": EVIDENCE_LABELS["principle"], "pmids": ["30558493"]},
    "autoregulation": {"concept": "Autoregulated session demand", "evidence": "Review and meta-analysis", "implementation": "Readiness primarily modifies duration, sets and RIR guidance.", "label": EVIDENCE_LABELS["principle"], "pmids": ["32813181", "33776802"]},
    "proximity_to_failure": {"concept": "RIR / proximity to failure", "evidence": "Systematic review and meta-regressions", "implementation": "Normal strength usually uses 1–3 RIR; reduced sessions use a more conservative 2–4 RIR range.", "label": EVIDENCE_LABELS["principle"], "pmids": ["36334240", "38970765"]},
    "overall_rule": {"concept": "Overall Green / Amber / Red combination", "evidence": "Not directly validated", "implementation": "Transparent deterministic decision rule shared with readiness_engine.py.", "label": EVIDENCE_LABELS["heuristic"], "pmids": []},
}

REFERENCES = (
    {"authors": "Saw AE, Main LC, Gastin PB", "title": "Monitoring the athlete training response: subjective self-reported measures trump commonly used objective measures: a systematic review", "journal": "British Journal of Sports Medicine", "year": 2016, "citation": "50(5):281–291", "pmid": "26423706"},
    {"authors": "Bourdon PC et al.", "title": "Monitoring Athlete Training Loads: Consensus Statement", "journal": "International Journal of Sports Physiology and Performance", "year": 2017, "citation": "12(Suppl 2):S2-161–S2-170", "pmid": "28463642"},
    {"authors": "Haddad M, Stylianides G, Djaoui L, Dellal A, Chamari K", "title": "Session-RPE Method for Training Load Monitoring: Validity, Ecological Usefulness, and Influencing Factors", "journal": "Frontiers in Neuroscience", "year": 2017, "citation": "11:612", "pmid": "29163016"},
    {"authors": "Schoenfeld BJ, Ogborn D, Krieger JW", "title": "Dose-response relationship between weekly resistance training volume and increases in muscle mass: a systematic review and meta-analysis", "journal": "Journal of Sports Sciences", "year": 2017, "citation": "35(11):1073–1082", "pmid": "27433992"},
    {"authors": "Schoenfeld BJ, Grgic J, Krieger J", "title": "How many times per week should a muscle be trained to maximize muscle hypertrophy? A systematic review and meta-analysis", "journal": "Journal of Sports Sciences", "year": 2019, "citation": "37(11):1286–1295", "pmid": "30558493"},
    {"authors": "Pelland JC, Remmert JF, Robinson ZP, Hinson SR, Zourdos MC", "title": "The Resistance Training Dose Response: Meta-Regressions Exploring the Effects of Weekly Volume and Frequency on Muscle Hypertrophy and Strength Gains", "journal": "Sports Medicine", "year": 2026, "citation": "56(2):481–505", "pmid": "41343037"},
    {"authors": "Greig L et al.", "title": "Autoregulation in Resistance Training: Addressing the Inconsistencies", "journal": "Sports Medicine", "year": 2020, "citation": "50(11):1873–1887", "pmid": "32813181"},
    {"authors": "Zhang X et al.", "title": "Auto-Regulation Method vs. Fixed-Loading Method in Maximum Strength Training for Athletes: A Systematic Review and Meta-Analysis", "journal": "Frontiers in Physiology", "year": 2021, "citation": "12:651112", "pmid": "33776802"},
    {"authors": "Refalo MC, Helms ER, Trexler ET, Hamilton DL, Fyfe JJ", "title": "Influence of Resistance Training Proximity-to-Failure on Skeletal Muscle Hypertrophy: A Systematic Review with Meta-analysis", "journal": "Sports Medicine", "year": 2023, "citation": "53(3):649–665", "pmid": "36334240"},
    {"authors": "Robinson ZP et al.", "title": "Exploring the Dose-Response Relationship Between Estimated Resistance Training Proximity to Failure, Strength Gain, and Muscle Hypertrophy: A Series of Meta-Regressions", "journal": "Sports Medicine", "year": 2024, "citation": "54(9):2209–2231", "pmid": "38970765"},
    {"authors": "Düking P et al.", "title": "Monitoring and adapting endurance training on the basis of heart rate variability monitored by wearable technologies: A systematic review with meta-analysis", "journal": "Journal of Science and Medicine in Sport", "year": 2021, "citation": "24(11):1180–1192", "pmid": "34489178"},
    {"authors": "Manresa-Rocamora A, Sarabia JM, Javaloyes A, Flatt AA, Moya-Ramón M", "title": "Heart Rate Variability-Guided Training for Enhancing Cardiac-Vagal Modulation, Aerobic Fitness, and Endurance Performance: A Methodological Systematic Review with Meta-Analysis", "journal": "International Journal of Environmental Research and Public Health", "year": 2021, "citation": "18(19):10299", "pmid": "34639599"},
)

LIMITATIONS = (
    "It does not diagnose overtraining or medical fatigue.",
    "It does not predict injury or estimate an exact muscle-recovery percentage.",
    "It does not guarantee optimal training or claim that a Green day is risk-free.",
    "It does not claim that HRV predicts today's performance with certainty.",
    "It does not replace professional medical or coaching judgement.",
)
