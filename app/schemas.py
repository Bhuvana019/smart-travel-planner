from datetime import date, datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

# ===================================================================
# USER SCHEMAS
# ===================================================================

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    user_id: int
    name: str
    email: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=6, max_length=100)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# ===================================================================
# ITINERARY SCHEMAS
# ===================================================================

class ItineraryCreate(BaseModel):
    date: date
    time: str = Field(..., description="Time of activity, e.g. 10:30")
    activity: str = Field(..., min_length=1, max_length=150)
    location: Optional[str] = Field(default="", max_length=150)
    category: Optional[str] = Field(default="General", max_length=50)
    estimated_cost: float = Field(default=0.0, ge=0.0)
    notes: Optional[str] = Field(default="")

class ItineraryUpdate(BaseModel):
    date: Optional[date] = None
    time: Optional[str] = None
    activity: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    estimated_cost: Optional[float] = None
    notes: Optional[str] = None

class ItineraryOut(BaseModel):
    item_id: int
    trip_id: int
    date: date
    time: str
    activity: str
    location: Optional[str] = ""
    category: Optional[str] = "General"
    estimated_cost: float = 0.0
    notes: Optional[str] = ""

    class Config:
        from_attributes = True

# ===================================================================
# EXPENSE SCHEMAS
# ===================================================================

class ExpenseCreate(BaseModel):
    category: str = Field(..., description="Food, Transport, Hotel, Activities, Shopping, Other")
    amount: float = Field(..., gt=0.0)
    description: Optional[str] = Field(default="", max_length=200)
    title: Optional[str] = Field(default=None, max_length=200)
    expense_date: date
    notes: Optional[str] = Field(default="")

    @model_validator(mode="before")
    @classmethod
    def reconcile_title_description(cls, values):
        if isinstance(values, dict):
            t = values.get("title")
            d = values.get("description")
            if t and not d:
                values["description"] = t
            elif d and not t:
                values["title"] = d
            elif not t and not d:
                values["description"] = "Expense"
                values["title"] = "Expense"
        return values

class ExpenseUpdate(BaseModel):
    category: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0.0)
    description: Optional[str] = None
    title: Optional[str] = None
    expense_date: Optional[date] = None
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_title_description(cls, values):
        if isinstance(values, dict):
            t = values.get("title")
            d = values.get("description")
            if t and not d:
                values["description"] = t
        return values

class ExpenseOut(BaseModel):
    expense_id: int
    trip_id: int
    category: str
    amount: float
    description: str
    title: Optional[str] = ""
    expense_date: date
    notes: Optional[str] = ""

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def sync_title(self):
        if not self.title and self.description:
            self.title = self.description
        return self

class BudgetSummary(BaseModel):
    budget: float
    total_spent: float
    remaining_budget: float
    budget_used_percentage: float
    budget_exceeded: bool
    category_breakdown: Dict[str, float]

# ===================================================================
# SAVED EXPERIENCES SCHEMAS
# ===================================================================

class SavedExperienceCreate(BaseModel):
    experience_id: int = 1
    name: str = Field(..., min_length=1, max_length=150)
    category: str = Field(..., min_length=1, max_length=50)
    price: float = Field(default=0.0, ge=0.0)
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)

class SavedExperienceOut(BaseModel):
    saved_id: int
    trip_id: int
    experience_id: int
    name: str
    category: str
    price: float
    rating: Optional[float] = None
    saved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ===================================================================
# TRIP SCHEMAS
# ===================================================================

