from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")


class Trip(Base):
    __tablename__ = "trips"

    trip_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    trip_name = Column(String(150), nullable=True, default="")
    destination = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    budget = Column(Float, nullable=False, default=0.0)
    travellers = Column(Integer, nullable=False, default=1)
    interests = Column(String(255), nullable=True, default="")
    description = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="trips")
    itinerary_items = relationship(
        "Itinerary", back_populates="trip", cascade="all, delete-orphan", order_by="Itinerary.date, Itinerary.time"
    )
    expenses = relationship(
        "Expense", back_populates="trip", cascade="all, delete-orphan", order_by="Expense.expense_date.desc()"
    )
    saved_experiences = relationship(
        "SavedExperience", back_populates="trip", cascade="all, delete-orphan"
    )


class Itinerary(Base):
    __tablename__ = "itinerary"

    item_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.trip_id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(String(20), nullable=False)
    activity = Column(String(150), nullable=False)
    location = Column(String(150), nullable=True, default="")
    category = Column(String(50), nullable=True, default="General")
    estimated_cost = Column(Float, nullable=False, default=0.0)
    notes = Column(Text, nullable=True, default="")

    # Relationship
    trip = relationship("Trip", back_populates="itinerary_items")


class Expense(Base):
    __tablename__ = "expenses"

    expense_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.trip_id", ondelete="CASCADE"), nullable=False)
    category = Column(String(50), nullable=False)  # Food, Transport, Hotel, Activities, Shopping, Other
    amount = Column(Float, nullable=False)
    description = Column(String(200), nullable=False)
    expense_date = Column(Date, nullable=False, default=date.today)
    notes = Column(Text, nullable=True, default="")

    # Relationship
    trip = relationship("Trip", back_populates="expenses")

    @property
    def title(self):
        return self.description


class SavedExperience(Base):
    __tablename__ = "saved_experiences"

    saved_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.trip_id", ondelete="CASCADE"), nullable=False)
    experience_id = Column(Integer, nullable=False)
    name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False)
    price = Column(Float, nullable=False, default=0.0)
    rating = Column(Float, nullable=True, default=None)
    saved_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    trip = relationship("Trip", back_populates="saved_experiences")
