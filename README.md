# AFOC Bootstrap

This repository contains a minimal bootstrap for the Autonomous Fiscal Orchestration Core (AFOC).

## Getting Started

1. Install dependencies:
   ```bash
   pip install -e .[dev]
   ```
2. Run tests:
   ```bash
   pytest
   ```
3. Launch the API:
   ```bash
   uvicorn afoc.api.app:create_app --factory
   ```
4. Launch the dashboard:
   ```bash
   streamlit run afoc/dashboard/app.py
   ```
