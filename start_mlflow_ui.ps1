# Launch MLflow UI with the professional SQLite backend
$ProjectRoot = Get-Location
$DbPath = Join-Path $ProjectRoot "mlflow.db"
echo "Starting MLflow Dashboard on http://127.0.0.1:5000"
echo "Database: $DbPath"
mlflow ui --backend-store-uri sqlite:///$DbPath
