from typing import List, Dict, Any
from app.models import Expense, Trip

def calculate_trip_budget(trip: Trip, expenses: List[Expense]) -> Dict[str, Any]:
    """
    Calculates spending metrics for a trip:
    - total_spent = Sum of all expenses
    - remaining_budget = Total Budget - Total Spent
    - budget_used_percentage = (Total Spent / Total Budget) * 100
    - budget_exceeded = True if Total Spent > Total Budget
    - category_breakdown = Dictionary mapping category to subtotal
    """
    total_spent = round(sum(float(e.amount) for e in expenses), 2)
    budget = float(trip.budget)
    
    remaining_budget = round(budget - total_spent, 2)
    
    if budget > 0:
        budget_used_pct = round((total_spent / budget) * 100.0, 1)
    else:
        budget_used_pct = 100.0 if total_spent > 0 else 0.0

    budget_exceeded = total_spent > budget

    # Standard Categories as specified in requirements
    category_breakdown = {
        "Food": 0.0,
        "Transport": 0.0,
        "Hotel": 0.0,
        "Activities": 0.0,
        "Shopping": 0.0,
        "Other": 0.0
    }

    for exp in expenses:
        cat = exp.category
        if cat in category_breakdown:
            category_breakdown[cat] = round(category_breakdown[cat] + float(exp.amount), 2)
        else:
            category_breakdown["Other"] = round(category_breakdown["Other"] + float(exp.amount), 2)

    return {
        "budget": budget,
        "total_spent": total_spent,
        "remaining_budget": remaining_budget,
        "budget_used_percentage": budget_used_pct,
        "budget_exceeded": budget_exceeded,
        "category_breakdown": category_breakdown
    }
