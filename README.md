# UK Train Rides Project

Final project for **DEPI (Professional Data Analyst track)**[cite: 1].

## Overview
End-to-end data analysis and business intelligence project covering UK train rides, combining cleaned datasets, SQL database modeling, simulated station/weather data scripts, project documentation, and presentation deliverables[cite: 1].

## Repository Structure
- `Clean_Data/` — Cleaned datasets prepared for analysis and modeling[cite: 1].
- `Raw_Data/` — Original source data files[cite: 1].
- `Python_Scripts/` — Python scripts for data processing and generating station (`Stations`) and weather (`Weather`) datasets and loading them into SQL Server[cite: 1].
- `SQL/` — SQL scripts and database queries supporting the project schema and analysis[cite: 1].
- `Deliverables_1-3 (Project Docum...` — Project documentation deliverables[cite: 1].
- `Phase2.pdf` — Phase 2 project documentation[cite: 1].
- `UK_Train_Rides_Presentation1.pdf` — Initial project presentation slides (early draft — requires major revisions; not the final version)[cite: 1].

## Data Model & Tools
- **Data Model:** Star Schema (`dim_station`, `dim_date`, `fact_journey`, `fact_weather_daily`, and `station_nearby_places`).
- **Tools & Stack:** Python (`pandas`, `numpy`, `pyodbc`), SQL Server, and Power BI.

## Notes
- Keep local paths or SQL Server connection details (`SERVER` / `DATABASE`) updated if running the scripts on another machine.
