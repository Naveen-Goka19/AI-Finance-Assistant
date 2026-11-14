
import numpy as np


def predict_next_month(monthly_expenses):
    """
    Predict next month's expenses using linear regression.
    """

    if len(monthly_expenses) < 2:
        return None

    # Convert expenses into numbers
    expenses = np.array(monthly_expenses, dtype=float)

    # Month numbers
    months = np.arange(1, len(expenses) + 1)

    # Calculate linear regression
    slope, intercept = np.polyfit(months, expenses, 1)

    # Predict next month
    next_month = len(expenses) + 1

    prediction = slope * next_month + intercept

    # Prevent negative predictions
    prediction = max(0, prediction)

    return round(float(prediction), 2)


def get_forecast_from_database(monthly_expenses):
    """
    Receives monthly expense totals and predicts
    the next month's expenses.
    """

    if len(monthly_expenses) < 2:
        return None

    return predict_next_month(monthly_expenses)


# Test the model
if __name__ == "__main__":

    expenses = [5000, 6000, 7000, 8000]

    result = get_forecast_from_database(expenses)

    print("Monthly Expenses:", expenses)

    if result is not None:
        print("Predicted Next Month Expense: ₹", result)
    else:
        print("Not enough data to predict expenses.")

