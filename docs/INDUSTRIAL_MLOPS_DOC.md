# Industrial MLOps Pipeline Documentation

This document defines the core pillars of industrial-grade machine learning and explains how they are implemented in the `src/pipeline.py` pipeline.

---

## 1. Dataset Version Tracking (Mandatory)
### 📖 Definition
The process of capturing a unique snapshot of the data used to train a specific model. This creates a link between the model artifacts and the exact data records that produced them.

### 🛠️ Implementation in Code
- **Method**: The script calculates an **MD5 Checksum** of the `data/bike_hour.csv` file using `hashlib`. 
- **Tracking**: This hash is logged in MLflow as a tag: `data_version`.
- **DVC Strategy**: Designed to integrate with Data Version Control (DVC) for large-scale data management.

---

## 2. Model Version Tagging & Registry
### 📖 Definition
A centralized system (Model Registry) that manages the lifecycle of a model, including versioning (v1, v2, etc.), stage transitions (Staging, Production, Archived), and metadata.

### 🛠️ Implementation in Code
- **Tool**: **MLflow Model Registry**.
- **Process**: The script calls `mlflow.sklearn.log_model()` with a fixed `registered_model_name="Bike_Demand_Predictor"`. 
- **Versioning**: Every execution automatically increments the version number in the MLflow UI.

---

## 3. Reproducibility Logs
### 📖 Definition
The documentation of the entire "recipe" required to recreate a model experiment, including the exact code version, hyperparameters, environment dependencies, and hardware context.

### 🛠️ Implementation in Code
- **Git Integration**: Captures the current **Git Commit Hash** via `get_git_hash()` and logs it as a tag.
- **Autologging**: `mlflow.sklearn.autolog()` automatically saves:
    - Scikit-learn parameters.
    - Python environment (`requirements.txt`).
    - Training metrics.

---

## 4. Bias Evaluation Report
### 📖 Definition
The systematic testing of a model's performance across different subgroups (protected classes, regions, or time periods) to ensure equitable outcomes and robust performance.

### 🛠️ Implementation in Code
- **Slice Analysis**: The script calculates accuracy separately for `Regular Days` vs. `Holidays`.
- **Logging**: Metrics are logged as `bias_acc_Regular_Day` and `bias_acc_Holiday`.

---

## 5. Model Drift Monitoring
### 📖 Definition
Detecting "Data Drift" (changes in input distributions) or "Concept Drift" (changes in the relationship between input and output) that causes model performance to degrade over time.

### 🛠️ Implementation in Code
- **Tool**: **Evidently AI**.
- **Report**: Merges `X_train` (Reference) and `X_test` (Current) to detect statistical shifts.
- **Artifact**: Generates `bike_drift_report.html`.

---

## 6. Inference Logging
### 📖 Definition
The real-time recording of every prediction request (input) and model response (output) in a production environment for audit, compliance, and future retraining.

### 🛠️ Implementation in Code
- **Infrastructure**: In production, models are wrapped in APIs (e.g., **FastAPI**).
- **Compliance Tool**: Logs are typically sent to centralized logging systems like **ELK** or **Prometheus**.
