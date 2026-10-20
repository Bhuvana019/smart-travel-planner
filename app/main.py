from contextlib import asynccontextmanager
from pathlib import Path
from datetime import date, datetime
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base, SessionLocal
from app.models import User, Trip, Itinerary, Expense, SavedExperience
from app.auth import hash_password
from app.routers import users, trips, itinerary, expenses, recommendations, pages, sync, integration


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger("smart_travel_planner")

BASE_DIR = Path(__file__).resolve().parent

def seed_demo_data():
    """
    Seeds the standard college demonstration scenario if database is fresh:
    User: Arun Kumar (arun.kumar@example.com / password123)
    Trip: Goa (15-18 Oct 2026, 3 travelers, ₹25,000 budget, Interests: Adventure, Beach, Food)
    Itinerary: Baga Beach, Dolphin Watching, Scuba Diving, Sunset Cruise
    Expenses: Food (₹2,000), Transport (₹1,500), Activities (₹3,700) -> Total Spent ₹7,200, Remaining ₹17,800
    Saved Experiences: Scuba Diving, Dolphin Watching
    """
    db = SessionLocal()
    try:
        arun = db.query(User).filter(User.email == "arun.kumar@example.com").first()
        if not arun:
            logger.info("Seeding demo user Arun Kumar...")
            arun = User(
                name="Arun Kumar",
                email="arun.kumar@example.com",
                password_hash=hash_password("password123")
            )
            db.add(arun)
            db.commit()
            db.refresh(arun)

            logger.info("Seeding demo Goa trip...")
            goa_trip = Trip(
                trip_id=101,
                user_id=arun.user_id,
                destination="Goa",
                start_date=date(2026, 10, 15),
                end_date=date(2026, 10, 18),
                budget=25000.0,
                travellers=3,
                interests="Adventure, Beach, Food",
                description="Sun, sand, scuba adventures, and coastal Goan cuisine with college friends."
            )
            db.add(goa_trip)
            db.commit()
            db.refresh(goa_trip)

            # Seed Itinerary
            itinerary_items = [
                Itinerary(
                    trip_id=goa_trip.trip_id,
                    date=date(2026, 10, 15),
                    time="10:30",
                    activity="Baga Beach",
                    location="North Goa",
                    estimated_cost=0.0,
                    notes="Relax and explore the beach shacks"
                ),
                Itinerary(
                    trip_id=goa_trip.trip_id,
                    date=date(2026, 10, 15),
                    time="16:00",
                    activity="Dolphin Watching",
                    location="Sinquerim Beach",
                    estimated_cost=1200.0,
                    notes="Scenic boat trip in the Arabian Sea"
                ),
                Itinerary(
                    trip_id=goa_trip.trip_id,
                    date=date(2026, 10, 16),
                    time="09:00",
                    activity="Scuba Diving",
                    location="Grande Island",
                    estimated_cost=2500.0,
                    notes="Certified guide with underwater photography"
                ),
                Itinerary(
                    trip_id=goa_trip.trip_id,
                    date=date(2026, 10, 16),
                    time="17:30",
                    activity="Sunset Cruise at Mandovi",
                    location="Panaji Jetty",
                    estimated_cost=950.0,
                    notes="1-hour river cruise with Goan cultural dance"
                )
            ]
            db.add_all(itinerary_items)

            # Seed Expenses:
            # Food = ₹850 + ₹1150 = ₹2,000
            # Transport = ₹650 + ₹850 = ₹1,500
            # Activities = ₹3,700
            # Total = ₹7,200 | Remaining = ₹17,800
            expenses_list = [
                Expense(
                    trip_id=goa_trip.trip_id,
                    category="Food",
                    amount=850.0,
                    description="Dinner at Britto's shack",
                    expense_date=date(2026, 10, 15)
                ),
                Expense(
                    trip_id=goa_trip.trip_id,
                    category="Transport",
                    amount=650.0,
                    description="Airport prepaid cab to hotel",
                    expense_date=date(2026, 10, 15)
                ),
                Expense(
                    trip_id=goa_trip.trip_id,
                    category="Food",
                    amount=1150.0,
                    description="Authentic seafood lunch in Panaji",
                    expense_date=date(2026, 10, 16)
                ),
                Expense(
                    trip_id=goa_trip.trip_id,
                    category="Transport",
                    amount=850.0,
                    description="Scooter rental for 3 days",
                    expense_date=date(2026, 10, 15)
                ),
                Expense(
                    trip_id=goa_trip.trip_id,
                    category="Activities",
                    amount=3700.0,
                    description="Scuba diving & water sports combo",
                    expense_date=date(2026, 10, 16)
                )
            ]
            db.add_all(expenses_list)

            # Seed initial saved experiences
            saved_exps = [
                SavedExperience(
                    trip_id=goa_trip.trip_id,
                    experience_id=1,
                    name="Scuba Diving",
                    category="Adventure",
                    price=2500.0,
                    rating=4.7
                ),
                SavedExperience(
                    trip_id=goa_trip.trip_id,
                    experience_id=2,
                    name="Dolphin Watching",
                    category="Adventure",
                    price=1200.0,
                    rating=4.5
                )
            ]
            db.add_all(saved_exps)

            # Also seed a second upcoming trip for Kerala
            kerala_trip = Trip(
                trip_id=102,
                user_id=arun.user_id,
                destination="Kerala Backwaters",
                start_date=date(2026, 11, 5),
                end_date=date(2026, 11, 10),
                budget=32000.0,
                travellers=2,
                interests="Relaxation, Nature, Food",
                description="Serene houseboat cruising in Alleppey and spice plantation trails."
            )
            db.add(kerala_trip)

            db.commit()
            logger.info("Demo scenario seeded successfully!")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and seed demo data
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    seed_demo_data()
    yield
    # Shutdown
    logger.info("Shutting down Smart Travel Planner...")

app = FastAPI(
    title="Smart Travel Planner API",
    description="Full-stack FastAPI backend for intelligent travel planning, budgeting, and experience discovery.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Assets
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Register API Routers
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(itinerary.router)
app.include_router(expenses.router)
app.include_router(recommendations.router)
app.include_router(sync.router)
app.include_router(integration.router)


# Register HTML Template Pages Router
app.include_router(pages.router)

@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": "Smart Travel Planner API",
        "port": 8000,
        "database": "SQLite (travel_planner.db)",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
