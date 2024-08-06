import type { Metadata } from "next";
import Head from "next/head";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Fluxwell - Generate images with Flux for free",
  description: "Fluxwell generate A.I art for free",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <Head>
        <link rel="icon" href="/public/favicon.ico" />
        {/* You can also add other favicon formats or sizes if needed */}
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
      </Head>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
