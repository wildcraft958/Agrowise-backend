import os
from google import genai
from google.genai import types

# 1. Set environment variables for the SDK
# The user provided: agrowise-192e3-feea2cfd6558.json
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "agrowise-192e3-feea2cfd6558.json"

# 2. Initialize the client specifically for Vertex AI
client = genai.Client(
    vertexai=True, 
    project="agrowise-192e3", 
    location="global" 
)

# 3. Vision Test
IMAGE_URI = "gs://generativeai-downloads/images/scones.jpg"
model_id = "gemini-3.1-flash-lite-preview"

print(f"Testing vision with model: {model_id}")
print(f"Image URI: {IMAGE_URI}")

try:
    response = client.models.generate_content(
        model=model_id,
        contents=[
          "What is shown in this image?",
          types.Part.from_uri(
            file_uri=IMAGE_URI,
            mime_type="image/jpeg", # Scones is usually jpeg
          ),
        ],
    )
    print("\nAI Response:")
    print("-" * 20)
    print(response.text)
    print("-" * 20)

except Exception as e:
    print(f"\nError during vision generation: {e}")
    print("\nTip: If 'model not found', try changing location to 'us-central1' or 'global'.")
