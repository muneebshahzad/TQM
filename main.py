import os, json
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from flask import Flask, render_template, request, jsonify
from lazop import LazopClient, LazopRequest  # Lazop, matching your sample

# ---- CONFIG ----
ENDPOINT     = os.getenv("DARAZ_ENDPOINT", "https://api.daraz.pk/rest")
APP_KEY      = os.getenv("DARAZ_APP_KEY")
APP_SECRET   = os.getenv("DARAZ_APP_SECRET")
ACCESS_TOKEN = os.getenv("DARAZ_ACCESS_TOKEN")

# Hardcoded initial fetch date: 6 July 2025 (+05:00)
CREATED_AFTER_ISO = "2025-07-06T00:00:00+05:00"
CREATED_AFTER_DISPLAY = "2025-07-06"

# All statuses EXCEPT "canceled"
STATUSES_EXCEPT_CANCELED = [
    "unpaid", "pending", "ready_to_ship", "shipped", "delivered",
    "returned", "failed", "topack", "toship", "packed"
]

# Local storage files
COSTS_FILE = "product_costs.json"   # { key: { "product_cost": "123.45", "packaging": "50.00", "vendor": "Tick Bags|Sleek Space|Other" }, ... }
PAID_FILE  = "vendor_paid.json"     # { order_id: true/false }

VENDOR_CHOICES = ["Tick Bags", "Sleek Space", "Other"]

app = Flask(__name__)
client = LazopClient(ENDPOINT, APP_KEY, APP_SECRET)

# ---------- helpers ----------
def _d(x) -> Decimal:
    try:
        s = str(x).replace(",", "").strip()
        return Decimal(s if s else "0")
    except Exception:
        return Decimal("0")

