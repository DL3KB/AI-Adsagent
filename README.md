# AdsAgent – Google Ads AI Analysis

A web agent that retrieves Google Ads campaign data and analyzes it with Gemini AI to deliver actionable recommendations.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 React Frontend                  │
│  Dashboard │ AI Analysis │ AI Chat              │
│  (Recharts, Lucide, React Query)                │
└────────────────────┬────────────────────────────┘
                     │ REST API
┌────────────────────┴────────────────────────────┐
│                 FastAPI Backend                 │
│  /api/campaigns │ /api/analyze │ /api/chat      │
├───────────┬─────────────────────┬───────────────┤
│ Google Ads│                     │  Gemini AI    │
│    SDK    │      SQLite DB      │    (Flash)    │
└───────────┴─────────────────────┴───────────────┘
```

## Features

- **Dashboard** – Overview of all Search Campaigns with KPIs (Cost, Clicks, CTR, CPC, Conversions)
- **Charts** – Visual breakdown: cost distribution, clicks vs. conversions
- **AI Analysis** – Gemini AI analyzes your data and provides prioritized recommendations
- **AI Chat** – Ask questions about your campaign data in a conversational format
- **Change Proposals** – AI-generated actionable proposals you can apply or reject directly
- **Search Terms Report** – Inspect search term performance, filter wasted spend
- **Device & Location Segmentation** – Performance breakdown by device type and geographic location
- **Period Comparison** – Compare current vs. previous period metrics with change indicators
- **CSV Export** – Export campaigns, search terms, and analysis results as CSV
- **Change Log** – Full audit trail of all actions taken through the app
- **SQLite Caching** – 15-minute cache to reduce API calls
- **Dark Mode** – Modern, dark UI

## Prerequisites

- Python 3.11+
- Node.js 18+
- Google Ads API credentials (Developer Token, OAuth2)
- Gemini API Key

## Setup

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Enter your API keys in .env!

# Start server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 3. Open the App

- **Frontend:** http://localhost:5173
- **Backend API Docs:** http://localhost:8000/docs

## .env Configuration

```env
# Google Ads API
GOOGLE_ADS_DEVELOPER_TOKEN=your-developer-token
GOOGLE_ADS_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your-client-secret
GOOGLE_ADS_REFRESH_TOKEN=your-refresh-token
GOOGLE_ADS_CUSTOMER_ID=your-customer-id-without-dashes

# Optional: MCC (Manager Account)
GOOGLE_ADS_LOGIN_CUSTOMER_ID=your-mcc-customer-id-without-dashes

# Gemini API
GEMINI_API_KEY=your-gemini-api-key
```

### Obtaining a Google Ads API Token

1. **Developer Token** → [Google Ads API Center](https://ads.google.com/aw/apicenter)
2. **OAuth2 Credentials** → [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
3. **Refresh Token** → Generate with the `google-ads` SDK:
   ```bash
   python -m google.ads.googleads.client --generate_refresh_token
   ```

### Obtaining a Gemini API Key

→ [Google AI Studio](https://aistudio.google.com/apikey)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/campaigns` | All Search Campaigns with metrics |
| GET | `/api/campaigns/{id}/ad-groups` | Ad Groups for a campaign |
| GET | `/api/keywords` | Keywords with Quality Scores |
| GET | `/api/search-terms` | Search terms report |
| GET | `/api/segmentation` | Device & location performance |
| GET | `/api/comparison` | Period-over-period comparison |
| GET | `/api/audit-log` | Change log entries |
| GET | `/api/export/campaigns/csv` | Export campaigns as CSV |
| GET | `/api/export/search-terms/csv` | Export search terms as CSV |
| GET | `/api/export/analysis/csv` | Export analysis as CSV |
| POST | `/api/analyze` | AI analysis of campaign data |
| POST | `/api/chat` | Chat about campaign data |
| POST | `/api/cache/clear` | Clear the API cache |
| GET | `/api/proposals` | Get AI-generated proposals |
| POST | `/api/proposals/apply` | Apply selected proposals |
| POST | `/api/proposals/{id}/reject` | Reject a proposal |
| GET | `/api/health` | Health check |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, FastAPI |
| Frontend | React, TypeScript, Vite |
| AI | Google Gemini 2.0 Flash |
| Ads API | google-ads Python SDK |
| Database | SQLite (caching & audit log) |
| Charts | Recharts |
| Icons | Lucide React |
| State | TanStack React Query |
| HTTP | Axios |
