# Docker Compose Generator

A command-line tool that automatically generates Docker Compose files from Dockerfiles.

## Features

- Analyzes Dockerfiles to extract configuration details
- Generates docker-compose.yml with appropriate services
- Identifies exposed ports and maps them automatically
- Detects volumes from VOLUME instructions
- Sets appropriate environment variables

## Usage

```
python main.py path/to/dockerfile [output_path]
```

If no output path is specified, the docker-compose.yml will be created in the same directory as the Dockerfile.

## Requirements

- Python 3.6+
- PyYAML
- Click 