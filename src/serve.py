import mlflow
import pandas as pd
from fastapi import FastAPI
import uvicorn
import os

app = FastAPI(title="Bike Demand Prediction Service")

# Configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", f"file:///{os.path.join(root_dir, 'mlruns')}")
MODEL_NAME = "Bike_Demand_Predictor"
MODEL_STAGE = "None" 

mlflow.set_tracking_uri(MLFLOW_URI)

# Load the model globally
try:
    print(f"Loading model: {MODEL_NAME} (Stage: {MODEL_STAGE})")
    model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/{MODEL_STAGE}")
except Exception as e:
    print(f"Warning: Could not load model. Ensure a model is registered. Error: {e}")
    model = None

@app.post("/predict")
def predict(data: dict):
    if model is None:
        return {"error": "Model not loaded", "status": "failed"}
    
    df = pd.DataFrame([data])
    prediction = model.predict(df)
    
    return {
        "prediction": int(prediction[0]),
        "status": "success"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