class TripCreate(BaseModel):
    trip_name: Optional[str] = Field(default="", max_length=150)
    destination: str = Field(..., min_length=1, max_length=100)
    start_date: date
    end_date: date
    budget: float = Field(..., ge=2000.0, description="Minimum budget ₹2,000")
    travellers: int = Field(..., gt=0)
    interests: Optional[Union[List[str], str]] = Field(default="")
    description: Optional[str] = Field(default="")

    @field_validator("budget", mode="before")
    @classmethod
    def parse_flexible_budget(cls, v):
        if isinstance(v, (int, float)):
            if float(v) < 2000.0:
                raise ValueError("Budget must be at least ₹2,000")
            return float(v)
        if isinstance(v, str):
            clean = v.strip().replace("₹", "").replace("INR", "").replace(" ", "").replace(",", "")
            if clean.lower().endswith("k"):
                try:
                    num = float(clean[:-1]) * 1000.0
                except Exception:
                    raise ValueError("Invalid budget number format")
            else:
                try:
                    num = float(clean)
                except Exception:
                    raise ValueError("Invalid budget number format")
            if num < 2000.0:
                raise ValueError("Budget must be at least ₹2,000")
            return num
        return v

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, end_date: date, info):
        start_date = info.data.get("start_date")
        if start_date and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        return end_date

class TripUpdate(BaseModel):
    trip_name: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = Field(None, ge=2000.0)
    travellers: Optional[int] = Field(None, gt=0)
    interests: Optional[Union[List[str], str]] = None
    description: Optional[str] = None

    @field_validator("budget", mode="before")
    @classmethod
    def parse_flexible_budget(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            if float(v) < 2000.0:
                raise ValueError("Budget must be at least ₹2,000")
            return float(v)
        if isinstance(v, str):
            clean = v.strip().replace("₹", "").replace("INR", "").replace(" ", "").replace(",", "")
            if clean.lower().endswith("k"):
                try:
                    num = float(clean[:-1]) * 1000.0
                except Exception:
                    raise ValueError("Invalid budget number format")
            else:
                try:
                    num = float(clean)
                except Exception:
                    raise ValueError("Invalid budget number format")
            if num < 2000.0:
                raise ValueError("Budget must be at least ₹2,000")
            return num
        return v

class TripOut(BaseModel):
    trip_id: int
    user_id: int
    trip_name: Optional[str] = ""
    destination: str
    start_date: date
    end_date: date
    budget: float
    travellers: int
    interests: str = ""
    description: Optional[str] = ""
    total_spent: float = 0.0
    remaining_budget: float = 0.0
    budget_used_percentage: float = 0.0
    budget_exceeded: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TripDetailOut(TripOut):
    itinerary_items: List[ItineraryOut] = []
    expenses: List[ExpenseOut] = []
    saved_experiences: List[SavedExperienceOut] = []
    category_breakdown: Dict[str, float] = {}

class TripSummaryOut(BaseModel):
    destination: str
    budget: float
    total_spent: float
    remaining_budget: float
    budget_used_percentage: float
    budget_exceeded: bool
    interests: List[str]
    selected_activities: List[str]

# Reverse API Integration Schema for Experience Finder
class ItinerarySummaryItem(BaseModel):
    item_id: int
    activity: str
    date: date
    time: str
    location: Optional[str] = ""
    category: Optional[str] = "General"
    estimated_cost: float = 0.0
    notes: Optional[str] = ""

    class Config:
        from_attributes = True

class TripIntegrationSummaryOut(BaseModel):
    trip_id: int
    destination: str
    start_date: date
    end_date: date
    budget: float
    selected_itinerary_activities: List[ItinerarySummaryItem] = []

    class Config:
        from_attributes = True


# ===================================================================
# EXTERNAL EXPERIENCE FINDER SCHEMAS
# ===================================================================

class ExperienceItem(BaseModel):
    id: Union[int, str] = 1
    name: str
    category: str = "General"
    price: float = 0.0
    rating: Optional[float] = None
    description: Optional[str] = ""
    destination: Optional[str] = ""
    duration: Optional[str] = ""
    image_url: Optional[str] = ""
    locality: Optional[str] = ""
    review_count: Optional[int] = 0

class ExperienceListResponse(BaseModel):
    experiences: List[ExperienceItem] = []
    source: str = "Local Development Adapter"
    is_external: bool = False
    status: str = "SUCCESS"  # SUCCESS, ERROR, EMPTY, DEV_MOCK
    status_message: str = "Loaded from local sample catalog"
    target_url: Optional[str] = None
    error_detail: Optional[str] = None
    retry_available: bool = False
    count: Optional[int] = 0
    request_summary: Optional[Dict[str, Any]] = None
    response_summary: Optional[Dict[str, Any]] = None
