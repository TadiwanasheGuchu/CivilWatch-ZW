import type { Metadata } from "next";

import { AccountView } from "@/features/authentication/account-view";

export const metadata: Metadata = { title: "Your account" };

export default function AccountPage() {
  return (
    <main id="main" className="mx-auto max-w-5xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <AccountView />
    </main>
  );
}
