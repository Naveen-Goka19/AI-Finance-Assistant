
# Step 1: Import libraries

import csv
from pathlib import Path
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score


# Step 2: Find dataset and model files

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = BASE_DIR / "expense_data.csv"

MODEL_PATH = BASE_DIR / "expense_model.pkl"


# Step 3: Read the dataset
descriptions = []
categories = []

with open(DATA_PATH, "r", encoding="utf-8-sig", newline="") as file:

    reader = csv.reader(file)

    # Read the first row (column headings)
    header = next(reader, None)

    if header is None or len(header) < 2:
        raise ValueError(
            "CSV file is empty or incorrect. "
            "Expected: description,category"
        )

    print("CSV headings:", header)

    # Read the remaining rows
    for row in reader:

        # Skip empty or incomplete rows
        if len(row) < 2:
            continue

        description = row[0].strip()
        category = row[1].strip()

        if description and category:
            descriptions.append(description)
            categories.append(category)


print("Dataset loaded successfully!")
print("Total examples:", len(descriptions))

if len(descriptions) == 0:
    raise ValueError("No training data found in CSV file.")



# Step 4: Divide data into training and testing

X_train, X_test, y_train, y_test = train_test_split(
    descriptions,
    categories,
    test_size=0.2,
    random_state=42,
    stratify=categories
)


# Step 5: Create the ML model

model = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
    ("classifier", MultinomialNB())
])


# Step 6: Train the model

model.fit(X_train, y_train)

print("\nModel training completed!")


# Step 7: Test the model

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\nModel Accuracy:", round(accuracy * 100, 2), "%")


# Step 8: Save the trained model

joblib.dump(model, MODEL_PATH)

print("\nModel saved successfully!")

print("Model location:", MODEL_PATH)


# Step 9: Test sample expenses

sample_expenses = [
    "Bought vegetables",
    "Bus ticket",
    "Purchased new shoes",
    "Electricity bill"
]

results = model.predict(sample_expenses)

print("\nSample Predictions:")

for description, category in zip(sample_expenses, results):
    print(description, ":", category)
