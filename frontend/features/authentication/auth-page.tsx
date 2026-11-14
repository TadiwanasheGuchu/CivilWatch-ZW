import type { ReactNode } from "react";

/** Narrow, centred column used by the sign-in and registration pages. */
export function AuthPage({ title, intro, children }: { title: string; intro: ReactNode; children: ReactNode }) {
  return (
    <main id="main" className="mx-auto w-full max-w-md px-4 pt-6 pb-12 sm:pt-12">
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="mt-2 text-base text-navy-soft">{intro}</p>
      <div className="mt-6 rounded-[var(--radius-panel)] border border-line bg-surface p-4 sm:p-6">
        {children}
      </div>
    </main>
  );
}
