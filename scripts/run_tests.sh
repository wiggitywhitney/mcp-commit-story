#!/bin/bash
# Test runner script for MCP Journal
# This script activates the virtual environment and runs pytest

set -e  # Exit on any error

# Print with colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

VENV_PATH=".venv"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_PATH.${NC}"
    echo -e "${YELLOW}Please run scripts/setup_test_env.sh first.${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate"

# Run pytest with arguments
echo -e "${GREEN}Running tests...${NC}"
python -m pytest "$@"
TEST_EXIT_CODE=$?

# Echo the test results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Tests failed with exit code $TEST_EXIT_CODE${NC}"
fi

# Return the pytest exit code
exit $TEST_EXIT_CODE 