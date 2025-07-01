"""
C言語専用AIエージェント型コードレビューツール
セットアップスクリプト
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="c-agent-reviewer",
    version="1.0.0",
    author="AI Code Review Team",
    description="C言語専用AIエージェント型コードレビューツール",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(include=['src', 'src.*']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "c-agent-reviewer=c_agent_reviewer:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.yaml", "*.json"],
    },
)