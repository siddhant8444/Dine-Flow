import json
from datetime import datetime
from typing import List

from fastapi import FastAPI, Request, Depends, WebSocket, WebSocketDisconnect, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import case

from app.config import DATABASE_URL
from app.database import engine, get_db, Base
from app.models import (
    Restaurant, Table, MenuCategory, MenuItem,
    ModifierGroup, ModifierOption,
    Order, OrderItem, OrderItemModifier
)
from app.schemas import (
    PlaceOrderRequest, OrderItemRequest, OrderStatusUpdate,
    CategoryCreate, MenuItemCreate, ModifierGroupCreate, ModifierOptionCreate
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DineFlow")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["now"] = datetime.utcnow


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, List[WebSocket]] = {}

    async def connect(self, restaurant_id: int, websocket: WebSocket):
        await websocket.accept()
        if restaurant_id not in self.active_connections:
            self.active_connections[restaurant_id] = []
        self.active_connections[restaurant_id].append(websocket)

    def disconnect(self, restaurant_id: int, websocket: WebSocket):
        if restaurant_id in self.active_connections:
            self.active_connections[restaurant_id].remove(websocket)
            if not self.active_connections[restaurant_id]:
                del self.active_connections[restaurant_id]

    async def broadcast(self, restaurant_id: int, message: dict):
        if restaurant_id in self.active_connections:
            for ws in self.active_connections[restaurant_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


def get_restaurant_by_slug(slug: str, db: Session) -> Restaurant:
    rest = db.query(Restaurant).filter(Restaurant.slug == slug).first()
    if not rest:
        raise HTTPException(404, "Restaurant not found")
    return rest


# ─── Customer Routes ─────────────────────────────────────────────────

@app.get("/{slug}/menu/{table_token}", response_class=HTMLResponse)
async def customer_menu(slug: str, table_token: str, lang: str = "en", db: Session = Depends(get_db)):
    restaurant = get_restaurant_by_slug(slug, db)
    table = db.query(Table).filter(Table.qr_token == table_token, Table.restaurant_id == restaurant.id).first()
    if not table:
        raise HTTPException(404, "Table not found")

    categories = db.query(MenuCategory).filter(
        MenuCategory.restaurant_id == restaurant.id
    ).order_by(MenuCategory.sort_order).all()

    return templates.TemplateResponse("customer/menu.html", {
        "request": {},
        "restaurant": restaurant,
        "table": table,
        "categories": categories,
        "lang": lang,
    })


@app.post("/{slug}/order")
async def place_order(slug: str, body: PlaceOrderRequest, db: Session = Depends(get_db)):
    restaurant = get_restaurant_by_slug(slug, db)
    table = db.query(Table).filter(
        Table.qr_token == body.table_token,
        Table.restaurant_id == restaurant.id
    ).first()
    if not table:
        raise HTTPException(404, "Table not found")

    order = Order(table_id=table.id, status="placed")
    db.add(order)
    db.flush()

    total = 0.0
    for item_req in body.items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == item_req.menu_item_id).first()
        if not menu_item:
            continue
        unit_price = menu_item.price
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=item_req.quantity,
            notes=item_req.notes,
            unit_price=menu_item.price,
        )
        db.add(order_item)
        db.flush()

        if item_req.modifier_ids:
            modifier_options = db.query(ModifierOption).filter(
                ModifierOption.id.in_(item_req.modifier_ids)
            ).all()
            for opt in modifier_options:
                db.add(OrderItemModifier(
                    order_item_id=order_item.id,
                    name=opt.name.get("en", str(opt.name)),
                    price_modifier=opt.price_modifier,
                ))
                unit_price += opt.price_modifier

        order_item.unit_price = unit_price
        total += unit_price * item_req.quantity

    table.is_occupied = True
    db.commit()

    await manager.broadcast(restaurant.id, {
        "type": "new_order",
        "order_id": order.id,
        "table_number": table.table_number,
    })

    return {"order_id": order.id, "total": round(total, 2)}


