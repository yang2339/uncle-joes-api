from typing import Optional, Dict, Any, List

import bcrypt
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from pydantic import BaseModel


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


# -----------------------------
# Pydantic Models
# -----------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


# -----------------------------
# Helper Functions
# -----------------------------

def to_float(value):
    if value is None:
        return 0.0
    return float(value)


def to_int(value):
    if value is None:
        return 0
    return int(value)


def row_to_dict(row) -> Dict[str, Any]:
    return dict(row)


# -----------------------------
# Root
# -----------------------------

@app.get("/")
def root():
    return {
        "message": "Uncle Joe's API is running",
        "project": PROJECT,
        "dataset": DATASET,
    }


# -----------------------------
# GP2: Locations Endpoints
# -----------------------------

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

    return [row_to_dict(row) for row in rows]


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

    return row_to_dict(results[0])


# -----------------------------
# GP2: Menu Endpoints
# -----------------------------

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

    return [row_to_dict(row) for row in rows]


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

    return row_to_dict(results[0])


# -----------------------------
# GP3: Login Endpoint
# -----------------------------

@app.post("/login")
def login_member(login: LoginRequest):
    query = f"""
        SELECT
            id,
            first_name,
            last_name,
            email,
            phone_number,
            home_store,
            password,
            api_token
        FROM `{PROJECT}.{DATASET}.members`
        WHERE LOWER(email) = LOWER(@member_email)
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("member_email", "STRING", login.email),
        ]
    )

    results = list(client.query(query, job_config=job_config).result())

    if not results:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    member = row_to_dict(results[0])
    stored_password_hash = member.get("password")

    if not stored_password_hash:
        raise HTTPException(
            status_code=500,
            detail="Password hash is missing for this member"
        )

    password_ok = bcrypt.checkpw(
        login.password.encode("utf-8"),
        stored_password_hash.encode("utf-8")
    )

    if not password_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Never return the stored password hash to the frontend.
    member.pop("password", None)

    return {
        "success": True,
        "message": "Login successful",
        "member": member,
    }


# -----------------------------
# GP3 Optional-Safe: Member Profile
# -----------------------------

@app.get("/members/{member_id}")
def get_member(member_id: str):
    query = f"""
        SELECT
            m.id,
            m.first_name,
            m.last_name,
            m.email,
            m.phone_number,
            m.home_store,
            l.city AS home_store_city,
            l.state AS home_store_state,
            l.address_one AS home_store_address
        FROM `{PROJECT}.{DATASET}.members` m
        LEFT JOIN `{PROJECT}.{DATASET}.locations` l
            ON m.home_store = l.id
        WHERE m.id = @member_id
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("member_id", "STRING", member_id),
        ]
    )

    results = list(client.query(query, job_config=job_config).result())

    if not results:
        raise HTTPException(status_code=404, detail="Member not found")

    member = row_to_dict(results[0])

    return {
        "id": member.get("id"),
        "first_name": member.get("first_name"),
        "last_name": member.get("last_name"),
        "email": member.get("email"),
        "phone_number": member.get("phone_number"),
        "home_store": {
            "id": member.get("home_store"),
            "city": member.get("home_store_city"),
            "state": member.get("home_store_state"),
            "address": member.get("home_store_address"),
        },
    }


# -----------------------------
# GP3: Member Order History
# -----------------------------

@app.get("/members/{member_id}/orders")
def get_member_orders(member_id: str):
    query = f"""
        SELECT
            o.order_id,
            o.member_id,
            o.store_id,
            o.order_date,
            o.items_subtotal,
            o.order_discount,
            o.order_subtotal,
            o.sales_tax,
            o.order_total,

            l.city AS store_city,
            l.state AS store_state,
            l.address_one AS store_address,

            oi.id AS order_item_id,
            oi.menu_item_id,
            oi.item_name,
            oi.size,
            oi.quantity,
            oi.price

        FROM `{PROJECT}.{DATASET}.orders` o
        LEFT JOIN `{PROJECT}.{DATASET}.locations` l
            ON o.store_id = l.id
        LEFT JOIN `{PROJECT}.{DATASET}.order_items` oi
            ON o.order_id = oi.order_id
        WHERE o.member_id = @member_id
        ORDER BY o.order_date DESC, o.order_id, oi.item_name
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("member_id", "STRING", member_id),
        ]
    )

    rows = list(client.query(query, job_config=job_config).result())

    orders: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        row_dict = row_to_dict(row)
        order_id = row_dict["order_id"]

        if order_id not in orders:
            order_date = row_dict.get("order_date")
            orders[order_id] = {
                "order_id": order_id,
                "member_id": row_dict.get("member_id"),
                "store_id": row_dict.get("store_id"),
                "order_date": str(order_date) if order_date is not None else None,
                "store_location": {
                    "city": row_dict.get("store_city"),
                    "state": row_dict.get("store_state"),
                    "address": row_dict.get("store_address"),
                },
                "items_subtotal": to_float(row_dict.get("items_subtotal")),
                "order_discount": to_float(row_dict.get("order_discount")),
                "order_subtotal": to_float(row_dict.get("order_subtotal")),
                "sales_tax": to_float(row_dict.get("sales_tax")),
                "order_total": to_float(row_dict.get("order_total")),
                "points_earned": int(to_float(row_dict.get("order_total")) // 1),
                "items": [],
            }

        if row_dict.get("order_item_id") is not None:
            orders[order_id]["items"].append({
                "order_item_id": row_dict.get("order_item_id"),
                "menu_item_id": row_dict.get("menu_item_id"),
                "item_name": row_dict.get("item_name"),
                "size": row_dict.get("size"),
                "quantity": to_int(row_dict.get("quantity")),
                "price": to_float(row_dict.get("price")),
            })

    return list(orders.values())


# -----------------------------
# GP3: Member Points Balance
# -----------------------------

@app.get("/members/{member_id}/points")
def get_member_points(member_id: str):
    query = f"""
        SELECT
            @member_id AS member_id,
            COALESCE(SUM(FLOOR(order_total)), 0) AS points_balance
        FROM `{PROJECT}.{DATASET}.orders`
        WHERE member_id = @member_id
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("member_id", "STRING", member_id),
        ]
    )

    rows = list(client.query(query, job_config=job_config).result())

    if not rows:
        return {
            "member_id": member_id,
            "points_balance": 0
        }

    row = row_to_dict(rows[0])

    return {
        "member_id": row.get("member_id"),
        "points_balance": int(row.get("points_balance") or 0)
    }


# -----------------------------
# GP3 Optional-Safe: Points History
# -----------------------------

@app.get("/members/{member_id}/points-history")
def get_member_points_history(member_id: str):
    query = f"""
        SELECT
            order_id,
            order_date,
            order_total,
            FLOOR(order_total) AS points_earned
        FROM `{PROJECT}.{DATASET}.orders`
        WHERE member_id = @member_id
        ORDER BY order_date DESC, order_id
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("member_id", "STRING", member_id),
        ]
    )

    rows = list(client.query(query, job_config=job_config).result())

    history = []
    total_points = 0

    for row in rows:
        row_dict = row_to_dict(row)
        points = int(row_dict.get("points_earned") or 0)
        total_points += points

        order_date = row_dict.get("order_date")

        history.append({
            "order_id": row_dict.get("order_id"),
            "order_date": str(order_date) if order_date is not None else None,
            "order_total": to_float(row_dict.get("order_total")),
            "points_earned": points,
        })

    return {
        "member_id": member_id,
        "points_balance": total_points,
        "history": history,
    }