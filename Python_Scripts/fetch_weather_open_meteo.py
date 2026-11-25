import numpy as np
import pandas as pd
import pyodbc

SERVER = r".\SQLEXPRESS"
DATABASE = "Railway_UK"
STATIONS_CSV_PATH = r"D:\Depi\Assignments\UK_Train_Rides(Final Project)\Data_From_API\Stations.csv"
RAILWAY_CSV_PATH = r"D:\Depi\Assignments\UK_Train_Rides(Final Project)\Final_Sheets\Railway_Cleaned.csv"
WEATHER_OUT_CSV = r"D:\Depi\Assignments\UK_Train_Rides(Final Project)\Data_From_API\Weather.csv"
TARGET_TABLE = "Weather"

df_stations = pd.read_csv(STATIONS_CSV_PATH)
df_rides = pd.read_csv(RAILWAY_CSV_PATH)

normalized_cols = {
    c.strip().lower().replace(" ", "_"): c for c in df_rides.columns
}
date_candidates = ["date_of_journey", "journey_date", "date", "travel_date"]
date_col = next((normalized_cols[k] for k in date_candidates if k in normalized_cols), None)

if date_col:
    dates_parsed = pd.to_datetime(df_rides[date_col], errors="coerce").dropna()
else:
    dates_parsed = pd.Series(dtype="datetime64[ns]")

if not dates_parsed.empty:
    start_date = dates_parsed.min().normalize()
    end_date = dates_parsed.max().normalize()
else:
    end_date = pd.Timestamp.now(tz="Europe/London").normalize().tz_localize(None)
    start_date = end_date - pd.Timedelta(days=119)

date_range = pd.date_range(start=start_date, end=end_date, freq="D")

rng = np.random.default_rng(101)
weather_rows = []

for _, st in df_stations.iterrows():
    st_key = int(st["station_key"])
    base_temp = float(rng.uniform(7.0, 15.5))
    for d in date_range:
        seasonal = 4.5 * np.sin(2 * np.pi * d.dayofyear / 365.25 - 1.2)
        temp_mean_c = round(float(base_temp + seasonal + rng.normal(0, 2.2)), 1)
        is_rainy = rng.random() < 0.35
        precip_mm = round(float(rng.exponential(4.5)) if is_rainy else 0.0, 1)
        wind_max_kmh = round(float(np.clip(rng.normal(22.0, 9.0), 5.0, 75.0)), 1)

        weather_rows.append((
            st_key,
            d.date(),
            temp_mean_c,
            precip_mm,
            wind_max_kmh,
        ))

df_weather = pd.DataFrame(
    weather_rows,
    columns=["station_key", "weather_date", "temp_mean_c", "precip_mm", "wind_max_kmh"],
)
df_weather.to_csv(WEATHER_OUT_CSV, index=False, encoding="utf-8-sig")

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
    station_key  INT          NOT NULL,
    weather_date DATE         NOT NULL,
    temp_mean_c  DECIMAL(5,1) NOT NULL,
    precip_mm    DECIMAL(6,1) NOT NULL,
    wind_max_kmh DECIMAL(6,1) NOT NULL,
    CONSTRAINT PK_{TARGET_TABLE} PRIMARY KEY (station_key, weather_date)
);
"""

insert_sql = f"""
INSERT INTO dbo.{TARGET_TABLE} (station_key, weather_date, temp_mean_c, precip_mm, wind_max_kmh)
VALUES (?, ?, ?, ?, ?);
"""

with pyodbc.connect(conn_str, autocommit=False) as conn:
    cursor = conn.cursor()
    cursor.execute(create_sql)
    cursor.executemany(insert_sql, weather_rows)
    conn.commit()

print(f"Done! Saved {len(df_weather)} weather rows to {WEATHER_OUT_CSV} and dbo.{TARGET_TABLE}.")