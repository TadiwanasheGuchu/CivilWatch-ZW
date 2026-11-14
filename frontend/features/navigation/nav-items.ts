import { Compass, House, ListChecks, Plus, UserRound, type LucideIcon } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  primary?: boolean;
}

/** Resident navigation (CLAUDE.md §4.2). Every item leads to a working page. */
export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Home", icon: House },
  { href: "/explore", label: "Explore", icon: Compass },
  { href: "/report", label: "Report", icon: Plus, primary: true },
  { href: "/my-reports", label: "My reports", icon: ListChecks },
  { href: "/account", label: "Profile", icon: UserRound },
];

export function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/my-reports") return pathname === "/my-reports" || pathname.startsWith("/reports/");
  return pathname === href || pathname.startsWith(`${href}/`);
}
