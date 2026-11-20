use [Railway_UK]
---------------------------------------------Check------------------------
USE Railway_UK;
SELECT COUNT(*) AS stations FROM Stations
SELECT COUNT(*) AS weather  FROM Weather
--------------------------------------------------------------------------
IF OBJECT_ID('dbo.fact_weather_daily','U') IS NOT NULL DROP TABLE dbo.fact_weather_daily;
IF OBJECT_ID('dbo.fact_journey','U')       IS NOT NULL DROP TABLE dbo.fact_journey;
IF OBJECT_ID('dbo.dim_station','U')        IS NOT NULL DROP TABLE dbo.dim_station;

CREATE TABLE dbo.dim_station (
    station_key  INT           NOT NULL CONSTRAINT PK_dim_station PRIMARY KEY,
    station_name NVARCHAR(100) NOT NULL CONSTRAINT UQ_dim_station_name UNIQUE,
    station_code VARCHAR(20)   NOT NULL,
    latitude     DECIMAL(9,6)  NOT NULL,
    longitude    DECIMAL(9,6)  NOT NULL
)
INSERT INTO dbo.dim_station (station_key, station_name, station_code, latitude, longitude)
SELECT location_id, LTRIM(RTRIM(Station_Name)), LTRIM(RTRIM(Station_ID)), Latitude, Longitude
FROM Stations

SELECT COUNT(*) AS stations FROM dbo.dim_station
----------------------------------------------------------------------------------------------
CREATE TABLE dbo.fact_weather_daily (
    station_key  INT          NOT NULL,
    weather_date DATE         NOT NULL,
    temp_mean_c  DECIMAL(5,1) NOT NULL,
    precip_mm    DECIMAL(6,1) NOT NULL,
    wind_max_kmh DECIMAL(6,1) NOT NULL,
    CONSTRAINT PK_fact_weather_daily PRIMARY KEY (station_key, weather_date),
    CONSTRAINT FK_weather_station FOREIGN KEY (station_key) REFERENCES dbo.dim_station(station_key)
)
INSERT INTO dbo.fact_weather_daily (station_key, weather_date, temp_mean_c, precip_mm, wind_max_kmh)
SELECT location_id, TRY_CONVERT(date, [Date], 101),
       Temperature_Mean_C, Precipitation_Sum_mm, Wind_Speed_Max_km_h
FROM Weather

SELECT COUNT(*) AS rows_, MIN(weather_date) AS first_day, MAX(weather_date) AS last_day
FROM dbo.fact_weather_daily
------------------------------------------------------------------------------------------------------
CREATE TABLE dbo.fact_journey (
    transaction_id   VARCHAR(60)   NOT NULL CONSTRAINT PK_fact_journey PRIMARY KEY,
    purchase_date    DATE          NOT NULL,
    purchase_time    TIME(0)       NOT NULL,
    purchase_type    VARCHAR(20)   NOT NULL,
    payment_method   VARCHAR(20)   NOT NULL,
    railcard         VARCHAR(20)   NOT NULL,
    ticket_class     VARCHAR(20)   NOT NULL,
    ticket_type      VARCHAR(20)   NOT NULL,
    price            DECIMAL(8,2)  NOT NULL CONSTRAINT CK_price_positive CHECK (price > 0),
    dep_station_key  INT           NOT NULL CONSTRAINT FK_journey_dep REFERENCES dbo.dim_station(station_key),
    arr_station_key  INT           NOT NULL CONSTRAINT FK_journey_arr REFERENCES dbo.dim_station(station_key),
    journey_date     DATE          NOT NULL,
    dep_time         TIME(0)       NOT NULL,
    sched_arr_time   TIME(0)       NOT NULL,
    actual_arr_time  TIME(0)       NULL,
    delay_minutes    DECIMAL(7,1)  NULL,
    journey_status   VARCHAR(20)   NOT NULL CONSTRAINT CK_status CHECK (journey_status IN ('On Time','Delayed','Cancelled')),
    delay_reason     VARCHAR(30)   NOT NULL,
    refund_requested BIT           NOT NULL,
    CONSTRAINT CK_purchase_before_journey CHECK (purchase_date <= journey_date)
);
GO
INSERT INTO dbo.fact_journey
    (transaction_id, purchase_date, purchase_time, purchase_type, payment_method, railcard, ticket_class, ticket_type,
     price, dep_station_key, arr_station_key, journey_date, dep_time, sched_arr_time, actual_arr_time, delay_minutes,
     journey_status, delay_reason, refund_requested)
