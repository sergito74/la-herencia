import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { Providers } from "@/app/providers";
import { NavHeader } from "@/components/layout/NavHeader";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "La Herencia",
  description: "Sistema La Herencia",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es" className={inter.variable}>
      <body className="min-h-screen bg-background font-sans text-ink-primary">
        <Providers>
          <NavHeader />
          {children}
        </Providers>
      </body>
    </html>
  );
}
