import { CoachMenuView } from "@/features/coach/coach-menu-view";
import { coachMenu } from "@/lib/coach-questions";

export const metadata = { title: "Training History & Evidence · Coach" };

export default function CoachHistoryPage() {
  return <CoachMenuView menu={coachMenu("history")} />;
}
