from fastapi import FastAPI
from app.api.endpoints import router
from app.db import Base, engine
from app.scheduler import start_scheduler
from automation.scheduler import automation_scheduler
from app.utils.logger import logger
from fastapi.middleware.cors import CORSMiddleware 

app = FastAPI(title="Narrify - Reddit Video Automation API")
Base.metadata.create_all(bind=engine)
app.include_router(router, prefix="/api")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins - use specific origins in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize schedulers and services on startup"""
    logger.info("Starting Narrify application")
    
    # Start Reddit scraping scheduler
    start_scheduler()
    logger.info("Reddit scraping scheduler started")
    
    # Start automation scheduler for YouTube posting
    automation_scheduler.start()
    logger.info("YouTube automation scheduler started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of schedulers"""
    logger.info("Shutting down Narrify application")
    automation_scheduler.stop()
    logger.info("Automation scheduler stopped")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Narrify - Reddit Video Automation",
        "version": "1.0.0"
    }
