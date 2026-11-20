create database Railway_UK
use[Railway_UK]
--------------------------------
select * from [dbo].[railway_raw]
--------------------------------
------------------------Count Nulls in Key Columns--------------------
SELECT
    COUNT(*) AS Total_Rows,

    SUM(CASE WHEN Railcard IS NULL
        THEN 1 ELSE 0 END) AS Missing_Railcard,

    SUM(CASE WHEN [Actual_Arrival_Time] IS NULL
        THEN 1 ELSE 0 END) AS Missing_Actual_Arrival,

    SUM(CASE WHEN [Reason_for_Delay] IS NULL
        THEN 1 ELSE 0 END) AS Missing_Reason

FROM dbo.railway_raw
------------------------------Check Duplicate Transaction ID---------------------------------
SELECT
    [Transaction_ID],
    COUNT(*) AS Duplicate_Count
FROM dbo.railway_raw
GROUP BY [Transaction_ID]
HAVING COUNT(*) > 1
--------------------------------------------------------------------------------------------
SELECT DISTINCT Railcard
FROM dbo.railway_raw

SELECT DISTINCT Journey_Status
FROM dbo.railway_raw

SELECT DISTINCT Ticket_Type
FROM dbo.railway_raw

SELECT DISTINCT Payment_Method
FROM dbo.railway_raw

SELECT DISTINCT Ticket_Class
FROM dbo.railway_raw
----------------------------------------Problem----------------------------------------------------
SELECT DISTINCT Reason_for_Delay
FROM dbo.railway_raw
---------------------------------------Solution--------------------------------------------
UPDATE dbo.railway
SET Reason_for_Delay = 'Weather'
WHERE Reason_for_Delay = 'Weather Conditions'

UPDATE dbo.railway
SET Reason_for_Delay = 'Staffing'
WHERE Reason_for_Delay = 'Staff Shortage'

UPDATE dbo.railway
SET Reason_for_Delay = 'Signal Failure'
WHERE Reason_for_Delay = 'Signal failure'

UPDATE dbo.railway
SET Reason_for_Delay = 'No Delay'
WHERE Journey_Status = 'On Time' AND Reason_for_Delay IS NULL
----------------------------------------Check--------------------------------------------------
SELECT DISTINCT Reason_for_Delay
FROM dbo.railway
-------------------------------------------------------------------------------------------
SELECT
    Journey_Status,
    COUNT(*) AS Missing_Arrival
FROM dbo.railway
WHERE Actual_Arrival_Time IS NULL
GROUP BY Journey_Status
------------------------------------check_price-------------------------------------------------
SELECT
    MIN(Price) AS Minimum_Price,
    MAX(Price) AS Maximum_Price,
    AVG(Price) AS Average_Price
FROM dbo.railway_raw

SELECT *
FROM dbo.railway_raw
WHERE Price <= 0
--------------------------------------Check_Date_of_Purchase------------------------------------------
SELECT *
FROM dbo.railway_raw
WHERE Date_of_Purchase > Date_of_Journey
--------------------------------------Check_Stations(Problem)-----------------------------------------
SELECT DISTINCT Departure_Station
FROM dbo.railway_raw
ORDER BY Departure_Station

SELECT DISTINCT Arrival_Destination
FROM dbo.railway_raw
ORDER BY Arrival_Destination
-----------------------------------------Solution---------------------------------------------------
UPDATE dbo.railway
SET Departure_Station = 'Edinburgh'
WHERE Departure_Station = 'Edinburgh Waverley'

UPDATE dbo.railway
SET Arrival_Destination = 'Edinburgh'
WHERE Arrival_Destination = 'Edinburgh Waverley'
------------------------------------------Chcek-----------------------------------------------------
SELECT DISTINCT Departure_Station
FROM dbo.railway
ORDER BY Departure_Station

SELECT DISTINCT Arrival_Destination
FROM dbo.railway
ORDER BY Arrival_Destination
----------------------------------------------------------------------------------------------------
SELECT
    SUM(CASE WHEN Railcard IS NULL THEN 1 ELSE 0 END) AS Missing_Railcard,
    SUM(CASE WHEN Actual_Arrival_Time IS NULL THEN 1 ELSE 0 END) AS Missing_Actual_Arrival,
    SUM(CASE WHEN Reason_for_Delay IS NULL THEN 1 ELSE 0 END) AS Missing_Reason
FROM dbo.railway_raw
--------------------------------------------------------------------------------------------
