import type { Metadata } from "next";
import type { ReactNode } from "react";
import "@fontsource/pixelify-sans/400.css";
import "@fontsource/pixelify-sans/700.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentEval Office",
  description: "Watch every agent evaluation run inside an isolated sandbox office.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
