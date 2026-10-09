/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === 'production';
const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;

if (isProd && !backendUrl) {
  console.warn(
    '\n⚠️  [AI-Diagnoser] WARNING: Neither BACKEND_URL nor NEXT_PUBLIC_API_URL is configured in production. ' +
    'Configure BACKEND_URL in your Vercel environment variables to point to your FastAPI production host.\n'
  );
}

const targetBase = backendUrl ? backendUrl.replace(/\/$/, '') : 'http://127.0.0.1:8000';

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    if (isProd && !backendUrl) {
      // Do not silently forward to localhost in production
      return [];
    }
    return [
      {
        source: '/api/v1/:path*',
        destination: `${targetBase}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
