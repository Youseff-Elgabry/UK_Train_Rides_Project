import math
import re
import time
import urllib.parse
from pathlib import Path
from urllib.parse import quote_plus
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from sqlalchemy import create_engine


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"[\uE000-\uF8FF\u202F\u00A0]+", " ", str(text))
    text = re.sub(r"\s*·\s*·\s*", " · ", text)
    text = re.sub(r"\s*\|\s*", " | ", text)
    text = re.sub(r"\s+", " ", text).strip(" ·|")
    return text


def extract_coords_from_url(url):
    if not url:
        return None, None
    s = str(url)
    m = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", s)
    if m:
        return float(m.group(1)), float(m.group(2))
    m2 = re.search(r"/@(-?\d+\.\d+),(-?\d+\.\d+)", s)
    if m2:
        return float(m2.group(1)), float(m2.group(2))
    return None, None


def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def shorten_maps_url(url):
    if not url:
        return ""
    clean_url = str(url).strip()
    if "/maps/place/" in clean_url:
        idx_data = clean_url.find("/data=")
        if idx_data != -1:
            return clean_url[:idx_data]
        idx_at = clean_url.find("/@")
        if idx_at != -1:
            return clean_url[:idx_at]
    return clean_url


def normalize_time_token(token):
    t = re.sub(r"\s+", " ", str(token or "").strip().upper())
    t = re.sub(r"([0-9])([AP]M)$", r"\1 \2", t)
    return t if t else "Not Listed"


def parse_open_close_hours(raw_hours):
    s = clean_text(raw_hours)
    if not s or s.lower() == "not listed":
        return "Not Listed", "Not Listed"

    low = s.lower()
    if "open 24 hours" in low:
        return "Open 24 Hours", "Open 24 Hours"
    if "temporarily closed" in low:
        return "Temporarily Closed", "Temporarily Closed"
    if "permanently closed" in low:
        return "Permanently Closed", "Permanently Closed"

    s_clean = re.sub(
        r"\b(?:mon(?:day)?|tue(?:s|sday)?|wed(?:nesday)?|thu(?:rs|rsday)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)\b",
        "",
        s,
        flags=re.I,
    )
    s_clean = re.sub(r"\s+", " ", s_clean).strip(" ·|-")

    m_opens = re.search(
        r"\bOpens?\s*(?:at)?\s*([0-9]{1,2}(?::[0-9]{2})?\s*(?:AM|PM)?)",
        s_clean,
        re.I,
    )
    m_closes = re.search(
        r"\bCloses?(?:\s+soon)?\s*(?:at)?\s*[·\s]*([0-9]{1,2}(?::[0-9]{2})?\s*(?:AM|PM)?)",
        s_clean,
        re.I,
    )

    open_val = normalize_time_token(m_opens.group(1)) if m_opens else "Not Listed"
    close_val = normalize_time_token(m_closes.group(1)) if m_closes else "Not Listed"

    return open_val, close_val


def parse_card_details(place_name, lines):
    p_clean = clean_text(place_name).lower()
    filtered_lines = []
    for ln in lines:
        c_ln = clean_text(ln)
        if not c_ln:
            continue
        if p_clean and c_ln.lower() == p_clean:
            continue
        filtered_lines.append(c_ln)

    joined = " | ".join(filtered_lines)
    if p_clean and joined.lower().startswith(p_clean):
        joined = joined[len(p_clean):].lstrip(" |·-")

    rating = None
    reviews_count = None

    m_both = re.search(r"\b([1-5]\.\d)\s*\(\s*([\d,]+)\s*\)", joined)
    if m_both:
        rating = float(m_both.group(1))
        reviews_count = int(m_both.group(2).replace(",", ""))
        joined = (joined[:m_both.start()] + " | " + joined[m_both.end():]).strip(" |·-")
    else:
        m_rating = re.search(r"\b([1-5]\.\d)\b", joined)
        if m_rating:
            rating = float(m_rating.group(1))
            joined = (joined[:m_rating.start()] + " | " + joined[m_rating.end():]).strip(" |·-")

    parts = [clean_text(p) for p in joined.split("|") if clean_text(p)]
    hours_keywords = [
        "open 24 hours",
        "closes soon",
        "opens ",
        "closed",
        "open ·",
        "closes ",
        "temporarily closed",
        "permanently closed",
    ]

    hours_list = []
    desc_list = []

    for part in parts:
        low = part.lower()
        if any(kw in low for kw in hours_keywords):
            hours_list.append(part)
        else:
            desc_list.append(part)

    raw_hours = " | ".join(dict.fromkeys(hours_list)) if hours_list else "Not Listed"
    opening_hours, closing_hours = parse_open_close_hours(raw_hours)

    full_desc = " | ".join(dict.fromkeys(desc_list)) if desc_list else "Not Listed"
    if full_desc == "Not Listed":
        category = "Other"
        description = "Not Listed"
    else:
        split_parts = re.split(r"\s*[·|]\s*", full_desc, maxsplit=1)
        category = split_parts[0].strip() if split_parts[0].strip() else "Other"
        description = split_parts[1].strip() if len(split_parts) > 1 and split_parts[1].strip() else "Not Listed"

    return {
        "category": category,
        "description": description,
        "rating": rating,
        "reviews_count": reviews_count,
        "opening_hours": opening_hours,
        "closing_hours": closing_hours,
    }


