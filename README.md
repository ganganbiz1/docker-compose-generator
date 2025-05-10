# Docker Compose Generator

A command-line tool that automatically generates Docker Compose files from Dockerfiles. This tool analyzes your Dockerfile and creates a corresponding `docker-compose.yml` file with all the necessary configurations.

## Features

- Analyzes Dockerfiles to extract configuration details
- Generates docker-compose.yml with appropriate services
- Identifies exposed ports and maps them automatically
- Detects volumes from VOLUME instructions
- Sets appropriate environment variables
- Supports multi-stage builds
- Handles healthchecks
- Preserves user configurations
- Maintains working directory settings

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ganganbiz1/docker-compose-generator.git
cd docker-compose-generator
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the tool:
```bash
pip install -e .
```

## Usage

```bash
# Generate docker-compose.yml in the same directory as Dockerfile
docker-compose-generator path/to/Dockerfile

# Specify custom output path
docker-compose-generator path/to/Dockerfile path/to/output/docker-compose.yml
```

### Example

Given a Dockerfile:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

ENV FLASK_APP=app.py
ENV FLASK_ENV=development

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0"]
```

The tool will generate:
```yaml
version: '3'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    image: app:latest
    ports:
      - "5000:5000"
    environment:
      FLASK_APP: app.py
      FLASK_ENV: development
    working_dir: /app
    command:
      - flask
      - run
      - --host=0.0.0.0
```

### Advanced Usage

The tool supports complex Dockerfiles with:
- Multi-stage builds
- Healthchecks
- Volume mounts
- User configurations
- Custom entrypoints

Example with a complex Dockerfile:
```dockerfile
# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Development

### Running Tests

```bash
python test/run_tests.py
```

## Requirements

- Python 3.10+
- PyYAML
- Click
