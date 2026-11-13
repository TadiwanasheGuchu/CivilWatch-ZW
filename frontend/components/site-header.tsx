import { MapPinned } from "lucide-react";
import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="bg-navy text-white">
      <div className="mx-auto flex h-14 max-w-5xl items-center px-4 sm:px-6">
        <Link
          href="/"
          className="inline-flex min-h-11 items-center gap-2 font-heading text-base font-bold tracking-tight"
        >
          <span className="grid size-8 place-items-center rounded-md bg-teal">
            <MapPinned aria-hidden="true" className="size-4" strokeWidth={2.25} />
          </span>
          CivicWatch <span className="font-medium text-white/70">ZW</span>
        </Link>
      </div>
    </header>
  );
}
