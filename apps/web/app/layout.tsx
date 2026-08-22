import type { Metadata } from "next";
import "./globals.css";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { ToastProvider } from "@/components/common/Toast";

export const metadata: Metadata = {
  title: "Mandate — Financial Control Plane for AI Agents & Razorpay",
  description:
    "Production authorization control plane, deterministic policy engine, and MCP security gateway for autonomous AI agents operating on Razorpay.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#090d16] text-slate-100 antialiased selection:bg-blue-600 selection:text-white">
        <ToastProvider>
          <DashboardLayout>{children}</DashboardLayout>
        </ToastProvider>
      </body>
    </html>
  );
}
