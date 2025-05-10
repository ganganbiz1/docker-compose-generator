FROM node:14-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

ENV API_URL=https://api.example.com
ENV DEBUG=false

EXPOSE 80
EXPOSE 443

VOLUME ["/var/log/nginx", "/etc/nginx/ssl"]

HEALTHCHECK --interval=30s --timeout=3s CMD wget -q --spider http://localhost:80/ || exit 1

ENTRYPOINT ["nginx", "-g", "daemon off;"] 