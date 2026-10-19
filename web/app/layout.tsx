import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "StoryPulls",
  description: "Paste a Reel, TikTok or Xiaohongshu post and get the places in it.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
