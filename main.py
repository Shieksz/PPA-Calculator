# Import FastAPI core classes for handling requests, HTML responses, and form inputs
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse

# Import Jinja2Templates to render HTML files from the 'templates' folder
from fastapi.templating import Jinja2Templates

# Import List type hint so FastAPI knows our form sends multiple rows of items at once
from typing import List

# Initialize the FastAPI web application
app = FastAPI(title="Value for Money Calculator")

# Point Jinja2 to the folder containing our HTML files
templates = Jinja2Templates(directory="templates")

# Master configuration dictionary defining conversion rates into standard base units:
# - Weight converts everything to 1 kg (and shows a secondary rate per 100g)
# - Volume converts everything to 1 L (and shows a secondary rate per 100ml)
# - Count keeps 1 item as the base (and shows a secondary rate per 100 items)
UNIT_CONFIG = {
    "weight": {
        "base_label": "kg",
        "sub_label": "100g",
        "sub_factor": 0.1,  # 100g is 0.1 of 1kg
        "units": {
            "g": 0.001,       # 1 gram = 0.001 kg
            "kg": 1.0,        # 1 kilogram = 1 kg
            "oz": 0.0283495,  # 1 ounce = 0.0283495 kg
            "lb": 0.453592,   # 1 pound = 0.453592 kg
        },
    },
    "volume": {
        "base_label": "L",
        "sub_label": "100ml",
        "sub_factor": 0.1,  # 100ml is 0.1 of 1L
        "units": {
            "ml": 0.001,          # 1 millilitre = 0.001 L
            "cl": 0.01,           # 1 centilitre = 0.01 L
            "L": 1.0,             # 1 litre = 1 L
            "fl oz (UK)": 0.0284131,  # 1 UK fluid ounce = 0.0284131 L
            "pt (UK)": 0.568261,      # 1 UK pint = 0.568261 L
        },
    },
    "count": {
        "base_label": "item",
        "sub_label": "100 items",
        "sub_factor": 100.0,  # Secondary display multiplies per-item cost by 100
        "units": {
            "items": 1.0,
            "sheets": 1.0,
            "rolls": 1.0,
        },
    },
}


# GET route for the homepage ("/") — loads the initial empty calculator
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,  # Required by Jinja2Templates
            "unit_config": UNIT_CONFIG,  # Passes unit dropdown options to the HTML
            "selected_category": "weight",  # Defaults the radio button to 'weight'
            "results": None,  # No calculation results yet on first page load
        },
    )


# POST route ("/calculate") — runs when the user clicks "Compare Value"
@app.post("/calculate", response_class=HTMLResponse)
async def calculate(
    request: Request,
    category: str = Form(...),          # Selected category ('weight', 'volume', or 'count')
    name: List[str] = Form(...),        # List of product names from all rows
    price: List[float] = Form(...),     # List of prices from all rows
    pack_qty: List[int] = Form(...),    # List of pack counts (e.g., 6 for a 6-pack)
    size: List[float] = Form(...),      # List of individual item sizes (e.g., 330)
    unit: List[str] = Form(...),        # List of selected units (e.g., 'ml')
):
    # Look up conversion rules for the chosen category (fallback to 'weight')
    config = UNIT_CONFIG.get(category, UNIT_CONFIG["weight"])
    items = []

    # Loop through each submitted product row by index
    for i in range(len(price)):
        # Skip invalid rows where price, size, or pack quantity is zero or negative
        if price[i] <= 0 or size[i] <= 0 or pack_qty[i] <= 0:
            continue

        # Convert the item's total quantity into the standard base unit (kg, L, or item)
        factor = config["units"].get(unit[i], 1.0)
        total_base_qty = pack_qty[i] * size[i] * factor

        # Calculate true unit price (e.g., £/kg) and sub-unit price (e.g., £/100g)
        unit_price = price[i] / total_base_qty
        sub_unit_price = unit_price * config["sub_factor"]

        # Use "Option 1", "Option 2", etc. if the user left the product name blank
        label = name[i].strip() if name[i].strip() else f"Option {i + 1}"

        # Store all calculated values for this product in a dictionary
        items.append(
            {
                "name": label,
                "price": price[i],
                "pack_qty": pack_qty[i],
                "size": size[i],
                "unit": unit[i],
                "unit_price": unit_price,
                "sub_unit_price": sub_unit_price,
            }
        )

    # If at least one valid item was entered, rank them and calculate percentage savings
    if items:
        best_price = min(x["unit_price"] for x in items)   # Lowest (cheapest) unit price
        worst_price = max(x["unit_price"] for x in items)  # Highest (most expensive) unit price

        for item in items:
            # Flag the cheapest item(s) so the UI can show the "Best Value" badge
            item["is_best"] = item["unit_price"] == best_price

            # Calculate % saved compared to the most expensive option in the list
            if worst_price > best_price:
                item["savings_pct"] = round(
                    ((worst_price - item["unit_price"]) / worst_price) * 100, 1
                )
            else:
                item["savings_pct"] = 0.0

        # Sort the list from cheapest unit price to most expensive
        items.sort(key=lambda x: x["unit_price"])

    # Re-render the same HTML page, now passing in the sorted 'results' list
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "unit_config": UNIT_CONFIG,
            "selected_category": category,
            "results": items,
            "base_label": config["base_label"],
            "sub_label": config["sub_label"],
        },
    )
