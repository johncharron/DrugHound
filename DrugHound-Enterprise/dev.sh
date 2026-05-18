#!/bin/bash
# DrugHound Enterprise - Development Workflow

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

case "$1" in
    "test")
        echo -e "${BLUE}Running tests...${NC}"
        python3 tests/test_suite.py
        ;;
    
    "quick")
        echo -e "${BLUE}Quick local test...${NC}"
        python3 -c "
import re
patterns = [r'([A-Z]{2,}[0-9]{3,})', r'([A-Z]{2,}-[0-9]+)']
test = 'BFKB8488 and AZD9291'
found = []
for p in patterns:
    found.extend(re.findall(p, test))
print('Found:', found)
assert 'BFKB8488' in found, 'Drug extraction failed'
print('✓ Quick test passed')
"
        ;;
    
    "status")
        echo -e "${BLUE}Git Status:${NC}"
        git status --short 2>/dev/null || echo "Not a git repo yet"
        echo ""
        echo -e "${BLUE}Last commit:${NC}"
        git log -1 --oneline 2>/dev/null || echo "No commits yet"
        ;;
    
    "init")
        echo -e "${BLUE}Initializing git...${NC}"
        git init
        git add app_final_working.py algorithms/ templates/ 2>/dev/null
        git commit -m "BASELINE: Working version"
        git tag v1.0-working
        echo -e "${GREEN}✓ Git initialized with working version tagged${NC}"
        ;;
    
    *)
        echo "DrugHound Enterprise Commands"
        echo "============================"
        echo "  ./dev.sh test   - Run full test suite"
        echo "  ./dev.sh quick  - Run quick local test"
        echo "  ./dev.sh status - Show git status"
        echo "  ./dev.sh init   - Initialize git (first time)"
        echo ""
        echo "Example workflow:"
        echo "  1. Make code changes"
        echo "  2. ./dev.sh test"
        echo "  3. git add . && git commit -m 'message'"
        ;;
esac
