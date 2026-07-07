# Frontend: сборка статики (Vite) + Caddy (раздача статики и reverse-proxy /api).

# --- Сборка ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Пусто → относительные пути /api/..., которые Caddy проксирует на backend.
ARG VITE_BACKEND_URL=""
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
RUN npm run build

# --- Раздача + reverse-proxy ---
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
