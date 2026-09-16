/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The API is a separate FastAPI process; nothing is proxied or rewritten here
  // so the backend URL stays explicit and reviewable.
  // Next 16 can generate agent rule files and a dev badge; both are disabled so
  // the repository and the screenshots contain only product output.
  agentRules: false,
  devIndicators: false,
};

export default nextConfig;
