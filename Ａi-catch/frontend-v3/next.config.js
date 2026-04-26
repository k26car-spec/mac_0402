/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,

    // Docker 部署支援
    output: 'standalone',

    // 環境變量
    env: {
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
        NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
    },

    // 圖片優化配置
    images: {
        domains: ['localhost'],
        unoptimized: true, // Docker 環境下建議關閉優化
    },

    // 編譯配置
    typescript: {
        ignoreBuildErrors: true,
    },

    eslint: {
        ignoreDuringBuilds: true,
    },
}

module.exports = nextConfig
