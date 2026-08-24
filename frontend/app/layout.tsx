import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vulnerability Intelligence - MCP Context Engineering",
  description: "Cortex Agents + MCP + Semantic View demo",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
