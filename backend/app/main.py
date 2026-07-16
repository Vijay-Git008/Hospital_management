import os
import json
import logging
from dotenv import load_dotenv

# Load .env variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
load_dotenv()
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db.database import Base, engine, get_db
from .db.models import Hospital
from .db.seed import seed_db
from .ws.hub import manager
from .routers import auth, cases, resources, negotiation, ai_config, analytics, nexus

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmergencyCommandCenter")

app = FastAPI(
    title="AI-Powered Emergency Resource Negotiation API",
    description="Deterministic multi-agent resource bidding with dynamic LLM explainability.",
    version="1.0.0"
)

# CORS Configuration
# Adjust to support frontend Vite dev server origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production, but open for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(resources.router)
app.include_router(negotiation.router)
app.include_router(ai_config.router)
app.include_router(analytics.router)
app.include_router(nexus.router)

@app.on_event("startup")
def startup_event():
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=engine)
    
    # Auto-seed if database is empty
    db = next(get_db())
    try:
        hospital_exists = db.query(Hospital).first()
        if not hospital_exists:
            logger.info("Database is empty. Seeding defaults...")
            seed_db()
        else:
            logger.info("Database already initialized.")
    except Exception as e:
        logger.error(f"Error checking database state: {e}")
    finally:
        db.close()

@app.get("/api/status")
def read_root():
    return {
        "status": "Online",
        "service": "Emergency Resource Negotiation Engine",
        "timestamp": os.getenv("CURRENT_TIME", "2026-07-16T13:40:00")
    }

# Serve static index.html from app/static/index.html at root
@app.get("/")
def serve_static_index():
    static_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "static/index.html"))
    if os.path.isfile(static_file):
        return FileResponse(static_file)
    return {"error": "NEXUS Static UI build not found"}

# Mount static files
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.isdir(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    # Catch-all route to serve the SPA
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Exclude /api and /ws routes from being caught here
        if full_path.startswith("api/") or full_path == "ws":
            # Just returning 404 for unmatched api routes
            return {"detail": "Not Found"}
            
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        return {"error": "Frontend build not found"}
else:
    logger.warning(f"Frontend dist directory not found at {frontend_dist}. Falling back to NEXUS static UI.")
    
    # Catch-all route to serve NEXUS static UI
    @app.get("/{full_path:path}")
    async def serve_nexus_fallback(request: Request, full_path: str):
        # Exclude /api and /ws routes from being caught here
        if full_path.startswith("api/") or full_path == "ws" or full_path.startswith("static"):
            return {"detail": "Not Found"}
        static_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "static/index.html"))
        if os.path.isfile(static_file):
            return FileResponse(static_file)
        return {"error": "NEXUS Static UI build not found"}

# Live dashboard WebSockets route
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; receive messages from client if necessary
            data = await websocket.receive_text()
            # Simple echo or heartbeat handling
            await websocket.send_json({"event": "heartbeat", "received": data[:50]})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        manager.disconnect(websocket)
