from fastapi import FastAPI
from app.api.endpoints import router
from app.db import Base, engine
from automation.scheduler import automation_scheduler
from app.utils.logger import logger
from app.video.tts import cleanup_tts_memory
from app.video.srt import cleanup_whisper_memory
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Narrify - Reddit Video Automation API")
Base.metadata.create_all(bind=engine)
app.include_router(router, prefix="/api")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Narrify application")
    automation_scheduler.start()
    logger.info("Automation scheduler started (scrape + generate at 05:00 daily)")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Narrify application")
    automation_scheduler.stop()
    logger.info("Automation scheduler stopped")
    cleanup_tts_memory()
    cleanup_whisper_memory()
    logger.info("GPU memory released")

@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "Narrify - Reddit Video Automation",
        "version": "1.0.0"
    }
