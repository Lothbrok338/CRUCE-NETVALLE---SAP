import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Control Tributario Integral",
  description: "Cruce NETVALLE / SIAT / SAP de IVA e IT",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-[#F5F7FA] text-foreground antialiased">
        <header className="bg-[#1F4E78] text-white shadow">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <Link href="/" className="text-lg font-bold">Control Tributario Integral</Link>
            <nav className="flex gap-6 text-sm font-medium">
              <Link href="/" className="hover:underline">Nuevo control</Link>
              <Link href="/historial" className="hover:underline">Historial</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
