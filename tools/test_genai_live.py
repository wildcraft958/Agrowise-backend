import os
import asyncio
from google import genai
from google.genai.types import (Content, HttpOptions, LiveConnectConfig, Modality, Part)

# 1. Fetch API key from environment or .env
# Note: You can also use python-dotenv here, but we'll try to get it from os.environ first
api_key = os.environ.get("VERTEX_AI_API_KEY")

if not api_key:
    # Fallback to reading .env manually for this quick test if not in environment
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("VERTEX_AI_API_KEY"):
                    api_key = line.split("=")[1].strip()
                    break
    except FileNotFoundError:
        pass

# 1. Set environment variables for the SDK
# The user provided: agrowise-192e3-feea2cfd6558.json
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "agrowise-192e3-feea2cfd6558.json"

# 2. Initialize the client specifically for Vertex AI
client = genai.Client(
    vertexai=True,
    project="agrowise-192e3",
    location="us-central1",
    http_options=HttpOptions(api_version="v1beta1")
)

# Use the standard Vertex AI model naming convention
# Trying user's initial snippet model ID
model_id = "gemini-3.1-flash-lite-preview" 

async def run_live_session():
    print(f"Connecting to {model_id} on Vertex AI...")
    try:
        async with client.aio.live.connect(
            model=model_id,
            config=LiveConnectConfig(response_modalities=[Modality.TEXT]),
        ) as session:
            
            text_input = "Hello? Gemini, are you there?"
            print(f"> {text_input}\n")
            
            await session.send_client_content(
                turns=Content(role="user", parts=[Part(text=text_input)])
            )

            print("AI Response: ", end="", flush=True)
            async for message in session.receive():
                if message.text:
                    print(message.text, end="", flush=True)
            print("\n")

    except Exception as e:
        print(f"\nError during live session: {e}")

if __name__ == "__main__":
    asyncio.run(run_live_session())