SELECT
    r.Transaction_ID,
    TRY_CONVERT(date, r.Date_of_Purchase, 101),
    t.pur_t,
    r.Purchase_Type, r.Payment_Method, r.Railcard, r.Ticket_Class, r.Ticket_Type,
    r.Price,
    d1.station_key, d2.station_key,
    TRY_CONVERT(date, r.Date_of_Journey, 101),
    t.dep_t, t.arr_t, t.act_t,
    CASE WHEN t.act_t IS NULL THEN NULL
         ELSE ((DATEDIFF(SECOND, t.arr_t, t.act_t) % 86400 + 86400 + 43200) % 86400 - 43200) / 60.0 END,
    r.Journey_Status, r.Reason_for_Delay,
    CASE WHEN CAST(r.Refund_Request AS VARCHAR(10)) IN ('1','True','TRUE','true','Yes') THEN 1 ELSE 0 END
FROM dbo.railway AS r
JOIN dbo.dim_station AS d1 ON d1.station_name = LTRIM(RTRIM(r.Departure_Station))
JOIN dbo.dim_station AS d2 ON d2.station_name = LTRIM(RTRIM(r.Arrival_Destination))
CROSS APPLY (SELECT TRY_CONVERT(time(0), r.Time_of_Purchase)    AS pur_t,
                    TRY_CONVERT(time(0), r.Departure_Time)      AS dep_t,
                    TRY_CONVERT(time(0), r.Arrival_Time)        AS arr_t,
                    TRY_CONVERT(time(0), r.Actual_Arrival_Time) AS act_t) AS t;
GO
CREATE INDEX IX_fact_journey_date  ON dbo.fact_journey (journey_date);
CREATE INDEX IX_fact_journey_route ON dbo.fact_journey (dep_station_key, arr_station_key);
GO
SELECT COUNT(*) AS loaded FROM dbo.fact_journey;
------------------------------------------------------------------------------------------------
CREATE TABLE dbo.dim_date (
    [Date]     DATE        NOT NULL CONSTRAINT PK_dim_date PRIMARY KEY,
    [Year]     INT         NOT NULL,
    [Month]    INT         NOT NULL,
    [DayName]  VARCHAR(15) NOT NULL
)

DECLARE @StartDate DATE = (SELECT MIN(purchase_date) FROM dbo.fact_journey);
DECLARE @EndDate   DATE = (SELECT MAX(journey_date)  FROM dbo.fact_journey);

;WITH CalendarCTE AS (
    SELECT @StartDate AS dt
    UNION ALL
    SELECT DATEADD(DAY, 1, dt)
    FROM CalendarCTE
    WHERE dt < @EndDate
)
INSERT INTO dbo.dim_date ([Date], [Year], [Month], [DayName])
SELECT
    dt,
    YEAR(dt),
    MONTH(dt),
    DATENAME(WEEKDAY, dt)
FROM CalendarCTE
OPTION (MAXRECURSION 0);


ALTER TABLE dbo.fact_journey
ADD CONSTRAINT FK_journey_date FOREIGN KEY (journey_date) REFERENCES dbo.dim_date([Date]);

ALTER TABLE dbo.fact_weather_daily
ADD CONSTRAINT FK_weather_date FOREIGN KEY (weather_date) REFERENCES dbo.dim_date([Date]);

----------------------------------------------------------------------------------------------