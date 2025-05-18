#!/bin/bash
# Setup script for MCP Journal test environment
# This script creates a virtual environment and installs all development dependencies

set -e  # Exit on any error

VENV_PATH=".venv"
PROJ_ROOT=$(pwd)

# Print with colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up test environment for MCP Journal...${NC}"

# Check if Python 3.9+ is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found. Please install Python 3.9 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo -e "${RED}Error: Python 3.9 or higher is required. Found Python $PYTHON_VERSION.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Creating virtual environment at $VENV_PATH...${NC}"
    python3 -m venv "$VENV_PATH"
else
    echo -e "${YELLOW}Using existing virtual environment at $VENV_PATH...${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate"

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install development dependencies
echo -e "${YELLOW}Installing development dependencies...${NC}"
pip install -e ".[dev]"

# Verify pytest is installed and working
echo -e "${YELLOW}Verifying pytest installation...${NC}"
if pytest --version; then
    echo -e "${GREEN}Pytest is installed and working.${NC}"
else
    echo -e "${RED}Failed to run pytest. Check your installation.${NC}"
    exit 1
fi

# Create a simple test runner script
echo -e "${YELLOW}Creating test runner script...${NC}"
cat > scripts/run_tests.sh << EOF
#!/bin/bash
# Test runner script for MCP Journal
source .venv/bin/activate
python -m pytest \$@
EOF
chmod +x scripts/run_tests.sh

echo -e "${GREEN}Test environment setup complete!${NC}"
echo -e "${GREEN}You can run tests with: ./scripts/run_tests.sh${NC}"
echo -e "${GREEN}Or activate the virtual environment with: source .venv/bin/activate${NC}"

# Verification message
echo ""
echo -e "${YELLOW}Verifying Task 1 tests...${NC}"
echo -e "Run: ./scripts/run_tests.sh tests/unit/test_structure.py tests/unit/test_imports.py"
echo -e "All Task 1 tests must pass before marking Task 1 as complete." 