import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Market & Competitor Analysis Agent",
  description:
    "Autonomous AI agent that researches a business idea and returns a SWOT + competitor analysis report.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
