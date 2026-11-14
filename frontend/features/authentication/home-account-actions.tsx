"use client";

import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { useSession } from "./use-session";

/** Account calls to action on the home page; hidden once signed in. */
export function HomeAccountActions() {
  const { data: session, isPending } = useSession();
  if (isPending || session) return null;
  return (
    <div className="flex flex-col gap-2 sm:flex-row">
      <Link href="/register" className={cn(buttonVariants({ size: "lg" }))}>
        Create an account
      </Link>
      <Link href="/sign-in" className={cn(buttonVariants({ variant: "secondary", size: "lg" }))}>
        Sign in
      </Link>
    </div>
  );
}
