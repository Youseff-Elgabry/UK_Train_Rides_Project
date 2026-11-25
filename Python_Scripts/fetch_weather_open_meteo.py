import os
import time
import pandas as pd
import pyodbc
import requests

SERVER = r".\SQLEXPRESS"
DATABASE = "Railway_UK"
STATIONS_CSV_PATH = r"D:\Depi\Assignments\UK_Train_Rides(Final Project)\Data_From_API\Stations.csv"
RAILWAY_CSV_PATH = r"D:\Depi\Assignments\UK_Train_Rides(Final Project)\Final_Sheets\Railway_Cleaned.csv"
WEATHER_OUT_CSV = r"D:\Depi\Assignments\UK_Train_Rides(Final Project)\Data_From_API\Weather.csv"
TARGET_TABLE = "Weather"
STATIONS_TABLE = "Stations"

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
)


def load_stations() -> pd.DataFrame:
    try:
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            query = f"SELECT location_id, Station_Name, Station_ID, Longitude, Latitude FROM dbo.{STATIONS_TABLE}"
            df_db = pd.read_sql(query, conn)
            if not df_db.empty:
                return df_db
    except Exception:
        pass

    if not os.path.exists(STATIONS_CSV_PATH):
        raise FileNotFoundError(f"Stations not found in dbo.{STATIONS_TABLE} or {STATIONS_CSV_PATH}")
    return pd.read_csv(STATIONS_CSV_PATH)


df_stations = load_stations()
df_rides = pd.read_csv(RAILWAY_CSV_PATH)

normalized_cols = {c.strip().lower().replace(" ", "_"): c for c in df_rides.columns}
date_candidates = ["date_of_journey", "journey_date", "date", "travel_date"]
date_col = next((normalized_cols[k] for k in date_candidates if k in normalized_cols), None)

if not date_col:
    raise KeyError(f"Date column not found. Available columns: {list(df_rides.columns)}")

dates_parsed = pd.to_datetime(df_rides[date_col], errors="coerce").dropna()
start_date = dates_parsed.min().strftime("%Y-%m-%d")
end_date = dates_parsed.max().strftime("%Y-%m-%d")

weather_rows = []

for _, st in df_stations.iterrows():
    loc_id = int(st["location_id"])
    lat = float(st["Latitude"])
    lon = float(st["Longitude"])

    resp = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_mean,precipitation_sum,wind_speed_10m_max",
            "timezone": "Europe/London",
        },
        timeout=30,
    )
    resp.raise_for_status()
    daily = resp.json().get("daily") or {}

    times = daily.get("time") or []
    temps = daily.get("temperature_2m_mean") or []
    precips = daily.get("precipitation_sum") or []
    winds = daily.get("wind_speed_10m_max") or []

    for d_str, t_val, p_val, w_val in zip(times, temps, precips, winds):
        dt_obj = pd.to_datetime(d_str)
        formatted_date = f"{dt_obj.month}/{dt_obj.day}/{dt_obj.year}"
        weather_rows.append((
            loc_id,
            formatted_date,
            round(float(t_val), 1) if t_val is not None else None,
            round(float(p_val), 1) if p_val is not None else None,
            round(float(w_val), 1) if w_val is not None else None,
        ))

    time.sleep(0.2)

weather_cols = [
    "location_id",
    "Date",
    "Temperature_Mean (°C)",
    "Precipitation_Sum (mm)",
    "Wind_Speed_Max (km/h)",
]

df_weather = pd.DataFrame(weather_rows, columns=weather_cols)
df_weather.to_csv(WEATHER_OUT_CSV, index=False, encoding="utf-8-sig")

sql_rows = [
    (r[0], pd.to_datetime(r[1]).date(), r[2], r[3], r[4])
    for r in weather_rows
]

create_sql = f"""
IF OBJECT_ID('dbo.{TARGET_TABLE}', 'U') IS NOT NULL
    DROP TABLE dbo.{TARGET_TABLE};

CREATE TABLE dbo.{TARGET_TABLE} (
    [location_id]            INT          NOT NULL,
    [Date]                   DATE         NOT NULL,
    [Temperature_Mean (°C)]  DECIMAL(5,1) NULL,
    [Precipitation_Sum (mm)] DECIMAL(6,1) NULL,
    [Wind_Speed_Max (km/h)]  DECIMAL(6,1) NULL,
    CONSTRAINT PK_{TARGET_TABLE} PRIMARY KEY ([location_id], [Date])
);
"""

insert_sql = f"""
INSERT INTO dbo.{TARGET_TABLE} (
    [location_id],
    [Date],
    [Temperature_Mean (°C)],
    [Precipitation_Sum (mm)],
    [Wind_Speed_Max (km/h)]
)
VALUES (?, ?, ?, ?, ?);
"""

with pyodbc.connect(conn_str, autocommit=False) as conn:
    cursor = conn.cursor()
    cursor.execute(create_sql)
    cursor.executemany(insert_sql, sql_rows)
    conn.commit()

print(f"Done! Saved {len(df_weather)} weather rows to {WEATHER_OUT_CSV} and dbo.{TARGET_TABLE}.")