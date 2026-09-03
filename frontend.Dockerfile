# Stage 1: Build the Vite application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./
RUN npm ci

# Copy source code
COPY frontend/ .

# Build the application
# Use VITE_API_URL if provided, else fallback to /api (for proxy routing)
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL:-/api}

RUN npm run build

# Stage 2: Serve with NGINX
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Add custom NGINX config for SPA routing and proxying
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
