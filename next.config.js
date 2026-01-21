/** @type {import('next').NextConfig} */
const nextConfig = {
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
