import numpy as np
import pandas as pd
import pyodbc

SERVER = r".\SQLEXPRESS"
DATABASE = "Railway_UK"
RAILWAY_CSV_PATH = r"D:\Depi\Assignments\UK_Train_Rides(Final Project)\Final_Sheets\Railway_Cleaned.csv"
STATIONS_OUT_CSV = r"D:\Depi\Assignments\UK_Train_Rides(Final Project)\Data_From_API\Stations.csv"
TARGET_TABLE = "Stations"

df_rides = pd.read_csv(RAILWAY_CSV_PATH)

normalized_cols = {
    c.strip().lower().replace(" ", "_"): c for c in df_rides.columns
}

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

rng = np.random.default_rng(42)
rows = []
for idx, st_name in enumerate(stations_list, start=1):
    lat = round(float(rng.uniform(50.5, 55.9)), 6)
    lon = round(float(rng.uniform(-4.5, 1.8)), 6)
    crs_code = "".join(rng.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), size=3))
    naptan_code = f"9100{crs_code}{idx:02d}"
    rows.append((
        idx,
        st_name,
        naptan_code,
        crs_code,
        lat,
        lon,
    ))

df_stations = pd.DataFrame(
    rows,
    columns=["station_key", "station_name", "station_code", "crs_code", "latitude", "longitude"],
)
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
    station_key  INT           NOT NULL PRIMARY KEY,
    station_name NVARCHAR(100) NOT NULL,
    station_code VARCHAR(20)   NOT NULL,
    crs_code     VARCHAR(10)   NOT NULL,
    latitude     DECIMAL(9,6)  NOT NULL,
    longitude    DECIMAL(9,6)  NOT NULL
);
"""

insert_sql = f"""
INSERT INTO dbo.{TARGET_TABLE} (station_key, station_name, station_code, crs_code, latitude, longitude)
VALUES (?, ?, ?, ?, ?, ?);
"""

with pyodbc.connect(conn_str, autocommit=False) as conn:
    cursor = conn.cursor()
    cursor.execute(create_sql)
    cursor.executemany(insert_sql, rows)
    conn.commit()

print(f"Done! Saved {len(df_stations)} stations to {STATIONS_OUT_CSV} and dbo.{TARGET_TABLE}.")