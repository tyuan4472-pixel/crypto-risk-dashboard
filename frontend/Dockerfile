# 国内构建用阿里云镜像，海外部署改回 node:20-alpine
FROM registry.cn-hangzhou.aliyuncs.com/library/node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM registry.cn-hangzhou.aliyuncs.com/library/node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
