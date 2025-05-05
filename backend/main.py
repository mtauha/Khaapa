import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime

from sheets import lookup_product, get_next_order_id, append_order, summarize_date
from auth import router as auth_router

# Load your .env yourself (e.g. with python-dotenv in uvicorn command or here)
# from dotenv import load_dotenv
# load_dotenv()

app = FastAPI()

# 1) Enable sessions so authlib can store state in request.session
app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "change-me-in-production")
)

# 2) CORS (if needed by your frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3) Mount the auth routes (/login, /auth/callback)
app.include_router(auth_router)


# 4) Root endpoint so / doesn’t 404
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Khaapa POS Backend"}


def get_current_session(request: Request):
    sk = request.cookies.get("session_key")
    if not sk:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sk


@app.get("/products/{barcode}")
def api_lookup(barcode: str, sk: str = Depends(get_current_session)):
    prod = lookup_product(barcode, sk)
    if not prod:
        raise HTTPException(status_code=404, detail="Not found")
    return prod


@app.get("/orders/next_id")
def api_next_id(sk: str = Depends(get_current_session)):
    return {"next_order_id": get_next_order_id(sk)}


@app.post("/orders")
def api_create_order(payload: dict, sk: str = Depends(get_current_session)):
    """
    payload:
    {
      "order_id": 1,
      "date_time": "2025-05-06 14:23:00",
      "pos": "Cash",
      "lines": [
        { "item_name": "Widget A", "quantity": 2 },
        { "item_name": "Widget B", "quantity": 1 }
      ]
    }
    """
    duty = sk  # or map sk → email if you’ve stored that elsewhere
    append_order(
        sk,
        payload["order_id"],
        payload["date_time"],
        payload["pos"],
        duty,
        payload["lines"],
    )
    return {"success": True}


@app.get("/summary")
def api_summary(date: str = None, sk: str = Depends(get_current_session)):
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    total_revenue = summarize_date(date, sk)
    return {"date": date, "total_revenue": total_revenue}
