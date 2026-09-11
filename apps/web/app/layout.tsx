import type { Metadata } from "next";
import "./globals.css";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { ToastProvider } from "@/components/common/Toast";

export const metadata: Metadata = {
  title: "Mandate — Financial Control Plane for AI Agents",
  description:
    "A deterministic authorization and control plane for AI agents operating through Razorpay APIs and MCP.",
  metadataBase: new URL("https://mandate-razorpay-control-plane.vercel.app"),
  openGraph: {
    title: "Mandate — Financial Control Plane for AI Agents",
    description:
      "A deterministic authorization and control plane for AI agents operating through Razorpay APIs and MCP.",
    url: "https://mandate-razorpay-control-plane.vercel.app/",
    siteName: "Mandate",
    images: [
      {
        url: "https://mandate-razorpay-control-plane.vercel.app/og-image.png",
        width: 1200,
        height: 627,
        alt: "Mandate — Financial Control Plane for AI Agents",
      },
    ],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Mandate — Financial Control Plane for AI Agents",
    description:
      "A deterministic authorization and control plane for AI agents operating through Razorpay APIs and MCP.",
    images: ["https://mandate-razorpay-control-plane.vercel.app/og-image.png"],
  },
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
