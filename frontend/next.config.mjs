/** @type {import('next').NextConfig} */
// Permite aislar la compilación del recorrido UI de un servidor de desarrollo abierto.
const nextConfig = { distDir: process.env.NEXT_DIST_DIR || ".next" };

export default nextConfig;
