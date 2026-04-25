################
# Stage 1: build
################
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# В production VITE_API_URL пустой → fetch идёт на тот же origin,
# а nginx в этом же контейнере проксирует /api/* на backend.
ENV VITE_API_URL=""
ENV VITE_DEV_USER_ID=""

RUN npm run build


################
# Stage 2: serve
################
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
