import re
import time
import pandas as pd
import pyodbc
import requests

SERVER = r".\SQLEXPRESS"
DATABASE = "Railway_UK"
RAILWAY_CSV_PATH = r"D:\Depi\Assignments\UK_Train_Rides(Final Project)\Final_Sheets\Railway_Cleaned.csv"
STATIONS_OUT_CSV = r"D:\Depi\Assignments\UK_Train_Rides(Final Project)\Data_From_API\Stations.csv"
TARGET_TABLE = "Stations"

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

df_rides = pd.read_csv(RAILWAY_CSV_PATH)
normalized_cols = {c.strip().lower().replace(" ", "_"): c for c in df_rides.columns}

dep_candidates = ["departure_station", "dep_station", "departure", "from_station", "origin_station"]
arr_candidates = ["arrival_destination", "arrival_station", "arr_station", "destination", "to_station"]

dep_col = next((normalized_cols[k] for k in dep_candidates if k in normalized_cols), None)
arr_col = next((normalized_cols[k] for k in arr_candidates if k in normalized_cols), None)

if not dep_col or not arr_col:
    raise KeyError(f"Available columns: {list(df_rides.columns)}")

stations_list = sorted(
    set(df_rides[dep_col].dropna().astype(str).str.strip()).union(
        set(df_rides[arr_col].dropna().astype(str).str.strip())
    )
)


def build_candidate_queries(station_name: str) -> list[str]:
    base = re.sub(r"\s+", " ", station_name).strip()
    stripped = re.sub(
        r"\b(new street|central|lime street|temple meads|piccadilly|euston|kings cross|king's cross|paddington|st pancras|st\. pancras|waterloo)\b",
        "",
        base,
        flags=re.IGNORECASE,
    )
    stripped = re.sub(r"\s+", " ", stripped).strip()
    first_word = base.split(" ")[0] if base else ""

    candidates = [base, stripped, first_word]
    unique_queries = []
    for item in candidates:
        cleaned = item.strip()
        if cleaned and cleaned not in unique_queries:
            unique_queries.append(cleaned)
    return unique_queries


def fetch_station_coords(station_name: str) -> tuple[float, float]:
    for q in build_candidate_queries(station_name):
        resp = requests.get(
            GEOCODING_URL,
            params={"name": q, "count": 10, "language": "en", "format": "json"},
            timeout=20,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
        uk_matches = [r for r in results if r.get("country_code") == "GB"]
        chosen = uk_matches[0] if uk_matches else None
        if chosen and chosen.get("latitude") is not None and chosen.get("longitude") is not None:
            return round(float(chosen["longitude"]), 6), round(float(chosen["latitude"]), 6)
    raise ValueError(f"Could not fetch coordinates for station: {station_name}")


rows = []
for idx, st_name in enumerate(stations_list, start=1):
    lon, lat = fetch_station_coords(st_name)
    clean_code = "".join(ch for ch in st_name.upper() if ch.isalpha())[:7].ljust(4, "X")
    station_id = f"9100{clean_code}{idx:02d}"
    rows.append((idx, st_name, station_id, lon, lat))
    time.sleep(0.15)

columns = ["location_id", "Station_Name", "Station_ID", "Longitude", "Latitude"]
df_stations = pd.DataFrame(rows, columns=columns)
df_stations.to_csv(STATIONS_OUT_CSV, index=False, encoding="utf-8-sig")

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
)

create_sql = f"""
IF OBJECT_ID('dbo.{TARGET_TABLE}', 'U') IS NOT NULL
    DROP TABLE dbo.{TARGET_TABLE};

CREATE TABLE dbo.{TARGET_TABLE} (
    [location_id]  INT           NOT NULL PRIMARY KEY,
    [Station_Name] NVARCHAR(100) NOT NULL,
    [Station_ID]   VARCHAR(20)   NOT NULL,
    [Longitude]    DECIMAL(9,6)  NOT NULL,
    [Latitude]     DECIMAL(9,6)  NOT NULL
);
"""

insert_sql = f"""
INSERT INTO dbo.{TARGET_TABLE} ([location_id], [Station_Name], [Station_ID], [Longitude], [Latitude])
VALUES (?, ?, ?, ?, ?);
"""

with pyodbc.connect(conn_str, autocommit=False) as conn:
    cursor = conn.cursor()
    cursor.execute(create_sql)
    cursor.executemany(insert_sql, rows)
    conn.commit()

print(f"Done! Saved {len(df_stations)} stations to {STATIONS_OUT_CSV} and dbo.{TARGET_TABLE}.")