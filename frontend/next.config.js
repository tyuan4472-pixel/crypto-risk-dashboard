/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  optimizeFonts: false,  // 跳过 Google Fonts 下载，避免国内构建卡死
};

module.exports = nextConfig;
