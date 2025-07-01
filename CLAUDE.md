# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a comprehensive specification for an AI-powered autonomous code review agent system, with specific focus on C language code analysis. The project defines a LangChain-based architecture that can perform complete, autonomous code reviews using file-based coding standards input.

## Architecture Overview

The system is designed around several key components:

- **LangChain Integration**: Uses `langchain.agents`, `ConversationBufferWindowMemory`, and structured chat agents for autonomous operation
- **File-Based Standards Input**: Supports PDF, Markdown (.md), and Text (.txt) files for coding standards specification  
- **Agent-Based Architecture**: Autonomous operation with planning, execution, and validation cycles
- **C Language Specialization**: Specific focus on C language code analysis with memory management, security, and performance checks

## Key Documentation

### Main Specification Document
The primary specification is located at `docs/ai_agent_code_reviewer_prompt.md`. This document contains:

- Complete agent architecture with Python class definitions
- LangChain tool implementations for code analysis
- File-based setup system replacing QA-format configuration
- Structured output formats (JSON, Markdown, HTML)
- Local Git integration for commit analysis
- Comprehensive C language analysis tools

## Setup and Usage Patterns

### Initial Setup (One-time)
```bash
# Setup with coding standards files
python agent_reviewer.py setup --standards-files "./docs/coding_standards.pdf,./docs/team_guidelines.md"

# Or using configuration file
python agent_reviewer.py setup --config "./setup_config.yaml"
```

### Regular Usage
```bash
# Review a specific commit
python agent_reviewer.py review abc123

# Review with specific file format output
python agent_reviewer.py review abc123 --output all
```

## Configuration System

The agent uses file-based configuration supporting:

- **PDF files**: For comprehensive coding standards documents
- **Markdown files**: For structured guidelines and checklists  
- **Text files**: For simple rule lists and conventions

Configuration files are processed using:
- `PyPDFLoader` for PDF extraction
- `UnstructuredMarkdownLoader` for Markdown processing
- `TextLoader` for plain text files
- `RecursiveCharacterTextSplitter` for chunking
- `FAISS` vectorstore for efficient retrieval

## Agent Tools

The system implements specialized LangChain tools:

- `analyze_code_structure`: Code structure and complexity analysis
- `security_scan`: Security vulnerability detection
- `check_coding_standards`: Standards compliance checking using uploaded documents
- `performance_analysis`: Performance optimization opportunities
- `dependency_analysis`: File dependency relationship analysis

## Output Formats

The agent generates multiple report formats:
- **JSON**: Structured data for programmatic processing
- **Markdown**: Developer-friendly reports with code examples
- **HTML**: Visual reports for web browsers
- **Text**: Console-friendly summaries

## Development Notes

- This is primarily a specification/design document rather than implemented code
- The document demonstrates integration of LangChain components with autonomous agent patterns
- Focus on C language code review with specialized analysis tools
- Designed for complete local operation without external API dependencies
- Emphasizes file-based configuration over interactive setup