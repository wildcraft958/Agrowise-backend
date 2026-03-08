# AgroWise: Data & Knowledge Base Inventory (Non-CIBRC)

This document provides a comprehensive list of all agricultural datasets, reference manuals, and knowledge bases available in this repository, excluding the CIBRC chemical registry.

---

## 1. Reference Manuals & Reports (`dataset/`)
These are high-fidelity ICAR and Government of India PDF documents used for RAG and expert advisory.

| File Name | Description |
| :--- | :--- |
| **Methods Manual Soil Testing In India** | Extensive GOI manual on chemical and physical soil analysis protocols. |
| **Soil and Water Testing Methods (IARI)** | Technical reference for lab-grade soil/water quality assessment. |
| **ICAR Eng Annual Report 2024-25** | Latest progress report on agricultural engineering and mechanization. |
| **Indian Farming (Nov 2025)** | Monthly ICAR publication with recent field studies and farmer success stories. |
| **Integrated Plant Nutrition Management** | Manual on balanced fertilisation and bio-fertiliser usage (Jan 2024). |

---

## 2. Market & Location Mappings (`bolbhav-data/`)
This directory contains pan-India geospatial and market data for price discovery and advisory targeting.

### 2.1 Market (Mandi) Data
- **`Agmark Mandis and locations.csv`**: Comprehensive list of Agmarknet-registered mandis with latitude/longitude.
- **`Agmark crops.csv`**: Mapping of standard crop names used in government market reporting.
- **`Mandi (APMC) Map.csv`**: Relational mapping of APMC markets across different states.

### 2.2 Geography & Hierarchy
- **`Location hierarchy.csv`**: Reference for the administrative structure (State → District → Block → Gram Panchayat).
- **`District Neighbour Map India.csv`**: Adjacency matrix for spatial analysis (e.g., tracking disease spread to neighboring districts).
- **`IMD Agromet advisory locations.csv`**: Mapping of IMD weather station IDs to administrative blocks.
- **`Gramhal_ Pan-India Mappings.csv`**: Specific mappings for Gramhal's market-linking services.

---

## 3. API & Mock Data (`data/` and `dataset/`)
- **`data/IMD_API.md`**: Technical reference for fetching real-time weather and advisory data.
- **`dataset/mock_data.md`**: Simulated dataset for testing the IVR/IVR logic and dashboard components.

---

## 4. Submission Documentation (Root)
- **`Hacksagon_Team_NamoFans_Submission_AI_Ready.md`**: The AI-optimized project pitch and overview, containing high-level feature descriptions and architectural goals.
