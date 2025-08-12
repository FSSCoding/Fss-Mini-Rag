#!/bin/bash
# FSS-Mini-RAG Runner Script
# Quick launcher for common operations

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if installed
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo -e "${YELLOW}FSS-Mini-RAG not installed.${NC}"
    echo "Run: ./install_mini_rag.sh"
    exit 1
fi

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo -e "${CYAN}${BOLD}FSS-Mini-RAG Quick Runner${NC}"
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./run_mini_rag.sh index <project_path>     # Index a project"
    echo "  ./run_mini_rag.sh search <project_path> <query>  # Search project"
    echo "  ./run_mini_rag.sh status <project_path>   # Check index status"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  ./run_mini_rag.sh index ~/my-project"
    echo "  ./run_mini_rag.sh search ~/my-project \"user authentication\""
    echo "  ./run_mini_rag.sh status ~/my-project"
    echo ""
    echo -e "${BOLD}Advanced:${NC}"
    echo "  ./rag-mini                    # Full CLI with all options"
    echo "  ./rag-mini-enhanced          # Enhanced CLI with smart features"
    echo ""
    exit 0
fi

# Activate virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Route to appropriate command
case "$1" in
    "index")
        if [ -z "$2" ]; then
            echo -e "${YELLOW}Usage: ./run_mini_rag.sh index <project_path>${NC}"
            exit 1
        fi
        echo -e "${BLUE}Indexing project: $2${NC}"
        "$SCRIPT_DIR/rag-mini" index "$2"
        ;;
    "search")
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo -e "${YELLOW}Usage: ./run_mini_rag.sh search <project_path> <query>${NC}"
            exit 1
        fi
        echo -e "${BLUE}Searching project: $2${NC}"
        echo -e "${BLUE}Query: $3${NC}"
        "$SCRIPT_DIR/rag-mini" search "$2" "$3"
        ;;
    "status")
        if [ -z "$2" ]; then
            echo -e "${YELLOW}Usage: ./run_mini_rag.sh status <project_path>${NC}"
            exit 1
        fi
        echo -e "${BLUE}Checking status: $2${NC}"
        "$SCRIPT_DIR/rag-mini" status "$2"
        ;;
    *)
        echo -e "${YELLOW}Unknown command: $1${NC}"
        echo "Use ./run_mini_rag.sh (no arguments) to see usage."
        exit 1
        ;;
esac