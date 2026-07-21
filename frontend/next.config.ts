import type { NextConfig } from "next";
import withSerwistInit from "@serwist/next";

const withSerwist = withSerwistInit({
  swSrc: "sw.ts",
  swDest: "public/sw.js",
  disable: process.env.NODE_ENV === "development",
});

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Prefer config redirect — `redirect()` in app/page.tsx was 500 on Netlify SSR.
  async redirects() {
    return [{ source: "/", destination: "/contacts", permanent: false }];
  },
};

export default withSerwist(nextConfig);
