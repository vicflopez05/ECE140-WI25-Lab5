from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import mysql.connector
from mysql.connector import Error
import os

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'mysql'),
    'user': os.getenv('DB_USER', 'user'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'database': os.getenv('DB_NAME', 'retail_db')
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/initdb")
async def init_db():
    try:
        with get_db_connection() as connection:
            if connection is None:
                return {"error": "Could not connect to database"}
            
            cursor = connection.cursor()
            
            with open('sql/init.sql', 'r') as file:
                init_script = file.read()
            
            # Drop existing tables if they exist
            cursor.execute("DROP TABLE IF EXISTS order_items")
            cursor.execute("DROP TABLE IF EXISTS orders")
            cursor.execute("DROP TABLE IF EXISTS products")
            cursor.execute("DROP TABLE IF EXISTS customers")
            connection.commit()
            
            # Split and execute statements
            statements = [stmt.strip() for stmt in init_script.split(';') if stmt.strip()]
            for statement in statements:
                try:
                    cursor.execute(statement)
                    connection.commit()
                except Error as e:
                    print(f"Error executing statement: {statement[:100]}...")
                    print(f"Error message: {str(e)}")
                    return {"error": f"Error during initialization: {str(e)}"}
            
            # Verify data was inserted
            tables = ['customers', 'products', 'orders', 'order_items']
            counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                counts[table] = count
                if count == 0:
                    return {"error": f"Table {table} is empty after initialization"}
            
            return {
                "message": "Database initialized successfully",
                "table_counts": counts
            }
            
    except Error as e:
        print(f"Database error during initialization: {str(e)}")
        return {"error": f"Database error: {str(e)}"}
    except Exception as e:
        print(f"Unexpected error during initialization: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}

@app.get("/table/{table_name}")
async def get_table_data(table_name: str):
    valid_tables = {
        'customers': "SELECT * FROM customers LIMIT 50",
        'orders': "SELECT * FROM orders LIMIT 50",
        'products': "SELECT * FROM products LIMIT 50",
        'orderItems': "SELECT * FROM order_items LIMIT 50"
    }
    
    if table_name not in valid_tables:
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    try:
        with get_db_connection() as connection:
            if connection is None:
                return {"error": "Could not connect to database"}
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(valid_tables[table_name])
            results = cursor.fetchall()
            return {"data": results}
            
    except Error as e:
        return {"error": f"Database error: {str(e)}"}

# Template routes for lab
@app.get("/assignment1")
async def assignment1():
    # Basic JOIN query
    try:
        with get_db_connection() as connection:
            if connection is None:
                return {"error": "Could not connect to database"}

            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT
                    customers.name,
                    customers.email,
                    orders.total_amount
                FROM customers
                INNER JOIN orders
                ON customers.customer_id = orders.customer_id
                ORDER BY orders.total_amount DESC
                """
            )

            results = cursor.fetchall()
            return {"data": results}

    except Error as e:
        return {"error": f"Database error: {str(e)}"}

@app.get("/assignment2")
async def assignment2():
    # GROUP BY query
    try:
        with get_db_connection() as connection:
            if connection is None:
                return {"error": "Could not connect to database"}

            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT
                    products.category as category,
                    COUNT(DISTINCT order_items.order_id) as total_orders,
                    SUM(order_items.quantity * order_items.unit_price) as total_revenue,
                    AVG(order_items.unit_price) as avg_order_value
                FROM products
                INNER JOIN order_items
                ON products.product_id = order_items.product_id
                GROUP BY products.category
                ORDER BY total_revenue DESC
                """
            )

            results = cursor.fetchall()
            return {"data": results}

    except Error as e:
        return {"error": f"Database error: {str(e)}"}

@app.get("/assignment3")
async def assignment3():
    # Complex JOIN with GROUP BY
    try:
        with get_db_connection() as connection:
            if connection is None:
                return {"error": "Could not connect to database"}

            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT
                    customers.membership_level,
                    customers.city,
                    COUNT(orders.customer_id) as total_orders,
                    AVG(orders.total_amount) as avg_order_value,
                    COUNT(DISTINCT orders.customer_id) as customer_count,
                    COUNT(orders.customer_id)/COUNT(DISTINCT orders.customer_id) as orders_per_customer
                FROM customers
                INNER JOIN orders
                ON customers.customer_id = orders.customer_id
                GROUP BY customers.membership_level, customers.city
                ORDER BY customers.membership_level
                """
            )

            results = cursor.fetchall()
            return {"data": results}

    except Error as e:
        return {"error": f"Database error: {str(e)}"}

@app.get("/assignment4")
async def assignment4():
    # Subquery
    try:
        with get_db_connection() as connection:
            if connection is None:
                return {"error": "Could not connect to database"}

            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT
                    name,
                    category,
                    total_sales,
                    (total_sales / total_orders) as category_avg,
                    (((total_sales - (total_sales / total_orders)) / (total_sales / total_orders)) * 100) as percent_above_avg
                FROM (
                    SELECT
                        products.name as name,
                        products.category as category,
                        SUM(order_items.quantity * order_items.unit_price) as total_sales,
                        COUNT(order_items.product_id) as total_orders
                    FROM products
                    INNER JOIN order_items
                    ON products.product_id = order_items.product_id
                    GROUP BY products.name, products.category
                ) as a_4
                WHERE total_orders > 1
                ORDER BY percent_above_avg DESC
                """
            )

            results = cursor.fetchall()
            return {"data": results}

    except Error as e:
        return {"error": f"Database error: {str(e)}"}
