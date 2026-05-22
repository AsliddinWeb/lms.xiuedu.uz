# =============================================================================
# Frontend Dockerfile — multi-stage (dev | build | nginx prod)
# =============================================================================
ARG NODE_VERSION=20

# ---------- base ----------
FROM node:${NODE_VERSION}-alpine AS base
RUN corepack enable && corepack prepare pnpm@9.0.0 --activate
WORKDIR /app

# ---------- deps ----------
FROM base AS deps
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile=false

# ---------- dev ----------
FROM base AS dev
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 8201 8203
CMD ["pnpm", "dev:user", "--host", "0.0.0.0"]

# ---------- build (user) ----------
FROM deps AS build-user
# Production'da VITE_API_URL build-arg orqali kelishi mumkin (compose'da set bo'ladi).
# Vite import.meta.env.VITE_* ni build-time'da embed qiladi.
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}
COPY . .
RUN pnpm build:user

# ---------- build (admin) ----------
FROM deps AS build-admin
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}
COPY . .
RUN pnpm build:admin

# ---------- prod-user ----------
FROM nginx:1.25-alpine AS prod-user
COPY --from=build-user /app/dist-user /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# ---------- prod-admin ----------
FROM nginx:1.25-alpine AS prod-admin
COPY --from=build-admin /app/dist-admin /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
