# ==============================================================================
# Production Dockerfile for DEVA Intelligence Frontend (React + Vite SPA)
# Multi-stage build with Nginx Alpine
# ==============================================================================

FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ------------------------------------------------------------------------------
# Nginx Static Serving Stage
# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runner

COPY --from=builder /app/dist /usr/share/nginx/html

RUN cat << 'EOF' > /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml image/svg+xml;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Reverse proxy backend API and metrics
    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /metrics {
        proxy_pass http://api:8000/metrics;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}
EOF

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
