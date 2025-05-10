# Build stage for Go application
FROM golang:1.18-alpine AS builder

# Set build arguments
ARG APP_VERSION=1.0.0
ARG BUILD_DATE=unknown

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache git ca-certificates && \
    update-ca-certificates

# Copy Go module files and download dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build the application with version info
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-X main.Version=${APP_VERSION} -X main.BuildDate=${BUILD_DATE}" -o /app/server ./cmd/server

# Create a minimal runtime image
FROM alpine:3.16

# Create a non-root user to run the application
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Set environment variables
ENV APP_ENV=production
ENV LOG_LEVEL=info
ENV SERVER_PORT=8080
ENV DB_HOST=postgres
ENV DB_PORT=5432
ENV DB_NAME=appdb
ENV DB_USER=dbuser
ENV ENABLE_METRICS=true

# Copy the binary from the builder stage
COPY --from=builder /app/server /usr/local/bin/server
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy config files
COPY ./config/config.yaml /etc/app/config.yaml

# Create directories for data and logs
RUN mkdir -p /var/lib/app/data /var/log/app && \
    chown -R appuser:appgroup /var/lib/app /var/log/app /etc/app

# Expose ports
EXPOSE 8080
EXPOSE 8081/tcp
EXPOSE 9090/udp

# Define volumes
VOLUME ["/var/lib/app/data", "/var/log/app", "/etc/app/custom-config"]

# Switch to non-root user
USER appuser

# Set healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -q --spider http://localhost:8080/health || exit 1

# Set entrypoint and command
ENTRYPOINT ["/usr/local/bin/server"]
CMD ["--config", "/etc/app/config.yaml", "--verbose"] 