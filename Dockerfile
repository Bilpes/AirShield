FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS builder
WORKDIR /app
ARG NEXT_PUBLIC_EDGE_WS_URL=
ARG AIRSHIELD_ALLOW_INSECURE_LOCAL_EDGE=false
# Same-origin /edge/* proxy upstream; rewrites are resolved at build time, so
# full-stack builds must point this at the edge service container.
ARG EDGE_UPSTREAM=http://127.0.0.1:8001
ENV NEXT_PUBLIC_EDGE_WS_URL=$NEXT_PUBLIC_EDGE_WS_URL \
    AIRSHIELD_ALLOW_INSECURE_LOCAL_EDGE=$AIRSHIELD_ALLOW_INSECURE_LOCAL_EDGE \
    EDGE_UPSTREAM=$EDGE_UPSTREAM
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=4174 HOSTNAME=0.0.0.0
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 4174
CMD ["node", "server.js"]
