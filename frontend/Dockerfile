FROM registry.cn-hangzhou.aliyuncs.com/library/node:20-alpine AS builder
WORKDIR /app

# npm 国内源
RUN npm config set registry https://registry.npmmirror.com

COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM registry.cn-hangzhou.aliyuncs.com/library/node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
