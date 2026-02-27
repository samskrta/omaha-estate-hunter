/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'picturescdn.estatesales.net',
      },
    ],
  },
}

module.exports = nextConfig
