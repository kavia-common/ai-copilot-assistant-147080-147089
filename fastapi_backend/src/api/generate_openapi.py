import json
import os

from src.api.main import app

# Get the OpenAPI schema
# Note: The schema is generated from Pydantic models (e.g., ChatRequest) that now
# include response_style Literal['list','plain','guided']. Regenerating will
# persist the 'guided' enum into interfaces/openapi.json.
openapi_schema = app.openapi()

# Write to file
output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
