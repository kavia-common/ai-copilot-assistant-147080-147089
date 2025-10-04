import json
import os

from src.api.main import app

# Get the OpenAPI schema
# Note: The route accepts either a minimal {'message': string} or a full
# {'messages': [...], 'response_style'?}. Regenerating keeps this description
# in the OpenAPI schema.
openapi_schema = app.openapi()

# Write to file
output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
