# 다단계: node 로 정적 빌드 → nginx 로 서빙(앱 셸). gateway/worker 처럼 서버에서 빌드(sha 태그).
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
