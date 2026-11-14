
# Import the required library

import joblib
from pathlib import Path


# Find the current folder

BASE_DIR = Path(__file__).resolve().parent


# Find the saved ML model

MODEL_PATH = BASE_DIR / "expense_model.pkl"


# Load the trained model

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        "Model not found. Run train_model.py first."
    )

model = joblib.load(MODEL_PATH)

print("ML model loaded successfully!")


# Create a function to predict expense category

def predict_category(description):

    description = description.strip()

    if not description:
        raise ValueError("Please enter an expense description.")

    prediction = model.predict([description])

    return prediction[0]


# Test the function

if __name__ == "__main__":

    expense = "Bus Ticket"

    category = predict_category(expense)

    print("Expense:", expense)

    print("Predicted Category:", category)
