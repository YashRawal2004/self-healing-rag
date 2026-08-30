import path from "node:path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Browser talks only to :3000 so the session cookie is first-party.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:5000/api/:path*",
      },
    ];
  },

  // Without this, Turbopack walks up looking for a lockfile, finds the stray one
  // in the home directory, and treats that as the project root — which makes it
  // watch every unrelated folder above this app.
  turbopack: {
    root: path.resolve(import.meta.dirname),
  },

  // Default is bottom-left, which sits right on top of the sidebar's Documents
  // button. Moved rather than disabled — it still surfaces compile errors.
  devIndicators: {
    position: "bottom-right",
  },
};

export default nextConfig;