def _fmt_pkr(x) -> str:
    try:
        d = _d(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        d = Decimal("0.00")
    return f"PKR {d:,.2f}"

def _parse_order_date_str(s: str | None) -> str:
    if not s:
        return ""
    if "T" in s: return s.split("T", 1)[0]
    if " " in s: return s.split(" ", 1)[0]
    return s[:10]

def _join_address(addr: dict | None) -> str:
    if not addr: return ""
    parts = [addr.get("address1"), addr.get("address2"), addr.get("address3"),
             addr.get("address4"), addr.get("address5"), addr.get("city")]
    parts = [p for p in parts if p and str(p).lower() != "null"]
    line = ", ".join(parts)
    post = addr.get("post_code") or ""
    country = addr.get("country") or ""
    if post:    line = f"{line}, {post}" if line else post
    if country: line = f"{line}, {country}" if line else country
    return line

def format_title(name, variation):
    base = f"{name or 'Unknown'} {variation or ''}".strip()
    if "Color family:" in base:
        p, c = base.split("Color family:", 1)
        return f"{p.strip()} - {c.strip()}"
    return base

def _load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_json(path: str, data: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def _item_key(it: dict) -> str:
    """
    Stable identifier for a product across orders.
    Prefer seller_sku, then lazada_sku, then sku, then name|variation.
    """
    for k in ("seller_sku", "lazada_sku", "sku"):
        v = (it.get(k) or "").strip()
        if v: return v
    return f"{(it.get('name') or '').strip()}|{(it.get('variation') or '').strip()}"

# ---------- API calls ----------
def _orders_list(created_after_iso: str, statuses=None):
    lim = "50"
    offsets = ["0"]
    status_list = statuses or [None]
    seen = {}

    for status in status_list:
        for offset in offsets:
            req = LazopRequest('/orders/get', 'GET')
            req.add_api_param('access_token', ACCESS_TOKEN)
            req.add_api_param('sort_direction', 'DESC')
            req.add_api_param('offset', offset)
            req.add_api_param('created_after', created_after_iso)
            req.add_api_param('limit', lim)               # keep your sample's 'limit'
            req.add_api_param('update_after', created_after_iso)
            req.add_api_param('sort_by', 'updated_at')
            if status:
                req.add_api_param('status', status)

            resp = client.execute(req)
            orders = (getattr(resp, "body", {}) or {}).get('data', {}).get('orders', []) or []

            for o in orders:
                oid = str(o.get('order_id'))
                if oid in seen: continue
                name = f"{o.get('customer_first_name','') or ''} {o.get('customer_last_name','') or ''}".strip()
                addr_ship = o.get('address_shipping') or {}
                if not name:
                    name = f"{addr_ship.get('first_name','') or ''} {addr_ship.get('last_name','') or ''}".strip()
                address = _join_address(addr_ship)
                phone = addr_ship.get('phone') or addr_ship.get('phone2') or ""
                seen[oid] = {
                    'order_id': oid,
                    'created_at_raw': o.get('created_at', ''),
                    'order_date': _parse_order_date_str(o.get('created_at', '')),
                    'price': o.get('price', '0.00'),
                    'customer': {'name': name or "", 'address': address or "", 'phone': phone or ""},
                    'statuses': o.get('statuses') or []
                }
    return list(seen.values())

def _items_with_tracking(order_id: str, order_statuses=None):
    # Items
    it_req = LazopRequest('/order/items/get', 'GET')
    it_req.add_api_param('access_token', ACCESS_TOKEN)
    it_req.add_api_param('order_id', order_id)
    it_res = client.execute(it_req)
    items = (getattr(it_res, "body", {}) or {}).get('data', []) or []

    # Tracking
    tr_req = LazopRequest('/logistic/order/trace', 'GET')
    tr_req.add_api_param('access_token', ACCESS_TOKEN)
    tr_req.add_api_param('order_id', order_id)
    tr_res = client.execute(tr_req)
    tr_body = getattr(tr_res, "body", {}) or {}
    tr_result = tr_body.get('result', {}) or {}
    tr_data = tr_result.get('data', []) or []
    tmap = {}
    if tr_data:
        pkg_list = tr_data[0].get('package_detail_info_list', []) or []
        for pkg in pkg_list:
            tnum = pkg.get('tracking_number')
            det = pkg.get('logistic_detail_info_list', []) or []
            last = det[-1].get('title') if det else None
            if tnum: tmap[tnum] = last or None

    order_status_text = None
    if order_statuses:
        for s in reversed(order_statuses):
            if s:
                order_status_text = s.replace('_', ' ').title()
                break

    rows = []
    for it in items:
        tnum = it.get('tracking_code') or 'N/A'
        status_from_trace = tmap.get(tnum)
        if status_from_trace:
            final_status = status_from_trace
        elif tnum in ("", None, "N/A"):
            final_status = "Un-Booked"
        else:
            item_status = (it.get('status') or it.get('order_item_status') or "").strip()
            final_status = item_status.replace('_', ' ').title() if item_status else (order_status_text or "N/A")

        rows.append({
            'key': _item_key(it),
            'item_image': it.get('product_main_image', ''),
            'item_title': format_title(it.get('name'), it.get('variation')),
            'quantity': it.get('quantity', 1),
            'tracking_number': tnum,
            'status': final_status
        })
    return rows

# ---- Invoicing (restored logic you liked) ----
def _finance_for_order(order_id: str, order_date_str: str, order_total_str: str):
    """
    Returns:
      net_total_num (Decimal), net_total_fmt (str), statement_text (str),
      paid_status_label (str), breakdown (list of {label, amount_fmt})
    Ensures "Product Price Paid by Buyer" == order total if the API doesn't provide it.
    """
    try:
        od = datetime.strptime(order_date_str or CREATED_AFTER_DISPLAY, "%Y-%m-%d").date()
    except Exception:
        od = date.today()
    start_date = (od - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date   = (od + timedelta(days=120)).strftime("%Y-%m-%d")

    req = LazopRequest('/finance/transaction/details/get', 'GET')
    req.add_api_param('access_token', ACCESS_TOKEN)
    req.add_api_param('offset', '0')
    req.add_api_param('limit', '500')
    req.add_api_param('start_time', start_date)
    req.add_api_param('end_time', end_date)
    req.add_api_param('trade_order_id', order_id)

    res = client.execute(req)
    rows = (getattr(res, "body", {}) or {}).get("data", []) or []

    agg = {}
    for r in rows:
        label = (r.get("fee_name") or r.get("transaction_type") or "Other").strip()
        amt = _d(r.get("amount"))
        agg[label] = agg.get(label, Decimal("0")) + amt

    product_key = None
    for k in list(agg.keys()):
        if k.strip().lower() == "product price paid by buyer":
            product_key = k
            break
    order_total = _d(order_total_str)
    if product_key is None:
        agg["Product Price Paid by Buyer"] = order_total
    elif agg[product_key] <= 0:
        agg[product_key] = order_total

    paid_status_label = "Paid" if any(str(r.get("paid_status","")).lower() in ("yes","paid") for r in rows) else "Not Paid"
    statement_text = rows[-1].get("statement") if rows else ""

    net_total_num = sum(agg.values(), Decimal("0"))
    net_total_fmt = _fmt_pkr(net_total_num)

    items = list(agg.items())
    items.sort(key=lambda kv: (
        kv[0].strip().lower() != "product price paid by buyer",
        0 if kv[1] >= 0 else 1,
        kv[0].lower()
    ))
    breakdown = [{"label": k, "amount_fmt": _fmt_pkr(v)} for k, v in items]
    return net_total_num, net_total_fmt, statement_text, paid_status_label, breakdown

# -------- LOAD RAW DATA ON STARTUP (once) --------
RAW_ORDERS_CACHE = []
LOAD_ERROR = None
try:
    summaries = _orders_list(CREATED_AFTER_ISO, statuses=STATUSES_EXCEPT_CANCELED)
    RAW_ORDERS_CACHE = []
    for s in summaries:
        items_list = _items_with_tracking(s['order_id'], order_statuses=s.get('statuses'))
        # store only raw order summary + raw items; finance computed on-demand & cached into this dict
        RAW_ORDERS_CACHE.append({**s, 'items_list': items_list})
    print(f"[startup] Loaded {len(RAW_ORDERS_CACHE)} unique orders since {CREATED_AFTER_DISPLAY}.")
except Exception as e:
    LOAD_ERROR = str(e)
    print(f"[startup] Error: {LOAD_ERROR}")

def _ensure_finance(base: dict):
    """Compute finance once per order & cache onto RAW_ORDERS_CACHE entry."""
    has_all = (
        base.get("invoice_amount") is not None and
        base.get("invoice_amount_num") is not None and
        base.get("statement") is not None and
        base.get("paid_status") is not None and
        base.get("invoice_breakdown") is not None
    )
    if has_all:
        return (
            _d(base.get("invoice_amount_num") or 0),
            base.get("invoice_amount") or "",
            base.get("statement") or "",
            base.get("paid_status") or "",
            base.get("invoice_breakdown") or [],
        )
    net_num, inv_fmt, stmt, paid, br = _finance_for_order(
        base["order_id"], base.get("order_date"), base.get("price")
    )
    base["invoice_amount_num"] = str(net_num)
    base["invoice_amount"] = inv_fmt
    base["statement"] = stmt or ""
    base["paid_status"] = paid or ""
    base["invoice_breakdown"] = br or []
    return net_num, inv_fmt, base["statement"], base["paid_status"], base["invoice_breakdown"]

# Build a view from RAW_ORDERS_CACHE and current JSON files
def _build_runtime_view(filtered_raw):
    costs = _load_json(COSTS_FILE)
    paid  = _load_json(PAID_FILE)

    view = []
    for base in filtered_raw:
        # finance (ensure cached on RAW_ORDERS_CACHE)
        net_num, inv_fmt, statement, paid_status, breakdown = _ensure_finance(base)

        # recompute costs from latest JSON
        prod_total = Decimal("0")
        pack_total = Decimal("0")
        items = []
        for it in base.get("items_list", []):
            key = it.get("key")
            rec = costs.get(key) if key else None
            pc = _d(rec.get("product_cost")) if rec else Decimal("0")
            pk = _d(rec.get("packaging"))    if rec else Decimal("0")
            vend = (rec.get("vendor") if rec else "") or "Other"
            qty = _d(it.get("quantity") or 1)

            prod_total += pc * qty
            pack_total += pk * qty

            items.append({
                **it,
                "product_cost": str(pc),
                "packaging": str(pk),
                "vendor": vend,
                "needs_cost": (rec is None),
            })

        net_profit_num = net_num - prod_total - pack_total

        view.append({
            "order_id": base["order_id"],
            "order_date": base.get("order_date", ""),
            "price": base.get("price", "0.00"),
            "customer": base.get("customer", {}),
            "statement": statement,
            "paid_status": paid_status,
            "invoice_amount": inv_fmt,
            "invoice_amount_num": str(net_num),
            "invoice_breakdown": breakdown,
            "items_list": items,
            "product_cost_total": _fmt_pkr(prod_total),
            "packaging_total": _fmt_pkr(pack_total),
            "net_profit": _fmt_pkr(net_profit_num),
            "net_profit_num": str(net_profit_num),
            "vendor_paid": bool(paid.get(base["order_id"], False)),
        })
    return view

def _within_range(od: str, start: str | None, end: str | None) -> bool:
    """od, start, end are 'YYYY-MM-DD' strings."""
    if not od:
        return False
    try:
        d = datetime.strptime(od, "%Y-%m-%d").date()
    except Exception:
        return False
    if start:
        try:
            s = datetime.strptime(start, "%Y-%m-%d").date()
            if d < s: return False
        except: pass
    if end:
        try:
            e = datetime.strptime(end, "%Y-%m-%d").date()
            if d > e: return False
        except: pass
    return True

def _compute_stats(orders_view):
    """
    Returns dict with:
      payables_total, payables_tick, payables_sleek, payables_other,
      net_profit_collected
    Payables are computed ONLY over unpaid orders (vendor_paid == False).
    Vendor split is based on per-item vendor from product_costs.json.
    Net profit collected = sum(net_profit) where finance paid_status == 'Paid'.
    """
    payables_total = Decimal("0")
    split = {"Tick Bags": Decimal("0"), "Sleek Space": Decimal("0"), "Other": Decimal("0")}
    net_profit_collected = Decimal("0")

    for o in orders_view:
        # vendor split & total payables only for unpaid
        if not o.get("vendor_paid", False):
            for it in o.get("items_list", []):
                qty = _d(it.get("quantity") or 1)
                pc  = _d(it.get("product_cost"))
                pk  = _d(it.get("packaging"))
                vendor = (it.get("vendor") or "Other")
                line = (pc + pk) * qty
                payables_total += line
                if vendor not in split:
                    split["Other"] += line
                else:
                    split[vendor] += line
        # collected net profit (only if finance marked Paid)
        if str(o.get("paid_status","")).lower().startswith("paid"):
            net_profit_collected += _d(o.get("net_profit_num") or 0)

    return {
        "payables_total": _fmt_pkr(payables_total),
        "payables_tick": _fmt_pkr(split["Tick Bags"]),
        "payables_sleek": _fmt_pkr(split["Sleek Space"]),
        "payables_other": _fmt_pkr(split["Other"]),
        "net_profit_collected": _fmt_pkr(net_profit_collected),
    }

# ---------- Routes ----------
@app.route("/")
def page():
    if LOAD_ERROR:
        return f"<h3>Daraz API error at startup</h3><pre>{LOAD_ERROR}</pre>", 502

    # Date filters (do NOT refetch from Daraz; filter the cached set)
    start_q = request.args.get("from")  or CREATED_AFTER_DISPLAY
    end_q   = request.args.get("to")    or None

    filtered_raw = [o for o in RAW_ORDERS_CACHE if _within_range(o.get("order_date",""), start_q, end_q)]
    orders_view = _build_runtime_view(filtered_raw)
    stats = _compute_stats(orders_view)

    return render_template(
        "tqm.html",
        orders=orders_view,
        created_after=start_q,
        created_before=end_q or "",
        stats=stats,
        vendors=VENDOR_CHOICES,
    )

@app.post("/api/save_cost")
def api_save_cost():
    """
    Body JSON: {"key": "...", "product_cost": "123.45", "packaging": "50.00", "vendor": "Tick Bags|Sleek Space|Other"}
    Saves to product_costs.json.
    """
    data = request.get_json(force=True, silent=True) or {}
    key = (data.get("key") or "").strip()
    if not key:
        return jsonify({"ok": False, "error": "Missing key"}), 400

    try:
        pc = str(_d(data.get("product_cost")))
        pk = str(_d(data.get("packaging")))
    except Exception:
        return jsonify({"ok": False, "error": "Invalid amounts"}), 400

    vendor = (data.get("vendor") or "Other").strip()
    if vendor not in VENDOR_CHOICES:
        vendor = "Other"

    costs = _load_json(COSTS_FILE)
    costs[key] = {"product_cost": pc, "packaging": pk, "vendor": vendor}
    _save_json(COSTS_FILE, costs)
    return jsonify({"ok": True})

@app.post("/api/toggle_paid")
def api_toggle_paid():
    """
    Body JSON: {"order_id": "...", "paid": true/false}
    Saves to vendor_paid.json and returns new state.
    """
    data = request.get_json(force=True, silent=True) or {}
    oid = (data.get("order_id") or "").strip()
    if not oid:
        return jsonify({"ok": False, "error": "Missing order_id"}), 400
    paid = bool(data.get("paid"))
    paid_map = _load_json(PAID_FILE)
    paid_map[oid] = paid
    _save_json(PAID_FILE, paid_map)
    return jsonify({"ok": True, "paid": paid})

if __name__ == "__main__":
    print("Open: http://127.0.0.1:5000/")
    app.run(debug=True)
