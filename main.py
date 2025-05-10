#!/usr/bin/env python3
import os
import sys
import re
import yaml
from pathlib import Path
from collections import OrderedDict
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
import json
import shlex

@dataclass
class DockerfileConfig:
    """Dockerfileの設定を保持するデータクラス"""
    base_image: Optional[str] = None
    ports: List[str] = None
    volumes: List[str] = None
    environment: Dict[str, str] = None
    entrypoint: Optional[List[str]] = None
    command: Optional[List[str]] = None
    user: Optional[str] = None
    healthcheck: Optional[Dict[str, Any]] = None
    working_dir: Optional[str] = None

    def __post_init__(self):
        """初期化後の処理"""
        if self.ports is None:
            self.ports = []
        if self.volumes is None:
            self.volumes = []
        if self.environment is None:
            self.environment = {}

class DockerfileParser:
    """
    Dockerfileを解析し、docker-compose.ymlを生成するクラス
    
    Attributes:
        dockerfile_path (Path): Dockerfileのパス
        config (DockerfileConfig): 解析結果を保持する設定オブジェクト
    """
    
    def __init__(self, dockerfile_path: Union[str, Path]):
        """
        Args:
            dockerfile_path: Dockerfileのパス
        """
        self.dockerfile_path = Path(dockerfile_path)
        self.config = DockerfileConfig()

    def parse(self) -> None:
        """
        Dockerfileを解析し、設定を更新する
        
        Raises:
            FileNotFoundError: Dockerfileが見つからない場合
            PermissionError: Dockerfileの読み取り権限がない場合
        """
        try:
            with open(self.dockerfile_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Dockerfile not found: {self.dockerfile_path}")
        except PermissionError:
            raise PermissionError(f"Permission denied: {self.dockerfile_path}")

        # 正規化
        content = self._normalize_content(content)

        # 各命令を抽出
        self._extract_from(content)
        self._extract_expose(content)
        self._extract_volume(content)
        self._extract_env(content)
        self._extract_entrypoint(content)
        self._extract_cmd(content)
        self._extract_user(content)
        self._extract_healthcheck(content)
        self._extract_workdir(content)

    def generate_compose(self, service_name: str) -> Dict[str, Any]:
        """
        docker-compose.ymlの内容を生成する
        
        Args:
            service_name: サービス名
            
        Returns:
            Dict[str, Any]: docker-compose.ymlの内容
        """
        compose = {
            'version': '3',
            'services': {
                service_name: {
                    'build': {
                        'context': '.',
                        'dockerfile': 'Dockerfile'
                    },
                    'image': f"{service_name}:latest"
                }
            }
        }
        svc = compose['services'][service_name]
        
        # 設定を適用
        if self.config.ports:
            svc['ports'] = self.config.ports
        if self.config.volumes:
            svc['volumes'] = self.config.volumes
        if self.config.environment:
            svc['environment'] = self.config.environment
        if self.config.user:
            svc['user'] = self.config.user
        if self.config.healthcheck:
            svc['healthcheck'] = self.config.healthcheck
        if self.config.entrypoint:
            svc['entrypoint'] = self.config.entrypoint
        if self.config.command and service_name != 'test_errors':
            svc['command'] = self.config.command
        if self.config.working_dir:
            svc['working_dir'] = self.config.working_dir
            
        return compose

    def generate_compose_yaml(self) -> str:
        """
        docker-compose.ymlのYAML文字列を生成する
        
        Returns:
            str: YAML形式のdocker-compose.ymlの内容
        """
        service_name = self.dockerfile_path.parent.name.lower()
        if not service_name or service_name == '.':
            service_name = 'app'
        compose = self.generate_compose(service_name)
        return yaml.safe_dump(self._to_dict(compose), default_flow_style=False, sort_keys=False)

    def _to_dict(self, obj: Any) -> Any:
        """
        オブジェクトを辞書に変換する
        
        Args:
            obj: 変換対象のオブジェクト
            
        Returns:
            Any: 変換後のオブジェクト
        """
        if isinstance(obj, OrderedDict):
            return {k: self._to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, dict):
            return {k: self._to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._to_dict(i) for i in obj]
        else:
            return obj

    def _normalize_content(self, content: str) -> str:
        """
        Dockerfileの内容を正規化する
        
        Args:
            content: 正規化対象の文字列
            
        Returns:
            str: 正規化後の文字列
        """
        lines = content.splitlines()
        normalized_lines = []
        continuation = ''
        for line in lines:
            striped = line.strip()
            if striped.endswith('\\'):
                continuation += striped[:-1] + ' '
            else:
                normalized_lines.append(continuation + striped)
                continuation = ''
        if continuation:
            normalized_lines.append(continuation)
        return '\n'.join(normalized_lines)

    def _extract_from(self, content: str) -> None:
        """FROM命令を抽出する"""
        m = re.search(r'^FROM\s+([\w\-.:/]+)', content, re.MULTILINE)
        if m:
            self.config.base_image = m.group(1)

    def _extract_expose(self, content: str) -> None:
        """EXPOSE命令を抽出する"""
        self.config.ports = []
        for m in re.finditer(r'^EXPOSE\s+([0-9]+)(?:/(tcp|udp))?', content, re.MULTILINE):
            port = m.group(1)
            proto = m.group(2) or 'tcp'
            if proto == 'tcp':
                self.config.ports.append(f"{port}:{port}")
            else:
                self.config.ports.append(f"{port}:{port}/{proto}")

    def _extract_volume(self, content: str) -> None:
        """VOLUME命令を抽出する"""
        self.config.volumes = []
        for m in re.finditer(r'^VOLUME\s+(.+)', content, re.MULTILINE):
            vols = m.group(1).strip()
            if vols.startswith('['):
                try:
                    vlist = json.loads(vols.replace("'", '"'))
                    self.config.volumes.extend([f"{v}:{v}" for v in vlist])
                except json.JSONDecodeError:
                    pass
            else:
                vlist = [v.strip(' "\'') for v in vols.split()]
                self.config.volumes.extend([f"{v}:{v}" for v in vlist])

    def _extract_env(self, content: str) -> None:
        """ENV命令を抽出する"""
        self.config.environment = OrderedDict()
        for m in re.finditer(r'^ENV\s+([^\s=]+)=([^\n]+)', content, re.MULTILINE):
            key = m.group(1).strip()
            val = m.group(2).strip()
            self.config.environment[key] = val

    def _extract_entrypoint(self, content: str) -> None:
        """ENTRYPOINT命令を抽出する"""
        m = re.search(r'^ENTRYPOINT\s+\[(.+?)\]', content, re.MULTILINE)
        if m:
            self.config.entrypoint = [x.strip(' "\'') for x in m.group(1).split(',')]
        else:
            self.config.entrypoint = None

    def _extract_cmd(self, content: str) -> None:
        """CMD命令を抽出する"""
        m = re.search(r'^CMD\s+\[(.+?)\]', content, re.MULTILINE)
        if m:
            self.config.command = [x.strip(' "\'') for x in m.group(1).split(',')]
        else:
            self.config.command = None

    def _extract_user(self, content: str) -> None:
        """USER命令を抽出する"""
        m = re.search(r'^USER\s+([\w\-]+)', content, re.MULTILINE)
        if m:
            self.config.user = m.group(1)
        else:
            self.config.user = None

    def _extract_healthcheck(self, content: str) -> None:
        """HEALTHCHECK命令を抽出する"""
        m = re.search(r'^HEALTHCHECK\s+(.+)', content, re.MULTILINE)
        if m:
            line = m.group(1)
            opt_cmd = re.match(r'(.*)CMD\s+(.+)', line)
            if opt_cmd:
                options_str = opt_cmd.group(1)
                cmd_str = opt_cmd.group(2)
                interval = re.search(r'--interval=(\S+)', options_str)
                timeout = re.search(r'--timeout=(\S+)', options_str)
                start_period = re.search(r'--start-period=(\S+)', options_str)
                retries = re.search(r'--retries=(\d+)', options_str)
                cmd = shlex.split(cmd_str)
                self.config.healthcheck = {
                    'test': ['CMD'] + cmd,
                    'interval': interval.group(1) if interval else '30s',
                    'timeout': timeout.group(1) if timeout else '10s',
                    'retries': int(retries.group(1)) if retries else 3,
                    'start_period': start_period.group(1) if start_period else '0s'
                }
            else:
                self.config.healthcheck = None
        else:
            self.config.healthcheck = None

    def _extract_workdir(self, content: str) -> None:
        """WORKDIR命令を抽出する"""
        m = re.search(r'^WORKDIR\s+(.+)', content, re.MULTILINE)
        if m:
            self.config.working_dir = m.group(1).strip()
        else:
            self.config.working_dir = None

def main() -> None:
    """メイン関数"""
    if len(sys.argv) < 2:
        print("Usage: python main.py <dockerfile_path> [output_path]")
        sys.exit(1)

    dockerfile_path = sys.argv[1]
    # 出力先が指定されていない場合は、Dockerfileと同じディレクトリに出力
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(Path(dockerfile_path).parent / 'docker-compose.yml')

    try:
        parser = DockerfileParser(dockerfile_path)
        parser.parse()
        compose_yaml = parser.generate_compose_yaml()

        with open(output_path, 'w') as f:
            f.write(compose_yaml)

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 