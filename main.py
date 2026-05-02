from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery

PROJECT = "sp26-mgmt54500-dev"
DATASET = "uncle_joes"

app = FastAPI(title="Uncle Joe's API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = bigquery.Client(project=PROJECT)


@app.get("/")
def root():
    return {
        "message": "Uncle Joe's API is running",
        "project": PROJECT,
        "dataset": DATASET,
    }


@app.get("/locations")
def get_locations(
    state: Optional[str] = Query(None, description="Filter locations by state abbreviation"),
    city: Optional[str] = Query(None, description="Filter locations by city"),
    open_only: Optional[bool] = Query(None, description="Return only open-for-business locations"),
):
    where_clauses = []
    query_parameters = []

    if state:
        where_clauses.append("LOWER(state) = LOWER(@state)")
        query_parameters.append(
            bigquery.ScalarQueryParameter("state", "STRING", state)
        )

    if city:
        where_clauses.append("LOWER(city) = LOWER(@city)")
        query_parameters.append(
            bigquery.ScalarQueryParameter("city", "STRING", city)
        )

    if open_only is not None:
        where_clauses.append("open_for_business = @open_only")
        query_parameters.append(
            bigquery.ScalarQueryParameter("open_only", "BOOL", open_only)
        )

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    query = f"""
        SELECT
            id,
            open_for_business,
            city,
            state,
            wifi,
            drive_thru,
            door_dash,
            email,
            phone_number,
            fax_number,
            location_map_address,
            location_map_lat,
            location_map_lng,
            address_one,
            address_two,
            zip_code,
            near_by,
            hours_monday_open,
            hours_monday_close,
            hours_tuesday_open,
            hours_tuesday_close,
            hours_wednesday_open,
            hours_wednesday_close,
            hours_thursday_open,
            hours_thursday_close,
            hours_friday_open,
            hours_friday_close,
            hours_saturday_open,
            hours_saturday_close,
            hours_sunday_open,
            hours_sunday_close
        FROM `{PROJECT}.{DATASET}.locations`
        {where_sql}
        ORDER BY open_for_business DESC, state, city, address_one
    """

    job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)

    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


@app.get("/locations/{location_id}")
def get_location(location_id: str):
    query = f"""
        SELECT
            id,
            open_for_business,
            city,
            state,
            wifi,
            drive_thru,
            door_dash,
            email,
            phone_number,
            fax_number,
            location_map_address,
            location_map_lat,
            location_map_lng,
            address_one,
            address_two,
            zip_code,
            near_by,
            hours_monday_open,
            hours_monday_close,
            hours_tuesday_open,
            hours_tuesday_close,
            hours_wednesday_open,
            hours_wednesday_close,
            hours_thursday_open,
            hours_thursday_close,
            hours_friday_open,
            hours_friday_close,
            hours_saturday_open,
            hours_saturday_close,
            hours_sunday_open,
            hours_sunday_close
        FROM `{PROJECT}.{DATASET}.locations`
        WHERE id = @location_id
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("location_id", "STRING", location_id),
        ]
    )

    results = list(client.query(query, job_config=job_config).result())

    if not results:
        raise HTTPException(status_code=404, detail="Location not found")

    return dict(results[0])


@app.get("/menu")
def get_menu(
    category: Optional[str] = Query(None, description="Filter menu items by category"),
):
    where_sql = ""
    query_parameters = []

    if category:
        where_sql = "WHERE LOWER(category) = LOWER(@category)"
        query_parameters.append(
            bigquery.ScalarQueryParameter("category", "STRING", category)
        )

    query = f"""
        SELECT
            id,
            name,
            category,
            size,
            calories,
            price
        FROM `{PROJECT}.{DATASET}.menu_items`
        {where_sql}
        ORDER BY category, name, size
    """

    job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)

    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


@app.get("/menu/{item_id}")
def get_menu_item(item_id: str):
    query = f"""
        SELECT
            id,
            name,
            category,
            size,
            calories,
            price
        FROM `{PROJECT}.{DATASET}.menu_items`
        WHERE id = @item_id
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("item_id", "STRING", item_id),
        ]
    )

    results = list(client.query(query, job_config=job_config).result())

    if not results:
        raise HTTPException(status_code=404, detail="Item not found")

    return dict(results[0])