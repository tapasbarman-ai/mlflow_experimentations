import mlflow
import pandas as pd
from fastapi import FastAPI
import uvicorn
import os
import logging

# --- REQUIREMENT: Inference logging where contractually required ---
# Configure structured logging for Audit/Compliance
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("inference_audit.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("InferenceService")

app = FastAPI(title="Bike Demand Prediction Service (Industrial v2)")

# Configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
db_path_raw = os.path.join(root_dir, "mlflow.db").replace("\\", "/")
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{db_path_raw}")
MODEL_NAME = "Bike_Demand_Predictor"
# Default to "None" if no production model is tagged yet, so the local test works
MODEL_STAGE = os.getenv("MODEL_STAGE", "None") 

mlflow.set_tracking_uri(MLFLOW_URI)

# Load the model globally
model = None
try:
    logger.info(f"Attempting to load model: {MODEL_NAME} (Stage: {MODEL_STAGE})")
    model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/{MODEL_STAGE}")
    logger.info("Model loaded successfully into memory.")
except Exception as e:
    logger.error(f"Failed to load model from registry: {e}")
    logger.warning("Service will start with model=None. Predictions will fail until model is registered.")

@app.post("/predict")
def predict(data: dict):
    # Log the incoming request for audit purposes
    logger.info(f"AUDIT_REQUEST: {data}")
    
    if model is None:
        logger.error("Prediction failed: Model not loaded")
        return {"error": "Model not loaded", "status": "failed"}
    
    try:
        df = pd.DataFrame([data])
        prediction = model.predict(df)
        
        # Log the prediction for audit purposes
        result = int(prediction[0])
        logger.info(f"AUDIT_SUCCESS: Prediction={result}")
        
        return {
            "prediction": result,
            "status": "success",
            "model_version": MODEL_STAGE
        }
    except Exception as e:
        logger.error(f"Prediction logic error: {e}")
        return {"error": str(e), "status": "failed"}

@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": model is not None}

if __name__ == "__main__":
    # --- FIXED: Use 127.0.0.1 for local Windows stability to avoid WinError 10022 ---
    # use PORT env var if provided (for Docker/Cloud)
    port = int(os.getenv("PORT", 8000))
    # Note: We avoid reload=True here because it causes the socket OS error on many Windows setups
    uvicorn.run(app, host="127.0.0.1", port=port)
