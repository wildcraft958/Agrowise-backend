# AgroMind API — Test Examples
claude --resume de5fac85-d9c4-495f-bd65-467e0729b3f0                                       
Base URL: `http://localhost:8000`

---

## POST /agromind/chat

### 1. Basic crop query (Hindi) — minimal context
```json
{
  "message": "Mere gehu ki pattiyan peeli pad rahi hain, kya karun?",
  "user_id": "farmer_001",
  "language": "hi",
  "context_block": ""
}
```
> Without state/district in context the agent asks for more info before calling mandatory tools. Use examples 2–5 for full responses.

---

### 2. Wheat fertilizer — with context block (mandatory tools fire)
```json
{
  "message": "What fertilizer should I apply to wheat at tillering stage?",
  "user_id": "farmer_002",
  "language": "en",
  "context_block": "## Farmer Location\nState: Punjab\nDistrict: Ludhiana\nBlock: Ludhiana-1\n\n## Crop\nWheat, sown 45 days ago, currently at tillering stage."
}
```

---

### 3. Pest control — tests CIBRC safety check
```json
{
  "message": "My cotton crop has bollworm infestation in Vidarbha. Which pesticide should I use?",
  "user_id": "farmer_003",
  "language": "en",
  "context_block": "## Farmer Location\nState: Maharashtra\nDistrict: Amravati\n\n## Crop\nCotton, 60 days after sowing, flowering stage."
}
```

---

### 4. Banned chemical — expect safety_violation: true
```json
{
  "message": "Can I use Aldrin to control termites in my sugarcane field in Uttar Pradesh?",
  "user_id": "farmer_004",
  "language": "en",
  "context_block": "## Farmer Location\nState: Uttar Pradesh\nDistrict: Lucknow\n\n## Crop\nSugarcane, ratoon crop."
}
```

Expected response shape:
```json
{
  "answer": "This response mentioned a banned chemical and has been blocked...",
  "tool_trace": ["cibrc_safety_check", "imd_weather_check"],
  "safety_violation": true,
  "violations": ["Aldrin"]
}
```

---

### 5. Mandi price query
```json
{
  "message": "What is the current wheat price in Amritsar mandi?",
  "user_id": "farmer_005",
  "language": "en",
  "context_block": "## Farmer Location\nState: Punjab\nDistrict: Amritsar"
}
```

---

### 6. Irrigation advisory — soil moisture + ET tools
```json
{
  "message": "Should I irrigate my paddy field today? Soil feels moderately dry.",
  "user_id": "farmer_006",
  "language": "en",
  "context_block": "## Farmer Location\nState: West Bengal\nDistrict: Bardhaman\n\n## Crop\nPaddy (Kharif), 30 days after transplanting, vegetative stage.\n\n## Soil\nClay loam, field capacity ~35%, current estimated moisture ~18%."
}
```

---

## POST /diagnosis

### 7. Crop disease detection

Step 1 — encode image (no line wraps):
```bash
# Linux
IMAGE_B64=$(base64 -w0 /path/to/leaf.jpg)

# macOS
IMAGE_B64=$(base64 /path/to/leaf.jpg)
```

Step 2 — send:
```bash
curl -X POST http://localhost:8000/diagnosis \
  -H "Content-Type: application/json" \
  -d "{\"image_b64\": \"$IMAGE_B64\", \"crop\": \"wheat\", \"user_id\": \"farmer_001\"}"
```

JSON body:
```json
{
  "image_b64": "<base64-string-no-newlines>",
  "crop": "wheat",
  "user_id": "farmer_001"
}
```

Expected response:
```json
{
  "disease": "Yellow Rust",
  "confidence": 0.87,
  "severity": "Moderate",
  "affected_area_pct": 35,
  "recommendations": ["Apply propiconazole fungicide", "Remove infected leaves"],
  "additional_notes": "Early stage — intervene within 48 hours"
}
```

Crop field is optional — omit to let the model infer from the image.

---

## GET /health

```bash
curl http://localhost:8000/health
```
```json
{"status": "ok", "version": "0.1.0"}
```

---

## Common Errors

### 422 — Invalid control character in JSON

```json
{
  "detail": [
    {
      "type": "json_invalid",
      "loc": ["body", 176],
      "msg": "JSON decode error",
      "ctx": {"error": "Invalid control character at"}
    }
  ]
}
```

Cause: base64 output wraps at 76 chars by default, embedding newlines inside the JSON string.

Fix:
```bash
# Wrong
base64 leaf.jpg

# Correct — single unbroken line
base64 -w0 leaf.jpg
```

macOS base64 does not wrap so no flag needed there.

---

### 500 — Safety validator crash
LLM returned a list content block instead of plain text (tool-call response). Fixed in agent/chain.py — make sure you are on the latest code.

### 404 on GET /
Root path has no handler. Use /health, /docs, or /agromind/chat.
