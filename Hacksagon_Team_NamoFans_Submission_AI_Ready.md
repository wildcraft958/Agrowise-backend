# Hacksagon Submission: AgroWise & AgroSense
**Team NamoFans**
**Track:** Agritech & Rural Innovation

---

## Executive Summary
**Objective:** To empower Indian farmers with a ‘Phygital’ (Physical + Digital) ecosystem combining ground-truth soil telemetry with accessible, vernacular AI. Ensures precision agriculture is available to everyone, from smartphone users to feature phone owners.

### Sustainable Development Goals (SDG) Addressed:
*   **Goal 1: No Poverty:** Reduces input waste, saving ~$50K+/hectare.
*   **Goal 2: Zero Hunger:** Prevents crop failure and secures food supply.
*   **Goal 15: Life on Land:** Cuts chemical overuse by 40%, regenerating soil health.

---

## Problem Statement

### 1. The ‘Invisible’ Soil Crisis
Critical stress factors like root-zone moisture deficits and pH imbalances are invisible. Farmers rely on lagging visual cues (e.g., wilting). By then, physiological damage is often permanent, leading to reactive over-watering or under-watering.

### 2. Farming in the Dark
Generic weather apps lack hyper-local microclimate data. Scientific soil testing is a luxury most smallholder farmers never receive due to a lack of extension officers.

### 3. The Digital Divide
Most agritech is ‘Smartphone-First’, alienating the most vulnerable farmers who use feature phones or live in areas with spotty connectivity.

---

## Proposed Solution: The Phygital Ecosystem

### 1. AgroSense (Hardware) - The Ground Truth
A solar-powered, ‘deploy-and-forget’ IoT spike.
*   **Function:** Measures soil moisture, temperature, and humidity at the root zone.
*   **Features:** Autonomous operation, solar-powered, deep-sleep architecture.

### 2. AgroWise PWA (Software) - The High-Tech Layer
A Progressive Web App for smartphone users.
*   **Function:** Provides a visual dashboard with ‘Soil Thirst’ gauges.
*   **Features:** Uses ‘Neuro-Symbolic’ AI to diagnose diseases by correlating leaf photos with real-time soil sensor data.

### 3. Kisan-Vani (Voice Interface) - The High-Reach Layer
A toll-free IVR (Interactive Voice Response) for feature phone users.
*   **Function:** Bridges the digital divide by providing voice alerts in local dialects.
*   **Features:** Farmers can ‘dial their farm’ to check status without internet.

---

## System Architecture: The "Sense-Analyze-Act" Loop

1.  **Sense:** AgroSense spikes capture soil telemetry and push data to the Firebase cloud via WiFi/GSM.
2.  **Analyze (The Brain):** ‘AgroMind’ AI correlates sensor data with:
    *   **Gemini Flash:** Multi-modal analysis (Images + Sensors).
    *   **Scientific Databases:** ICAR/CIBRC manuals and IMD weather APIs.
    *   **Sarvam AI:** ASR/TTS for local language support.
3.  **Act:**
    *   **Smartphone:** Push notifications and visual graphs.
    *   **Feature Phone:** Automated voice calls in local dialects.

---

## Key Features & Novelty

### 1. Hyper-Local "Ground Truth"
Unlike satellite-based data (20km averages), AgroSense provides in-situ sensing of micro-climate realities.

### 2. Frugal Engineering (< ₹800 BOM)
Industrial-grade utility at a hobbyist price. Uses ESP32 and offloads processing to the cloud. Commercial probes often cost ₹15,000+.

### 3. Neuro-Symbolic Diagnosis
Combines Computer Vision (leaf photos) with Sensor Data. This eliminates false positives (e.g., drought stress vs. root rot).

### 4. “Peace of Mind” Telemetry
Automated alerts ensure farmers only need to act when a crisis occurs.

---

## Case Study / Interaction Scenario
**Context:** Ram (West Bengal) spots spots on leaves after a humid week.
1.  **Interaction:** Opens AgroWise, describes weather in Bengali, and takes a photo.
2.  **Result:** App diagnoses "Late Blight" due to high humidity.
3.  **Advice:** "Do not water today. Spray Mancozeb immediately."

---

## AgroWise PWA Features
*   **Device Onboarding:** Seamless setup via QR codes.
*   **Two-Point Calibration:** Monthly calibration for high precision.
*   **Vernacular Notifications:** Voice/SMS alerts in multiple languages (Hindi, Bengali, English).
