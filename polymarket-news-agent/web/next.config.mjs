/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async redirects() {
    return [
      { source: "/how-it-works", destination: "/docs", permanent: true },
      { source: "/architecture", destination: "/docs", permanent: true },
    ]
  },
}

export default nextConfig
