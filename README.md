# TRINETRA — See. Track. Understand.

TRINETRA is a full-stack SIH-style vehicle intelligence command center.

## What is included

- React + TypeScript + Vite frontend
- FastAPI backend
- PostgreSQL service for the local stack
- JWT demo authentication
- WebSocket live vehicle detection simulation
- Multi-factor vehicle matching
- Vehicle trajectory reconstruction
- Interactive GIS map
- Analytics and alerts
- Docker-based local development
- **One-container production deployment**: React is built and served by FastAPI
- Render Blueprint for a public HTTPS URL

> Current AI is deterministic **DEMO MODE**. It does not perform real-world facial/vehicle recognition or OCR. The matching layer is structured so real OCR, object detection and vehicle Re-ID can be integrated later.

## Demo credentials

Email: `admin@trinetra.local`  
Password: `Admin@123`

## Option A — Run locally in VS Code

Requirements:
- Docker Desktop
- VS Code

From the `TRINETRA` folder:

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:5173
- Backend docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

Stop:

```bash
docker compose down
```

## Option B — Give teachers a public link

The included `Dockerfile.production` builds the React frontend and serves it from FastAPI, so you only need one public web service.

### Recommended: Render

Render supports Docker web services and gives each web service a public `onrender.com` URL. Its Blueprint system can create interconnected services/databases from `render.yaml`. See the official docs:
- https://render.com/docs/web-services
- https://render.com/docs/docker
- https://render.com/docs/infrastructure-as-code

### Deploy steps

1. Create a GitHub repository named `TRINETRA`.
2. Upload/push the contents of this folder to GitHub.
3. Create an account at Render.
4. In Render choose **New → Blueprint**.
5. Connect your GitHub repository.
6. Render detects `render.yaml`.
7. Deploy the `trinetra` web service.
8. After deployment, Render provides a public HTTPS URL such as:
   `https://trinetra-xxxx.onrender.com`
9. Share that URL with teachers/judges.

### Important

The demo dataset is currently held in the backend process, so it is **demo persistence**, not production database persistence. The PostgreSQL service is included in the local Docker stack and the architecture is ready for the next persistence upgrade.

For a hackathon presentation, this public deployment is suitable for demonstrating the UI, API, live simulation, tracking flow and explainable AI matching.

## If you want a separate frontend/backend deployment

The frontend already supports:

```bash
VITE_API_URL=https://YOUR-BACKEND-URL
```

Then build:

```bash
npm run build
```

The WebSocket URL automatically switches to `wss://` when the site is served over HTTPS.

## Project structure

```text
TRINETRA/
├── backend/
│   ├── app/main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/main.tsx
│   ├── src/index.css
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── Dockerfile.production
├── render.yaml
└── README.md
```

## Local teacher demo

If internet is unavailable:

```bash
docker compose up --build
```

Then open `http://localhost:5173` on the teacher's machine.

## Production roadmap

For a real deployment, add:
- SQLAlchemy models + PostgreSQL persistence
- database migrations
- real user/role management
- real ALPR/OCR
- YOLO vehicle detection
- vehicle Re-ID embeddings
- object tracking
- real camera/video ingestion
- secure secrets management
- audit logs
- rate limiting
- HTTPS domain and monitoring
