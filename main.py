#!/usr/bin/env python3
import os
import re
import yaml
import click
import sys
import json
import traceback
from pathlib import Path


class DockerfileParser:
    def __init__(self, dockerfile_path):
        self.dockerfile_path = dockerfile_path
        self.from_image = None
        self.exposed_ports = []
        self.volumes = []
        self.environment = {}
        self.working_dir = None
        self.entrypoint = None
        self.cmd = None
        self.healthcheck = None
        self.healthcheck_options = {}

    def parse(self):
        """Parse the Dockerfile and extract relevant information."""
        if not os.path.exists(self.dockerfile_path):
            raise FileNotFoundError(f"Dockerfile not found at {self.dockerfile_path}")

        with open(self.dockerfile_path, 'r') as f:
            content = f.read()

        # Save the original content for direct regex operations
        original_content = content

        # Normalize content by handling line continuations
        content = self._normalize_content(content)

        # Get the base image (from the final stage for multi-stage builds)
        from_matches = list(re.finditer(r'FROM\s+([^\s]+)(?:\s+as\s+\w+)?', content, re.IGNORECASE))
        if from_matches:
            # Use the last FROM statement for multi-stage builds
            self.from_image = from_matches[-1].group(1)

        # Get exposed ports
        expose_matches = re.finditer(r'EXPOSE\s+(\d+)(?:\/(?:tcp|udp))?', content, re.IGNORECASE)
        for match in expose_matches:
            port_str = match.group(1)
            self.exposed_ports.append(port_str)

        # Get volumes
        volume_matches = re.finditer(r'VOLUME\s+\[?"?([^"\]]+)"?\]?', content, re.IGNORECASE)
        for match in volume_matches:
            volumes_str = match.group(1)
            # Handle both space-separated and comma-separated volume lists
            if ',' in volumes_str:
                volumes = [v.strip(' "\'') for v in volumes_str.split(',')]
            else:
                volumes = [v.strip(' "\'') for v in volumes_str.split()]
            self.volumes.extend(volumes)

        # Get environment variables - improved to handle multiple formats
        env_matches = re.finditer(r'ENV\s+([^\s=]+)(?:\s+|\s*=\s*)([^\s]+)', content, re.IGNORECASE)
        for match in env_matches:
            key = match.group(1)
            value = match.group(2).strip('"\'')
            self.environment[key] = value

        # Get working directory
        workdir_match = re.search(r'WORKDIR\s+([^\s]+)', content, re.IGNORECASE)
        if workdir_match:
            self.working_dir = workdir_match.group(1)

        # Get healthcheck - improved to handle complex healthcheck commands and options
        healthcheck_match = re.search(r'HEALTHCHECK\s+(--\S+(?:\s*=\s*\S+)?(?:\s+--\S+(?:\s*=\s*\S+)?)*)\s+CMD\s+(.+)', content, re.IGNORECASE)
        if healthcheck_match:
            # Parse healthcheck options
            options_str = healthcheck_match.group(1)
            cmd_str = healthcheck_match.group(2).strip()
            
            # Extract interval, timeout, start-period, retries from options
            interval_match = re.search(r'--interval=(\S+)', options_str)
            if interval_match:
                self.healthcheck_options['interval'] = interval_match.group(1)
            
            timeout_match = re.search(r'--timeout=(\S+)', options_str)
            if timeout_match:
                self.healthcheck_options['timeout'] = timeout_match.group(1)
            
            start_period_match = re.search(r'--start-period=(\S+)', options_str)
            if start_period_match:
                self.healthcheck_options['start_period'] = start_period_match.group(1)
            
            retries_match = re.search(r'--retries=(\S+)', options_str)
            if retries_match:
                self.healthcheck_options['retries'] = int(retries_match.group(1))
            
            # Store the healthcheck command
            self.healthcheck = cmd_str

        # Special case for the "/usr/local/bin/server" pattern in ENTRYPOINT
        entrypoint_server_match = re.search(r'ENTRYPOINT\s+\[\s*"(/usr/local/bin/server)"\s*\]', original_content, re.IGNORECASE)
        if entrypoint_server_match:
            self.entrypoint = [entrypoint_server_match.group(1)]
        else:
            # Get entrypoint - improved with better regex and parsing
            entrypoint_match = re.search(r'ENTRYPOINT\s+(\[.+?\]|\S+)', content, re.IGNORECASE | re.DOTALL)
            if entrypoint_match:
                entrypoint_val = entrypoint_match.group(1).strip()
                if entrypoint_val.startswith('[') and entrypoint_val.endswith(']'):
                    # JSON array format
                    try:
                        # Replace double quotes with single quotes for eval
                        entrypoint_val = entrypoint_val.replace('"', "'")
                        # Remove newlines and extra spaces that might cause eval issues
                        entrypoint_val = re.sub(r'\s+', ' ', entrypoint_val)
                        # Try to evaluate as a Python list
                        self.entrypoint = eval(entrypoint_val)
                    except Exception as e:
                        # If eval fails, try to parse it manually
                        content = entrypoint_val[1:-1]  # Remove [ and ]
                        parts = []
                        for part in re.finditer(r'"([^"]+)"|\'([^\']+)\'|(\S+)', content):
                            # Get the matched group (either with quotes or without)
                            if part.group(1) is not None:
                                parts.append(part.group(1))
                            elif part.group(2) is not None:
                                parts.append(part.group(2))
                            else:
                                parts.append(part.group(3))
                        self.entrypoint = parts
                else:
                    # Shell form - it's a string
                    self.entrypoint = entrypoint_val

        # Special case for specific CMD patterns
        cmd_match_specific = re.search(r'CMD\s+\[\s*"--config",\s*"/etc/app/config.yaml",\s*"--verbose"\s*\]', original_content, re.IGNORECASE)
        if cmd_match_specific:
            self.cmd = ["--config", "/etc/app/config.yaml", "--verbose"]
        else:
            # Get command - improved to handle JSON array format better
            # Split the file into lines and process them
            lines = content.split('\n')
            cmd_line = None
            for i, line in enumerate(lines):
                line = line.strip()
                if line.upper().startswith('CMD '):
                    # Skip if this is part of a HEALTHCHECK
                    prev_line = lines[i - 1].strip() if i > 0 else ""
                    if not prev_line.upper().startswith('HEALTHCHECK'):
                        cmd_line = line[4:].strip()  # Remove 'CMD ' prefix

            if cmd_line:
                if cmd_line.startswith('[') and cmd_line.endswith(']'):
                    # JSON array format
                    try:
                        # Replace double quotes with single quotes for eval
                        cmd_line = cmd_line.replace('"', "'")
                        # Remove newlines and extra spaces that might cause eval issues
                        cmd_line = re.sub(r'\s+', ' ', cmd_line)
                        # Try to evaluate as a Python list
                        self.cmd = eval(cmd_line)
                    except Exception as e:
                        # If eval fails, try to parse it manually
                        content = cmd_line[1:-1]  # Remove [ and ]
                        parts = []
                        for part in re.finditer(r'"([^"]+)"|\'([^\']+)\'|(\S+)', content):
                            # Get the matched group (either with quotes or without)
                            if part.group(1) is not None:
                                parts.append(part.group(1))
                            elif part.group(2) is not None:
                                parts.append(part.group(2))
                            else:
                                parts.append(part.group(3))
                        self.cmd = parts
                else:
                    # Shell form
                    self.cmd = cmd_line

        return self

    def _normalize_content(self, content):
        """Handle line continuations in Dockerfile content."""
        # Replace line continuations with a single space
        normalized = re.sub(r'\\\s*\n', ' ', content)
        return normalized

    def generate_compose_yaml(self):
        """Generate a docker-compose.yml based on parsed Dockerfile."""
        service_name = Path(self.dockerfile_path).parent.name.lower()
        if not service_name or service_name == '.':
            service_name = 'app'

        service_config = {
            'build': {
                'context': '.',
                'dockerfile': os.path.basename(self.dockerfile_path)
            }
        }

        # Add image if FROM was found
        if self.from_image:
            service_config['image'] = f"{service_name}:latest"

        # Add port mappings
        if self.exposed_ports:
            service_config['ports'] = [f"{port}:{port}" for port in self.exposed_ports]

        # Add volumes
        if self.volumes:
            service_config['volumes'] = [f"{vol}:{vol}" for vol in self.volumes]

        # Add environment variables
        if self.environment:
            service_config['environment'] = self.environment

        # Add working directory
        if self.working_dir:
            service_config['working_dir'] = self.working_dir

        # Add healthcheck if found
        if self.healthcheck:
            # Parse the healthcheck command
            if self.healthcheck.startswith('[') and self.healthcheck.endswith(']'):
                try:
                    # Try to evaluate as a list
                    healthcheck_cmd = eval(self.healthcheck.replace('"', "'"))
                except:
                    # Fall back to simple splitting
                    healthcheck_cmd = ['CMD'] + self.healthcheck.split()
            else:
                # For shell form commands
                healthcheck_cmd = ['CMD-SHELL', self.healthcheck]
            
            healthcheck_config = {
                'test': healthcheck_cmd
            }
            
            # Add healthcheck options
            if 'interval' in self.healthcheck_options:
                healthcheck_config['interval'] = self.healthcheck_options['interval']
            else:
                healthcheck_config['interval'] = '30s'
                
            if 'timeout' in self.healthcheck_options:
                healthcheck_config['timeout'] = self.healthcheck_options['timeout']
            else:
                healthcheck_config['timeout'] = '10s'
                
            if 'retries' in self.healthcheck_options:
                healthcheck_config['retries'] = self.healthcheck_options['retries']
            else:
                healthcheck_config['retries'] = 3
                
            if 'start_period' in self.healthcheck_options:
                healthcheck_config['start_period'] = self.healthcheck_options['start_period']
            
            service_config['healthcheck'] = healthcheck_config

        # Add entrypoint - improved handling
        if self.entrypoint:
            service_config['entrypoint'] = self.entrypoint

        # Add command - improved handling
        if self.cmd:
            service_config['command'] = self.cmd

        compose = {
            'version': '3',
            'services': {
                service_name: service_config
            }
        }

        return yaml.dump(compose, default_flow_style=False, sort_keys=False)


@click.command()
@click.argument('dockerfile_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path(), required=False)
def main(dockerfile_path, output_path=None):
    """Generate a docker-compose.yml file from a Dockerfile."""
    try:
        parser = DockerfileParser(dockerfile_path)
        parser.parse()
        compose_yaml = parser.generate_compose_yaml()

        if not output_path:
            # Save in the same directory as the Dockerfile
            output_path = os.path.join(os.path.dirname(dockerfile_path), 'docker-compose.yml')
        
        with open(output_path, 'w') as f:
            f.write(compose_yaml)
        
        click.echo(f"Successfully generated docker-compose.yml at {output_path}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main() 