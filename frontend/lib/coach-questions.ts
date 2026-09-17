/**
 * The Coach question library.
 *
 * The wording is the wording the deterministic router already matches — this
 * file only decides *where* a question is offered, never how it is answered.
 * The Coach home keeps four high-frequency questions; everything else lives in
 * the three Coach-internal menus below.
 */

export interface CoachMenu {
  key: string;
  title: string;
  summary: string;
  href: string;
  questions: string[];
}

/** Shown on the Coach home, and nowhere else. */
export const PRIMARY_QUESTIONS = [
  "Why this workout?",
  "Explain my readiness.",
  "Can I train harder today?",
  "How much have I trained this week?",
];

/** Coach-internal secondary surfaces. Never part of the primary app navigation. */
export const COACH_MENUS: CoachMenu[] = [
  {
    key: "personal-response",
    title: "Personal Response",
    summary: "How your own sessions have been followed by your own next check-in.",
    href: "/coach/personal-response",
    questions: [
      "How do I usually respond to high-demand sessions?",
      "How confident is today's personalized recommendation?",
      "How many sessions support this adjustment?",
      "Has Personal Response changed my training before?",
      "Why didn't you increase today's training if I usually recover well?",
    ],
  },
  {
    key: "calibration",
    title: "In-session Calibration",
    summary: "The optional checkpoint you can take while a session is running.",
    href: "/coach/calibration",
    questions: [
      "What is my calibration today?",
      "Why did you tell me to ease?",
      "What RIR did I record?",
      "Do I often need to ease during sessions?",
    ],
  },
  {
    key: "history",
    title: "Training History & Evidence",
    summary: "Recorded sessions, training load and the evidence behind today's recommendation.",
    href: "/coach/history",
    questions: [
      "How much have I trained back this week?",
      "What is my recent training load?",
      "How many sessions have I completed?",
      "What evidence supports today's recommendation?",
    ],
  },
];

export function coachMenu(key: string): CoachMenu {
  const menu = COACH_MENUS.find((item) => item.key === key);
  if (!menu) throw new Error(`Unknown coach menu: ${key}`);
  return menu;
}
