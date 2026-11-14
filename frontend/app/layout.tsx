import type { Metadata, Viewport } from "next";
import { Inter, Manrope } from "next/font/google";
import type { ReactNode } from "react";

import { SiteHeader } from "@/components/site-header";
import { BottomNav } from "@/features/navigation/bottom-nav";

import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  weight: ["600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "CivicWatch ZW", template: "%s · CivicWatch ZW" },
  description:
    "Report damaged roads, broken streetlights, blocked drains and other public infrastructure problems to your council, and follow them until they are fixed.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#172B3A",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en-ZW" className={`${inter.variable} ${manrope.variable}`}>
      <body className="min-h-dvh antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2"
        >
          Skip to content
        </a>
        <Providers>
          <SiteHeader />
          {/* Room for the phone bottom navigation. */}
          <div className="pb-20 md:pb-0">{children}</div>
          <BottomNav />
        </Providers>
      </body>
    </html>
  );
}
