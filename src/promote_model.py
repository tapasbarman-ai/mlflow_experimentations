import mlflow
from mlflow.tracking import MlflowClient
import os
import argparse

# Standardize tracking to the project root mlflow.db
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
db_path = os.path.join(root_dir, "mlflow.db")
mlflow.set_tracking_uri(f"sqlite:///{db_path}")

def promote_model(model_name, stage="Staging"):
    print(f"Promoting latest version of model '{model_name}' to '{stage}'...")
    
    client = MlflowClient()
    
    # Get latest version in 'None' stage (meaning just registered)
    latest_versions = client.get_latest_versions(model_name, stages=["None"])
    
    if not latest_versions:
        # Check if already in Staging
        latest_versions = client.get_latest_versions(model_name, stages=["Staging"])
        if not latest_versions:
            print(f"Error: No versions found for model '{model_name}'")
            return

    latest_version = latest_versions[0].version
    print(f"Latest version identified: {latest_version}")

    # Transition the model version
    client.transition_model_version_stage(
        name=model_name,
        version=latest_version,
        stage=stage,
        archive_existing_versions=True
    )
    
    print(f"Successfully promoted '{model_name}' (v{latest_version}) to '{stage}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="Bike_Demand_Predictor")
    parser.add_argument("--stage", type=str, default="Staging")
    args = parser.parse_args()

    promote_model(args.model, args.stage)
