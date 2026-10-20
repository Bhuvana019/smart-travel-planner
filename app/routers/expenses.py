from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Expense, Trip, User
from app.schemas import ExpenseCreate, ExpenseUpdate, ExpenseOut, BudgetSummary
from app.auth import get_current_user
from app.services.budget_service import calculate_trip_budget

router = APIRouter(tags=["Expenses"])

VALID_CATEGORIES = ["Food", "Transport", "Hotel", "Activities", "Shopping", "Other"]

def _normalize_category(cat: str) -> str:
    for valid in VALID_CATEGORIES:
        if cat.lower() == valid.lower():
            return valid
    return "Other"

@router.post("/api/trips/{trip_id}/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def add_expense(
    trip_id: int,
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a new expense to the specified trip and updates budget tracking."""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to add expenses to this trip")

    desc = (expense_data.description or expense_data.title or "General Expense").strip()
    new_expense = Expense(
        trip_id=trip.trip_id,
        category=_normalize_category(expense_data.category),
        amount=float(expense_data.amount),
        description=desc,
        expense_date=expense_data.expense_date,
        notes=expense_data.notes.strip() if expense_data.notes else ""
    )
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return ExpenseOut.model_validate(new_expense)

@router.get("/api/trips/{trip_id}/expenses", response_model=Dict[str, Any])
def get_trip_expenses(
    trip_id: int,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all expenses for a trip along with the budget calculations and category subtotals."""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to view this trip's expenses")

    all_expenses = db.query(Expense).filter(Expense.trip_id == trip_id).order_by(Expense.expense_date.desc()).all()
    budget_info = calculate_trip_budget(trip, all_expenses)

    filtered_expenses = all_expenses
    if category and category.strip().lower() != "all":
        filtered_expenses = [e for e in all_expenses if e.category.lower() == category.strip().lower()]

    return {
        "trip_id": trip.trip_id,
        "destination": trip.destination,
        "budget": budget_info["budget"],
        "total_spent": budget_info["total_spent"],
        "remaining_budget": budget_info["remaining_budget"],
        "budget_used_percentage": budget_info["budget_used_percentage"],
        "budget_exceeded": budget_info["budget_exceeded"],
        "category_breakdown": budget_info["category_breakdown"],
        "expenses": [ExpenseOut.model_validate(e) for e in filtered_expenses]
    }

@router.put("/api/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates an existing expense transaction."""
    expense = db.query(Expense).filter(Expense.expense_id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if expense.trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to edit this expense")

    if expense_update.category is not None:
        expense.category = _normalize_category(expense_update.category)
    if expense_update.amount is not None:
        expense.amount = float(expense_update.amount)
    desc = expense_update.description if expense_update.description is not None else expense_update.title
    if desc is not None:
        expense.description = desc.strip()
    if expense_update.expense_date is not None:
        expense.expense_date = expense_update.expense_date
    if expense_update.notes is not None:
        expense.notes = expense_update.notes.strip()

    db.commit()
    db.refresh(expense)
    return ExpenseOut.model_validate(expense)

@router.delete("/api/expenses/{expense_id}", status_code=status.HTTP_200_OK)
def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes an expense item."""
    expense = db.query(Expense).filter(Expense.expense_id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if expense.trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this expense")

    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted successfully", "expense_id": expense_id}
