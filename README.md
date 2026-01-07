# Iron-View: Tactical Readiness System

> **Battalion 74 | Operational Dashboard**  
> *A specialized, offline-first command system for tracking vehicle readiness, logistics, and intelligence.*

![Iron-View Dashboard](https://via.placeholder.com/800x400?text=Iron-View+Tactical+Dashboard)

## 🎯 Overview

Iron-View is a Python-based tactical report generator designed for the IDF field environment. It processes raw Excel questionnaires (Kfir format) and transforms them into a **professional, interactive HTML dashboard**.

The system replaces manual Excel crunching with immediate operational insights.

### Key Logic: The "Two-Brain" System
The analysis engine is built on two distinct layers:
1.  **The Iron Brain (Deterministic)**: Hard-coded, rule-based queries found in `src/iron_view/logic/queries.py`.
    *   *Role*: 100% accurate calculation of Operational Status, Critical Faults, and Logistics Gaps.
    *   *Output*: Priority Lists and KPIs.
2.  **The Creative Brain (Generative)**: AI logic found in `src/iron_view/logic/llm_client.py`.
    *   *Role*: Strategic analysis, anomaly detection, and trend prediction.
    *   *Output*: The strictly formatted "Intelligence Feed" sidebar.
    *   *Note*: Falls back to "Training Scenario" mode if no API key is present.

## ✨ Features

- **Tactical Flat UI**: A "Matte Black" design system built for low-light command environments.
- **Zero-Dependency Runner**: A single shell script automates the entire ETL pipeline.
- **Excel Adapter (Kfir)**: Robust parsing of Hebrew column names and non-standard input formats.
- **Vehicle Inspector**: Clickable drill-down into specific tanks for granular technical history.
- **Offline First**: Generates a self-contained HTML file that works without internet.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Modern Web Browser (Chrome/Edge)

### Installation
1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Usage
Simply run the master script. It will auto-detect the latest Excel file in `mvp/files` or `data/input`.

```bash
./run_iron_view.sh
```

The report will open automatically in your browser.

## 🏗️ Architecture

```
iron-view/
├── assets/             # CSS/JS Themes (Tactical Flat)
├── src/iron_view/
│   ├── domain/         # Pydantic Models (VehicleReport)
│   ├── etl/            # Adapters (Kfir) & Loaders
│   ├── logic/          # The Two-Brain System
│   └── renderer/       # Jinja2 Builders
├── templates/          # HTML Templates (dashboard.j2)
└── run_iron_view.sh    # Operational Runner
```

## 🛠️ Configuration
Edit `src/iron_view/config.py` to adjust:
- **Theme**: Switch between `tactical_flat.css` and `iron_glass.css`.
- **Thresholds**: Adjust severity scoring weights.

## 📄 License
Internal Use Only - Battalion 74.