def click_consent_if_present(driver):
    xpaths = [
        "//button[contains(., 'Accept all')]",
        "//button[contains(., 'Reject all')]",
        "//button[contains(., 'موافق')]",
        "//button[contains(., 'رفض')]",
    ]
    for xp in xpaths:
        try:
            for b in driver.find_elements(By.XPATH, xp):
                if b.is_displayed():
                    b.click()
                    time.sleep(1.5)
                    return
        except Exception:
            continue


def scroll_feed(driver, scrolls=10):
    try:
        feed = driver.find_element(By.CSS_SELECTOR, "div[role='feed']")
        for _ in range(scrolls):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
            time.sleep(1.5)
    except Exception:
        pass


def fetch_station_places(driver, lat, lon, st_name, query_text="things to do", max_items=25, scrolls=10, min_reviews=20):
    q = quote_plus(f"{query_text} near {st_name}")
    url = f"https://www.google.com/maps/search/{q}/@{lat},{lon},15z?hl=en"
    driver.get(url)
    time.sleep(4.0)
    click_consent_if_present(driver)
    time.sleep(2.0)
    scroll_feed(driver, scrolls=scrolls)

    cards = driver.find_elements(By.CSS_SELECTOR, "div[role='feed'] > div")
    results = []
    seen = set()

    for card in cards:
        links = card.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']")
        if not links:
            continue

        link = links[0]
        raw_href = link.get_attribute("href") or ""
        p_lat, p_lon = extract_coords_from_url(raw_href)
        dist_km = haversine_km(lat, lon, p_lat, p_lon)
        short_url = shorten_maps_url(raw_href)

        name = clean_text(link.get_attribute("aria-label") or "")
        lines = card.text.splitlines()
        if not name and lines:
            name = clean_text(lines[0])

        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())

        parsed = parse_card_details(name, lines)
        rev_count = parsed["reviews_count"] or 0
        cat_low = parsed["category"].lower()

        if rev_count < min_reviews or any(w in cat_low for w in ["transit", "train station", "subway"]):
            continue

        results.append({
            "place_name": name,
            "category": parsed["category"],
            "description": parsed["description"],
            "rating": parsed["rating"],
            "reviews_count": parsed["reviews_count"],
            "distance_km": dist_km,
            "opening_hours": parsed["opening_hours"],
            "closing_hours": parsed["closing_hours"],
            "maps_url": short_url,
        })

        if len(results) >= max_items:
            break

    return results


def write_to_sql_server(df, database_name="Railway_UK", table_name="uk_stations_nearby_places", server_name=r".\SQLEXPRESS"):
    params = urllib.parse.quote_plus(
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={server_name};"
        f"Database={database_name};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    df.to_sql(
        table_name,
        con=engine,
        schema="dbo",
        if_exists="replace",
        index=False,
    )
    print(f"Inserted {len(df)} rows into dbo.{table_name}")


def main():
    stations_df = pd.read_csv("Stations.csv")
    csv_path = Path("uk_stations_nearby_places_final.csv")

    if csv_path.exists():
        csv_path.unlink()

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)
    total_rows = 0

    try:
        for idx, row in stations_df.iterrows():
            loc_id = int(row["location_id"])
            st_name = str(row["Station_Name"]).strip()
            lat = float(row["Latitude"])
            lon = float(row["Longitude"])

            print(f"[{idx + 1}/{len(stations_df)}] ({loc_id}) {st_name}...")
            places = fetch_station_places(
                driver,
                lat,
                lon,
                st_name,
                query_text="things to do",
                max_items=25,
                scrolls=10,
                min_reviews=20,
            )

            if places:
                chunk = pd.DataFrame([
                    {
                        "location_id": loc_id,
                        "Station_Name": st_name,
                        "station_lat": lat,
                        "station_lon": lon,
                        **p,
                    }
                    for p in places
                ])
                chunk.to_csv(
                    csv_path,
                    mode="a",
                    header=not csv_path.exists(),
                    index=False,
                    encoding="utf-8-sig",
                )
                total_rows += len(chunk)

            print(f"   -> Saved {len(places)} rows (Total: {total_rows})")
            time.sleep(2.0)
    finally:
        driver.quit()

    if csv_path.exists():
        final_df = pd.read_csv(csv_path)
        print(f"\nDone! Total rows: {len(final_df)} -> {csv_path.resolve()}")
        write_to_sql_server(
            final_df,
            database_name="Railway_UK",
            table_name="uk_stations_nearby_places",
            server_name=r".\SQLEXPRESS",
        )
    else:
        print("\nNo rows were saved.")


if __name__ == "__main__":
    main()