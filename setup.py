from setuptools import setup

setup(
    name="docker-compose-generator",
    version="0.1.0",
    install_requires=[
        "PyYAML>=6.0",
        "Click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "docker-compose-generator=main:main",
        ],
    },
) 