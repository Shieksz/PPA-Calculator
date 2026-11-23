from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List

app = FastAPI(title="Value for Money Calculator")
templates = Jinja2Templates(directory="templates")

UNIT_CONFIG = {
    "weight": {
        "base_label": "kg",
        "sub_label": "100g",
        "sub_factor": 0.1,
        "units": {
            "g": 0.001,
            "kg": 1.0,
            "oz": 0.0283495,
            "lb": 0.453592,
        },
    },
    "volume": {
        "base_label": "L",
        "sub_label": "100ml",
        "sub_factor": 0.1,
        "units": {
            "ml": 0.001,
            "cl": 0.01,
            "L": 1.0,
            "fl oz (UK)": 0.0284131,
            "pt (UK)": 0.568261,
        },
    },
    "count": {
        "base_label": "item",
        "sub_label": "100 items",
        "sub_factor": 100.0,
        "units": {
            "items": 1.0,
            "sheets": 1.0,
            "rolls": 1.0,
        },
    },
}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "unit_config": UNIT_CONFIG,
            "selected_category": "weight",
            "results": None,
        },
    )


@app.post("/calculate", response_class=HTMLResponse)
async def calculate(
    request: Request,
    category: str = Form(...),
    name: List[str] = Form(...),
    price: List[float] = Form(...),
    pack_qty: List[int] = Form(...),
    size: List[float] = Form(...),
    unit: List[str] = Form(...),
):
    config = UNIT_CONFIG.get(category, UNIT_CONFIG["weight"])
    items = []

    for i in range(len(price)):
        if price[i] <= 0 or size[i] <= 0 or pack_qty[i] <= 0:
            continue

        factor = config["units"].get(unit[i], 1.0)
        total_base_qty = pack_qty[i] * size[i] * factor
        unit_price = price[i] / total_base_qty
        sub_unit_price = unit_price * config["sub_factor"]

        label = name[i].strip() if name[i].strip() else f"Option {i + 1}"
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

    if items:
        best_price = min(x["unit_price"] for x in items)
        worst_price = max(x["unit_price"] for x in items)

        for item in items:
            item["is_best"] = item["unit_price"] == best_price
            if worst_price > best_price:
                item["savings_pct"] = round(
                    ((worst_price - item["unit_price"]) / worst_price) * 100, 1
                )
            else:
                item["savings_pct"] = 0.0

        items.sort(key=lambda x: x["unit_price"])

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
