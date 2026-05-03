# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o scheduler ./cmd/scheduler/

# Runtime stage
FROM alpine:3.18

# Install docker-cli for running python pipeline
RUN apk add --no-cache docker-cli

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/scheduler .

# Create logs directory
RUN mkdir -p logs

EXPOSE 8080

# Default environment variables
ENV PIPELINE_DIR=/app/pipeline
ENV SCHEDULER_PORT=8080
ENV SCHEDULER_CRON="0 10 * * 1-5"

# Run the scheduler
CMD ["./scheduler"]
