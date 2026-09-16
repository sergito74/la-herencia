import type { Metadata } from "next";

import { Providers } from "@/app/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "La Herencia",
  description: "Sistema La Herencia",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-slate-50 text-slate-900">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
