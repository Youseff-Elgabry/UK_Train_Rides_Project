# UK Train Rides Project

Final project for **DEPI (Professional Data Analyst track)**.

## Overview
End-to-end data analysis and business intelligence project covering UK train rides, combining cleaned datasets, SQL Server (`Railway_UK`) database modeling, automated station geocoding and historical weather data scripts via Open-Meteo APIs, project documentation, and Power BI reporting.

## Repository Structure
- `Clean_Data/` — Cleaned datasets prepared for analysis and modeling.
- `Raw_Data/` — Original source data files.
- `Python_Scripts/` — Python scripts (`fetch_stations_open_meteo.py` and `fetch_weather_open_meteo.py`) for fetching station coordinates and daily weather data, exporting CSVs (`Stations.csv` and `Weather.csv`), and loading tables into SQL Server (`Railway_UK` as primary source with CSV fallback).
- `SQL/` — SQL scripts and database queries supporting the star-schema model and analysis.
- `Deliverables_1-3/` — Project documentation deliverables.
- `Phase2.pdf` — Phase 2 project documentation.
- `UK_Train_Rides_Presentation1.pdf` — Initial project presentation slides (early draft — requires major revisions; not the final version).

## Data Model & Tools
- **Data Model:** Star Schema (`dim_station`, `dim_date`, `fact_journey`, `fact_weather_daily`, and `station_nearby_places`).
- **Tools & Stack:** Python (`pandas`, `numpy`, `pyodbc`, `requests`), SQL Server, and Power BI.

## Notes
- Update local file paths and SQL Server connection settings (`SERVER` / `DATABASE`) if running the scripts on another machine.
