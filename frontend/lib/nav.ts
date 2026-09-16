import { Dumbbell, MessageCircle, Sun, TrendingUp, User, type LucideIcon } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

/** Five primary destinations only; secondary surfaces stay under Profile. */
export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Today", icon: Sun },
  { href: "/train", label: "Train", icon: Dumbbell },
  { href: "/coach", label: "Coach", icon: MessageCircle },
  { href: "/insights", label: "Insights", icon: TrendingUp },
  { href: "/profile", label: "Profile", icon: User },
];

export function isActivePath(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
