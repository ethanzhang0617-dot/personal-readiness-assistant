import { CoachMenuView } from "@/features/coach/coach-menu-view";
import { coachMenu } from "@/lib/coach-questions";

export const metadata = { title: "In-session Calibration · Coach" };

export default function CoachCalibrationPage() {
  return <CoachMenuView menu={coachMenu("calibration")} />;
}
