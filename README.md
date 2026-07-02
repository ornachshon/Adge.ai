# Facebook Ads Library Scraper

A Python-based web scraper that extracts advertisements from the Facebook Ads Library using Selenium, stores the results as CSV files, downloads ad assets, and maintains historical versions of each ad using a Slowly Changing Dimension Type 2 (SCD2) implementation in SQLite.

---

## Project Overview

This project was developed as part of a technical interview assignment.

The scraper:

- Navigates the Facebook Ads Library using Selenium.
- Scrapes both individual ads and grouped ("Summary") ads.
- Downloads the creative image for each advertisement.
- Exports every execution to a timestamped CSV file.
- Stores the data in a SQLite database.
- Preserves historical changes using a Slowly Changing Dimension Type 2 (SCD2) approach.
- Runs inside Docker for easy execution on any machine.

---

## Technologies

- Python 3.12
- Selenium
- Chrome / ChromeDriver
- Pandas
- SQLite
- Docker & Docker Compose
- Requests
- python-dotenv

---

## Project Structure

```
.
├── ad_assets/          # Downloaded ad images
├── csv_exports/        # CSV exports
├── database/
│   └── ads.db          # SQLite database
├── scraper.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env
└── README.md
```

---

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd <repository>
```

Create a `.env` file:

```text
FB_ADS_URL=https://www.facebook.com/ads/library/...
```

Build the Docker image:

```bash
docker compose build
```

Run the scraper:

```bash
docker compose up
```

---

## Output

Each execution produces:

### CSV Export

A timestamped CSV file:

```
csv_exports/
```

Example:

```
ads_export_2026-07-02_18-45-00.csv
```

---

### Downloaded Assets

Images are downloaded into:

```
ad_assets/
```

---

### SQLite Database

The database is created automatically:

```
database/ads.db
```

Example query:

```bash
sqlite3 database/ads.db
```

```sql
SELECT * FROM ads;
```

---

# Database Design

The project stores advertisements using a Slowly Changing Dimension Type 2 (SCD2) model.

Table:

| Column | Description |
|---------|-------------|
| record_id | Internal surrogate key |
| run_timestamp | Timestamp when this version became active |
| valid_to | End timestamp (NULL while current) |
| Asset Path | Downloaded image path |
| Source ID | Parent ad identifier |
| ID | Facebook Library ID |
| Status | Active / Inactive |
| Platform | Facebook, Instagram, etc. |
| Ad Text | Advertisement text |
| Start Date | Facebook start date |
| End Date | Facebook end date |

---

## Slowly Changing Dimension (SCD Type 2)

Instead of overwriting records, the scraper preserves history.

If an advertisement changes:

1. The previous record receives a `valid_to` timestamp.
2. A new row is inserted with the updated values.
3. The new row becomes the active version (`valid_to = NULL`).

Example:

| ID | Status | Ad Text | run_timestamp | valid_to |
|----|----------|----------------|----------------------|----------------------|
|123|Active|Old Text|2026-07-02 18:00|2026-07-02 18:10|
|123|Active|New Text|2026-07-02 18:10|NULL|

This allows complete historical tracking of every advertisement.

---

## Demonstration Mode

To demonstrate the SCD2 implementation during the interview, the project includes a helper function:

```python
simulate_change(df)
```

The function randomly modifies one advertisement before saving.

This intentionally creates a historical version in the database, allowing reviewers to easily verify the SCD2 implementation without waiting for real Facebook ads to change.

This function is intended for demonstration purposes only.

---

## Docker

The application is fully containerized.

Build:

```bash
docker compose build
```

Run:

```bash
docker compose up
```

No local Python installation is required.

---

## Notes

- The scraper is designed specifically for the Facebook Ads Library page provided through the environment variable.
- Chrome runs in headless mode inside Docker.
- Images, CSV files, and the SQLite database are persisted locally.

---

## Future Improvements

Possible enhancements include:

- PostgreSQL support
- Incremental scraping
- Scheduler (Cron / Airflow)
- Logging framework
- Unit and integration tests
- Retry mechanism for network failures
- CI/CD pipeline using GitHub Actions