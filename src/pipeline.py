import mlflow
import mlflow.sklearn
import pandas as pd
import os
import subprocess
import io
import hashlib
import json
from datetime import datetime
import requests
import zipfile
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, ConfusionMatrixDisplay

# --- FIX: Set Matplotlib backend to 'Agg' before importing pyplot ---
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- FIXED: Evidently AI Imports for v0.7.20 ---
from evidently import Report
from evidently.presets import DataDriftPreset


# Standardize tracking to the project root mlruns folder
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
mlruns_path = os.path.join(root_dir, "mlruns")
data_dir = os.path.join(root_dir, "data")
os.makedirs(data_dir, exist_ok=True)

mlflow.set_tracking_uri(f"file:///{mlruns_path}")
mlflow.set_experiment("Bike_Sharing_Industrial_MLOps_v2")
mlflow.sklearn.autolog()


def get_dvc_hash(file_path):
    """
    Requirement: Dataset Version Tracking
    Uses hashlib as a robust alternative since 'dvc hash' is not available in all DVC versions.
    """
    try:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Warning: Could not generate hash: {e}")
        return f"local-version-{datetime.now().strftime('%Y%m%d')}"

def get_git_hash():
    """Requirement: Reproducibility Logs (Git Commit)"""
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root_dir).decode('utf-8').strip()
    except Exception:
        return "not-a-git-repo"

# ==========================================
# SECTION 2: DATA INGESTION & VERSIONING
# ==========================================

def run_production_pipeline():
    # Requirement: Dataset version tracking mandatory
    print("Downloading Bike Sharing Dataset...")
    url = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
    response = requests.get(url)
    
    # Extract 'hour.csv' and save locally for DVC tracking
    with zipfile.ZipFile(io.BytesIO(response.content)) as arc:
        raw_data = pd.read_csv(arc.open("hour.csv"), header=0, sep=',')
        # Save in the data/ folder
        data_path = os.path.join(data_dir, "bike_hour.csv")
        raw_data.to_csv(data_path, index=False)

    # Capture Data Version (DVC) and Code Version (Git)
    dataset_hash = get_dvc_hash(data_path)
    git_hash = get_git_hash()
    print(f"Data Version: {dataset_hash}")

    # ==========================================
    # SECTION 3: DATA PREPROCESSING
    # ==========================================
    
    raw_data['target'] = (raw_data['cnt'] > 200).astype(int)
    categorical_cols = ['season', 'mnth', 'hr', 'holiday', 'weekday', 'workingday', 'weathersit']
    features = raw_data.drop(['instant', 'dteday', 'casual', 'registered', 'cnt', 'target'], axis=1)
    X = pd.get_dummies(features, columns=['season', 'weathersit', 'mnth', 'hr'], drop_first=True)
    y = raw_data['target']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # ==========================================
    # SECTION 4: MLFLOW EXPERIMENT START
    # ==========================================
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"Run_{timestamp}"
    
    artifacts_dir = os.path.join(root_dir, "artifacts", run_name)
    os.makedirs(artifacts_dir, exist_ok=True)
    print(f"Artifacts will be saved in: {artifacts_dir}")

    with mlflow.start_run(run_name=run_name) as run:
        
        mlflow.set_tag("data_version", dataset_hash)
        mlflow.set_tag("git_commit", git_hash)
        mlflow.set_tag("dataset_source", "UCI Bike Sharing")

        rf = RandomForestClassifier(n_estimators=80, max_depth=10, random_state=42)
        rf.fit(X_train, y_train)

        y_pred = rf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        mlflow.log_metric("overall_accuracy", acc)
        print(f"Pipeline Accuracy: {acc}")

        # ==========================================
        # SECTION 5: BIAS & FAIRNESS EVALUATION
        # ==========================================
        for val in [0, 1]:
            mask = X_test['holiday'] == val
            if mask.sum() > 0:
                group_acc = accuracy_score(y_test[mask], y_pred[mask])
                label = "Holiday" if val == 1 else "Regular_Day"
                mlflow.log_metric(f"bias_acc_{label}", group_acc)
                print(f" [Bias Check] {label} Accuracy: {group_acc:.4f}")

        # ==========================================
        # SECTION 6: DRIFT MONITORING (EVIDENTLY AI)
        # ==========================================
        print("Generating Drift Report...")
        drift_report = Report(metrics=[DataDriftPreset()])
        snapshot = drift_report.run(reference_data=X_train, current_data=X_test)
        
        report_path = os.path.join(artifacts_dir, "bike_drift_report.html")
        snapshot.save_html(report_path)
        mlflow.log_artifact(report_path)

        # ==========================================
        # SECTION 7: REPRODUCIBILITY & MODEL REGISTRY
        # ==========================================
        cm = confusion_matrix(y_test, y_pred)
        disp = ConfusionMatrixDisplay(confusion_matrix=cm)
        disp.plot()
        plt.title(f"Bike Demand Confusion Matrix ({run_name})")
        cm_path = os.path.join(artifacts_dir, "bike_cm.png")
        plt.savefig(cm_path)
        mlflow.log_artifact(cm_path)

        model_name = "Bike_Demand_Predictor"
        mlflow.sklearn.log_model(
            sk_model=rf,
            artifact_path="model",
            registered_model_name=model_name
        )
        print(f" Model Registered: {model_name}")

if __name__ == "__main__":
    run_production_pipeline()
