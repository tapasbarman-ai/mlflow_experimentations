import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt
import pandas as pd
import os

# 1. Set Tracking URI and Experiment
mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("Student_Performance_Analysis")

# Enable Autologging
mlflow.sklearn.autolog()

# Load data
# If running from inside 'src', 'data.csv' is in the same folder.
# If running from project root, it's in 'src/data.csv'.
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, "data.csv")

if not os.path.exists(data_path):
    # Try project root level if not found in src
    data_path = "src/data.csv"

df = pd.read_csv(data_path)

# --- FIX: Encoding Categorical Data ---
# Based on actual CSV columns: gender, academic_level, internet_quality
categorical_cols = ['gender', 'academic_level', 'internet_quality']
df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

# Drop student_id (it doesn't help predict scores) and split features/target
X = df.drop(["exam_score", "student_id"], axis=1)
y = df["exam_score"]

# Since exam_score is a number (0-100), but we are using a Classifier,
# let's turn it into a Pass/Fail task (1 if score > 50, else 0).
y = (y > 50).astype(int)

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    shuffle=True
)

print("Train shape:", X_train.shape)
print("Test shape:", X_test.shape)

# 2. Define Parameters
n_estimators = 100
max_depth = 5

# 3. Start MLflow Run
with mlflow.start_run(run_name="RandomForest_Final_Fix"):
    # Train model
    rf = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
    rf.fit(X_train, y_train)

    # Predictions and Metrics
    y_pred = rf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy (Pass/Fail): {accuracy}")

    # 4. Log Artifacts
    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm)
    disp.plot()
    
    plt.title("Confusion Matrix")
    plt.savefig("confusion_matrix.png")
    # Log the image as an artifact
    mlflow.log_artifact("confusion_matrix.png")
    
    print("Run completed successfully. Check the MLflow UI!")



