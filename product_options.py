"""User-selectable profile options — shared by Streamlit and the API.

Extracted from ``app.py`` so the API can offer exactly the same choices without
importing the Streamlit app. No formula, threshold or rule lives here.
"""

from __future__ import annotations


ACTIVITIES: tuple[str, ...] = ("Strength Training", "Running", "Cycling", "HYROX / Functional Fitness",
                               "Team Sports", "General Fitness", "Other")
GOALS: tuple[str, ...] = ("General Fitness", "Strength", "Muscle Gain", "Fat Loss", "Endurance",
                          "Performance", "Recovery / Health", "Other")
LEVELS: tuple[str, ...] = ("Beginner", "Intermediate", "Advanced")
SEXES: tuple[str, ...] = ("Male", "Female", "Prefer not to say")
SPLITS: tuple[str, ...] = ("No Preference", "Body Part Split", "Push / Pull / Legs", "Upper / Lower",
                           "Full Body", "Running-focused", "Hybrid")
