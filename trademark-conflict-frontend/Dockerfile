# =========================================================

# Stage 1 — Build React application

# =========================================================

FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_OIDC_AUTHORITY
ARG VITE_OIDC_CLIENT_ID
ARG VITE_OIDC_SCOPE="openid profile email"
ARG VITE_API_BASE_URL=""
ENV VITE_OIDC_AUTHORITY=$VITE_OIDC_AUTHORITY
ENV VITE_OIDC_CLIENT_ID=$VITE_OIDC_CLIENT_ID
ENV VITE_OIDC_SCOPE=$VITE_OIDC_SCOPE
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build

# =========================================================

# Stage 2 — Serve with NGINX

# =========================================================

FROM nginx:alpine

RUN rm -rf /usr/share/nginx/html/*

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]