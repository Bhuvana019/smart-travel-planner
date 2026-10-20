from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)

@router.get("/", response_class=HTMLResponse)
@router.get("/index.html", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@router.get("/login", response_class=HTMLResponse)
@router.get("/login.html", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@router.get("/register", response_class=HTMLResponse)
@router.get("/register.html", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@router.get("/about", response_class=HTMLResponse)
@router.get("/about.html", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse(request=request, name="about.html")

@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/dashboard.html", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@router.get("/create_trip.html", response_class=HTMLResponse)
@router.get("/trips/new", response_class=HTMLResponse)
async def create_trip_page(request: Request):
    return templates.TemplateResponse(request=request, name="create_trip.html")

@router.get("/trip", response_class=HTMLResponse)
@router.get("/trip.html", response_class=HTMLResponse)
@router.get("/trips/{trip_id}", response_class=HTMLResponse)
async def trip_details_page(request: Request, trip_id: int = 130, id: int = None):
    effective_id = id if (id is not None and id != 101) else (trip_id if trip_id != 101 else 130)
    return templates.TemplateResponse(request=request, name="trip.html", context={"trip_id": effective_id})

@router.get("/itinerary", response_class=HTMLResponse)
@router.get("/itinerary.html", response_class=HTMLResponse)
@router.get("/trips/{trip_id}/itinerary", response_class=HTMLResponse)
async def itinerary_page(request: Request, trip_id: int = 130, id: int = None):
    effective_id = id if (id is not None and id != 101) else (trip_id if trip_id != 101 else 130)
    return templates.TemplateResponse(request=request, name="itinerary.html", context={"trip_id": effective_id})

@router.get("/expenses", response_class=HTMLResponse)
@router.get("/expenses.html", response_class=HTMLResponse)
@router.get("/trips/{trip_id}/expenses", response_class=HTMLResponse)
async def expenses_page(request: Request, trip_id: int = 130, id: int = None):
    effective_id = id if (id is not None and id != 101) else (trip_id if trip_id != 101 else 130)
    return templates.TemplateResponse(request=request, name="expenses.html", context={"trip_id": effective_id})

@router.get("/recommendations", response_class=HTMLResponse)
@router.get("/recommendations.html", response_class=HTMLResponse)
@router.get("/trips/{trip_id}/discover", response_class=HTMLResponse)
async def recommendations_page(request: Request, trip_id: int = 130, id: int = None):
    effective_id = id if (id is not None and id != 101) else (trip_id if trip_id != 101 else 130)
    return templates.TemplateResponse(request=request, name="recommendations.html", context={"trip_id": effective_id})

@router.get("/profile", response_class=HTMLResponse)
@router.get("/profile.html", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse(request=request, name="profile.html")

@router.get("/exchange", response_class=HTMLResponse)
@router.get("/exchange.html", response_class=HTMLResponse)
async def exchange_page(request: Request):
    return templates.TemplateResponse(request=request, name="exchange.html")