@app.get("/{slug}/order/{order_id}/status", response_class=HTMLResponse)
async def order_status(slug: str, order_id: int, lang: str = "en", db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return templates.TemplateResponse("customer/order_status.html", {
        "request": {},
        "order": order,
        "lang": lang,
    })


# ─── Staff Routes ─────────────────────────────────────────────────────

@app.get("/{slug}/staff/login", response_class=HTMLResponse)
async def staff_login_form(slug: str, db: Session = Depends(get_db)):
    restaurant = get_restaurant_by_slug(slug, db)
    return templates.TemplateResponse("staff/login.html", {"request": {}, "restaurant": restaurant})


@app.post("/{slug}/staff/login")
async def staff_login(slug: str, password: str = Form(...), db: Session = Depends(get_db)):
    restaurant = get_restaurant_by_slug(slug, db)
    if password != "dineflow123":
        return templates.TemplateResponse("staff/login.html", {
            "request": {},
            "restaurant": restaurant,
            "error": "Wrong password"
        })
    response = RedirectResponse(url=f"/{slug}/staff/dashboard", status_code=303)
    response.set_cookie(key="staff_token", value="authenticated")
    return response


def staff_auth(request: Request, slug: str):
    if request.cookies.get("staff_token") != "authenticated":
        raise HTTPException(303, detail="", headers={"Location": f"/{slug}/staff/login"})


@app.get("/{slug}/staff/dashboard", response_class=HTMLResponse)
async def staff_dashboard(slug: str, request: Request, db: Session = Depends(get_db)):
    staff_auth(request, slug)
    restaurant = get_restaurant_by_slug(slug, db)
    tables = db.query(Table).filter(Table.restaurant_id == restaurant.id).order_by(Table.table_number).all()
    orders = db.query(Order).filter(
        Order.table_id.in_([t.id for t in tables]),
        Order.status != "paid"
    ).order_by(Order.created_at.desc()).all()
    return templates.TemplateResponse("staff/dashboard.html", {
        "request": request,
        "restaurant": restaurant,
        "tables": tables,
        "orders": orders,
    })


@app.patch("/{slug}/staff/order/{order_id}/status")
async def update_order_status(slug: str, order_id: int, body: OrderStatusUpdate, request: Request, db: Session = Depends(get_db)):
    staff_auth(request, slug)
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    order.status = body.status
    db.commit()

    # If HTMX request, return refreshed live orders partial
    if request.headers.get("HX-Request"):
        restaurant = get_restaurant_by_slug(slug, db)
        tables = db.query(Table).filter(Table.restaurant_id == restaurant.id).all()
        orders = db.query(Order).filter(
            Order.table_id.in_([t.id for t in tables]),
            Order.status != "paid"
        ).order_by(Order.created_at.desc()).all()
        return templates.TemplateResponse("staff/_live_orders.html", {
            "request": request,
            "restaurant": restaurant,
            "orders": orders,
        })

    return {"status": body.status}


@app.get("/{slug}/staff/table/{table_id}/bill", response_class=HTMLResponse)
async def view_bill(slug: str, table_id: int, request: Request, db: Session = Depends(get_db)):
    staff_auth(request, slug)
    restaurant = get_restaurant_by_slug(slug, db)
    table = db.query(Table).filter(Table.id == table_id, Table.restaurant_id == restaurant.id).first()
    if not table:
        raise HTTPException(404, "Table not found")

    active_orders = db.query(Order).filter(
        Order.table_id == table_id,
        Order.status != "paid"
    ).all()

    order_items = []
    subtotal = 0.0
    for order in active_orders:
        for item in order.items:
            modifiers = [m.name for m in item.modifiers]
            line_total = item.unit_price * item.quantity
            subtotal += line_total
            order_items.append({
                "name": item.menu_item.name,
                "qty": item.quantity,
                "unit_price": item.unit_price,
                "line_total": line_total,
                "modifiers": modifiers,
                "notes": item.notes,
            })

    gst = round(subtotal * restaurant.gst_rate / 100, 2)
    total = round(subtotal + gst, 2)

    return templates.TemplateResponse("staff/bill.html", {
        "request": request,
        "restaurant": restaurant,
        "table": table,
        "order_items": order_items,
        "subtotal": subtotal,
        "gst": gst,
        "total": total,
    })


@app.post("/{slug}/staff/table/{table_id}/clear")
async def clear_table(slug: str, table_id: int, request: Request, db: Session = Depends(get_db)):
    staff_auth(request, slug)
    restaurant = get_restaurant_by_slug(slug, db)
    table = db.query(Table).filter(Table.id == table_id, Table.restaurant_id == restaurant.id).first()
    if not table:
        raise HTTPException(404, "Table not found")

    orders = db.query(Order).filter(Order.table_id == table_id, Order.status != "paid").all()
    for order in orders:
        order.status = "paid"
    table.is_occupied = False
    db.commit()

    return {"status": "ok"}


@app.get("/{slug}/staff/order/{order_id}/docket", response_class=HTMLResponse)
async def print_docket(slug: str, order_id: int, request: Request, db: Session = Depends(get_db)):
    staff_auth(request, slug)
    restaurant = get_restaurant_by_slug(slug, db)
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return templates.TemplateResponse("staff/docket.html", {
        "request": request,
        "restaurant": restaurant,
        "order": order,
    })


@app.get("/{slug}/staff/orders/table/{table_id}", response_class=HTMLResponse)
async def table_orders_partial(slug: str, table_id: int, request: Request, db: Session = Depends(get_db)):
    staff_auth(request, slug)
    restaurant = get_restaurant_by_slug(slug, db)
    table = db.query(Table).filter(Table.id == table_id, Table.restaurant_id == restaurant.id).first()
    if not table:
        return HTMLResponse("")
    orders = db.query(Order).filter(
        Order.table_id == table_id,
        Order.status != "paid"
    ).order_by(Order.created_at.desc()).all()

    order_items = []
    for order in orders:
        for item in order.items:
            modifiers = ", ".join(m.name for m in item.modifiers)
            order_items.append({
                "name": item.menu_item.name,
                "qty": item.quantity,
                "modifiers": modifiers,
                "notes": item.notes,
                "status": order.status,
                "order_id": order.id,
            })

    return templates.TemplateResponse("staff/_table_orders.html", {
        "request": request,
        "table": table,
        "restaurant": restaurant,
        "order_items": order_items,
    })


# ─── WebSocket ────────────────────────────────────────────────────────

@app.websocket("/{slug}/ws/staff")
async def staff_ws(slug: str, websocket: WebSocket, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).filter(Restaurant.slug == slug).first()
    if not restaurant:
        await websocket.close()
        return
    await manager.connect(restaurant.id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(restaurant.id, websocket)


# ─── Super Admin Routes ───────────────────────────────────────────────

@app.get("/super-admin/login", response_class=HTMLResponse)
async def admin_login_form(request: Request):
    return templates.TemplateResponse("super_admin/login.html", {"request": request})


@app.post("/super-admin/login")
async def admin_login(request: Request, password: str = Form(...)):
    if password != "admin123":
        return templates.TemplateResponse("super_admin/login.html", {"request": request, "error": "Wrong password"})
    response = RedirectResponse(url="/super-admin/dashboard", status_code=303)
    response.set_cookie(key="admin_token", value="authenticated")
    return response


def admin_auth(request: Request):
    if request.cookies.get("admin_token") != "authenticated":
        raise HTTPException(303, detail="", headers={"Location": "/super-admin/login"})


@app.get("/super-admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    admin_auth(request)
    restaurants = db.query(Restaurant).all()
    return templates.TemplateResponse("super_admin/dashboard.html", {
        "request": request,
        "restaurants": restaurants,
    })


@app.get("/super-admin/restaurant/new", response_class=HTMLResponse)
async def admin_new_restaurant_form(request: Request):
    admin_auth(request)
    return templates.TemplateResponse("super_admin/restaurant_form.html", {"request": request})


@app.post("/super-admin/restaurant/new")
async def admin_create_restaurant(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    suburb: str = Form(""),
    table_count: int = Form(10),
    db: Session = Depends(get_db),
):
    admin_auth(request)
    existing = db.query(Restaurant).filter(Restaurant.slug == slug).first()
    if existing:
        return templates.TemplateResponse("super_admin/restaurant_form.html", {
            "request": request,
            "error": "Slug already taken",
        })

    restaurant = Restaurant(name=name, slug=slug, suburb=suburb)
    db.add(restaurant)
    db.flush()

    for i in range(1, table_count + 1):
        db.add(Table(restaurant_id=restaurant.id, table_number=i))

    db.commit()
    return RedirectResponse(url=f"/super-admin/restaurant/{restaurant.id}/menu", status_code=303)


@app.get("/super-admin/restaurant/{rest_id}/menu", response_class=HTMLResponse)
async def admin_menu_editor(request: Request, rest_id: int, db: Session = Depends(get_db)):
    admin_auth(request)
    restaurant = db.query(Restaurant).filter(Restaurant.id == rest_id).first()
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    categories = db.query(MenuCategory).filter(
        MenuCategory.restaurant_id == restaurant.id
    ).order_by(MenuCategory.sort_order).all()
    return templates.TemplateResponse("super_admin/menu_editor.html", {
        "request": request,
        "restaurant": restaurant,
        "categories": categories,
    })


@app.post("/super-admin/restaurant/{rest_id}/menu/category")
async def admin_add_category(
    rest_id: int,
    request: Request,
    name_en: str = Form(...),
    db: Session = Depends(get_db),
):
    admin_auth(request)
    restaurant = db.query(Restaurant).filter(Restaurant.id == rest_id).first()
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    category = MenuCategory(restaurant_id=rest_id, name={"en": name_en})
    db.add(category)
    db.commit()
    return RedirectResponse(url=f"/super-admin/restaurant/{rest_id}/menu", status_code=303)


@app.post("/super-admin/restaurant/{rest_id}/menu/item")
async def admin_add_item(
    rest_id: int,
    request: Request,
    category_id: int = Form(...),
    name_en: str = Form(...),
    price: float = Form(...),
    description_en: str = Form(""),
    db: Session = Depends(get_db),
):
    admin_auth(request)
    item = MenuItem(
        category_id=category_id,
        name={"en": name_en},
        description={"en": description_en},
        price=price,
    )
    db.add(item)
    db.commit()
    return RedirectResponse(url=f"/super-admin/restaurant/{rest_id}/menu", status_code=303)


@app.post("/super-admin/restaurant/{rest_id}/menu/item/{item_id}/delete")
async def admin_delete_item(rest_id: int, item_id: int, request: Request, db: Session = Depends(get_db)):
    admin_auth(request)
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url=f"/super-admin/restaurant/{rest_id}/menu", status_code=303)


@app.get("/super-admin/restaurant/{rest_id}/tables", response_class=HTMLResponse)
async def admin_tables(request: Request, rest_id: int, db: Session = Depends(get_db)):
    admin_auth(request)
    restaurant = db.query(Restaurant).filter(Restaurant.id == rest_id).first()
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    tables = db.query(Table).filter(Table.restaurant_id == rest_id).order_by(Table.table_number).all()
    return templates.TemplateResponse("super_admin/tables.html", {
        "request": request,
        "restaurant": restaurant,
        "tables": tables,
    })
