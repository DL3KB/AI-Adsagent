#!/bin/bash
# ============================================================
# AdsAgent - First-time setup
# Creates venv, installs dependencies, scaffolds .env
# ============================================================

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AdsAgent — Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# ---- Backend ----
echo -e "\n${YELLOW}[1/3] Setting up backend...${NC}"
cd "$ROOT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "  Creating Python virtual environment..."
    python3 -m venv venv
else
    echo "  Virtual environment already exists."
fi

echo "  Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet
deactivate

# ---- Backend .env ----
echo -e "\n${YELLOW}[2/3] Checking backend/.env...${NC}"
if [ ! -f ".env" ]; then
    cat > .env <<'ENVFILE'
# Google Ads API
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=
GOOGLE_ADS_REFRESH_TOKEN=
GOOGLE_ADS_CUSTOMER_ID=          # without dashes
GOOGLE_ADS_LOGIN_CUSTOMER_ID=    # MCC account ID without dashes

# Gemini API
GEMINI_API_KEY=

# App
APP_ENV=development
DATABASE_URL=sqlite+aiosqlite:///./adsagent.db
ENVFILE
    echo -e "  ${RED}Created backend/.env — please fill in your API credentials before starting.${NC}"
else
    echo "  .env already exists."
fi

# ---- Frontend ----
echo -e "\n${YELLOW}[3/3] Setting up frontend...${NC}"
cd "$ROOT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    echo "  Installing Node.js dependencies..."
    npm install --silent
else
    echo "  node_modules already exists. Run 'npm install' to update."
fi

# ---- Done ----
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "  Next steps:"
echo "    1. Fill in backend/.env with your API credentials (if not done)"
echo "    2. Run ./start.sh to launch the app"
echo ""
