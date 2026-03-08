# End-to-End System Architecture: AgroWise & AgroSense

This document outlines the "Sense-Analyze-Act" feedback loop that powers the AgroWise ecosystem. The architecture is designed for high-reach (feature phones) and high-tech (smartphones) accessibility.

## 1. Visual Architecture (Mermaid)

```mermaid
graph TD
    subgraph "The Farm (Hardware Layer)"
        A[AgroSense Spike] -->|WiFi/GSM| B
        A1["- ESP32 MCU<br/>- Capacitive Soil Sensor<br/>- Solar Powered"]
        A -.-> A1
    end

    subgraph "The Brain (Cloud & AI Layer)"
        B[(Firebase Backend)]
        
        subgraph "Neural-Symbolic Engine"
            C1[Inputs] --> C2[Analysis]
            C2 --> C3[RAG & Context]
            C3 --> C4[Safety Filter]
            C4 --> C5[Output Generation]

            D1["- Voice/Text (Sarvam AI)<br/>- Image (Leaf Photos)<br/>- IoT Sensor Data"]
            C1 -.-> D1
            
            D2["- Gemini Flash<br/>- Symptom Detection<br/>- Vertex AI"]
            C2 -.-> D2

            D3["- ICAR Manuals<br/>- IMD Weather API"]
            C3 -.-> D3

            D4["- CIBRC Database<br/>(Banned Chemicals Check)"]
            C4 -.-> D4

            D5["- Local Language TTS<br/>(Sarvam AI)"]
            C5 -.-> D5
        end

        B <==> C1
    end

    subgraph "The Users (Interface Layer)"
        C5 --> E1[PWA Dashboard]
        C5 --> E2[IVR Voice Calls]
        
        F1["Visuals & AI Chat"]
        E1 -.-> F1
        
        F2["Twilio / Exotel"]
        E2 -.-> F2
    end

    style B fill:#f9f,stroke:#333,stroke-width:2px
    style C1 fill:#dfd,stroke:#333
    style C2 fill:#dfd,stroke:#333
    style C3 fill:#dfd,stroke:#333
    style C4 fill:#dfd,stroke:#333
    style C5 fill:#dfd,stroke:#333
```

---

## 2. Component Breakdown

### A. The Farm (Edge Device)
*   **AgroSense Spike:** A low-cost (< ₹800), solar-powered IoT device.
*   **Edge Logic:** Uses ESP32 deep-sleep mode to conserve power, waking up to transmit soil moisture, temperature, and humidity directly to the cloud.

### B. The Brain (Cloud Engine)
*   **Firebase Backend:** Acts as the central data orchestrator.
*   **Neural-Symbolic Engine:** 
    *   **Multi-Modal Inputs:** Processes voice (Sarvam AI), images (Computer Vision), and raw sensor telemetry.
    *   **AI Analysis:** Uses **Gemini Flash** (Vertex AI) for rapid symptom detection and explanation.
    *   **Contextual RAG:** Cross-references findings with official ICAR disease manuals and real-time IMD weather data (to suppress irrigation alerts if rain is imminent).
    *   **Safety Layer:** Filters recommendations against the CIBRC database to ensure no banned or harmful chemicals are suggested to farmers.

### C. The Users (Omnichannel Delivery)
*   **AgroWise PWA:** High-fidelity dashboard for smartphone users featuring visual "Soil Thirst" gauges and interactive AI chat.
*   **Kisan-Vani (IVR):** Automated voice calls via Twilio/Exotel for feature phone users, bridging the digital divide with local language support (Sarvam AI).

---

## 3. Key Differentiation
> **"Not just classification."**
> Unlike traditional AG-Tech, the engine explains **WHY** a disease occurred and **WHEN** to act, combining ground-truth telemetry with symbolic scientific knowledge.