from fastapi import FastAPI
from app.api.endpoints import router
from app.db import Base, engine
from app.scheduler import start_scheduler
from fastapi.middleware.cors import CORSMiddleware 

app = FastAPI(title="Reddit AITA Scraper API")
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

# Start the daily scraping scheduler
start_scheduler()
