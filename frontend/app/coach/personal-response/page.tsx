import { CoachMenuView } from "@/features/coach/coach-menu-view";
import { coachMenu } from "@/lib/coach-questions";

export const metadata = { title: "Personal Response · Coach" };

export default function CoachPersonalResponsePage() {
  return <CoachMenuView menu={coachMenu("personal-response")} />;
}
