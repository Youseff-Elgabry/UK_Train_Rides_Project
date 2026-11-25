# UK Train Rides Project

Final project for **DEPI (Professional Data Analyst track)**.

## Overview
End-to-end data analysis and business intelligence project covering UK train rides, combining cleaned datasets, SQL database modeling, simulated station/weather data scripts, project documentation, and presentation deliverables.

## Repository Structure
- `Clean_Data/` — Cleaned datasets prepared for analysis and modeling.
- `Raw_Data/` — Original source data files.
- `Python_Scripts/` — Python scripts for data processing and generating station (`Stations`) and weather (`Weather`) datasets and loading them into SQL Server.
- `SQL/` — SQL scripts and database queries supporting the project schema and analysis.
- `Deliverables_1-3 (Project Docum...` — Project documentation deliverables.
- `Phase2.pdf` — Phase 2 project documentation.
- `UK_Train_Rides_Presentation1.pdf` — Initial project presentation slides (early draft — requires major revisions; not the final version).

## Data Model & Tools
- **Data Model:** Star Schema (`dim_station`, `dim_date`, `fact_journey`, `fact_weather_daily`, and `station_nearby_places`).
- **Tools & Stack:** Python (`pandas`, `numpy`, `pyodbc`), SQL Server, and Power BI.

## Notes
- Keep local paths or SQL Server connection details (`SERVER` / `DATABASE`) updated if running the scripts on another machine.
