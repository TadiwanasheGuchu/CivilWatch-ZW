"use client";

import { Panel } from "@/components/ui/panel";
import { MembershipList } from "@/features/council/membership-list";

import { ChangePasswordForm } from "./change-password-form";
import { EmailPreference } from "./email-preference";
import { ProfileForm } from "./profile-form";
import { RequireSession } from "./require-session";
import { SignOutButton } from "./sign-out-button";

export function AccountView() {
  return (
    <RequireSession>
      {(session) => (
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold">Your account</h1>
            <p className="mt-1 text-base text-navy-soft">Signed in as {session.user.email}</p>
          </div>
          <MembershipList />
          <div className="grid gap-6 lg:grid-cols-2">
            <Panel title="Your details">
              <ProfileForm session={session} />
            </Panel>
            <Panel title="Password" description="Changing it signs you out on every other device.">
              <ChangePasswordForm session={session} />
            </Panel>
          </div>
          <Panel title="Email" description="In-app notifications are always on.">
            <EmailPreference session={session} />
          </Panel>
          <Panel title="Sign out" description="Sign out of CivicWatch on this device.">
            <SignOutButton session={session} />
          </Panel>
        </div>
      )}
    </RequireSession>
  );
}
