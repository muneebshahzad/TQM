import os
import time
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from flask import Flask, render_template, request, jsonify
from lazop import LazopClient, LazopRequest

# Import the correct database connector
try:
    import pymssql
except ImportError:
    print("Error: 'pymssql' library not found. Please install it using 'pip install pymssql'")
    raise

# ---- CONFIG ----
ENDPOINT = os.getenv("DARAZ_ENDPOINT", "https://api.daraz.pk/rest")
APP_KEY = os.getenv("DARAZ_APP_KEY")
APP_SECRET = os.getenv("DARAZ_APP_SECRET")
ACCESS_TOKEN = os.getenv("DARAZ_ACCESS_TOKEN")

# ---- DATABASE CONFIG ----
COSTS_TABLE = "tqm_product_costs"
VENDOR_PAYMENTS_TABLE = "vendor_payments"  # Using the table created in vendor_payments.sql

# Hardcoded initial fetch date: 6 July 2025 (+05:00)
CREATED_AFTER_ISO = "2025-07-06T00:00:00+05:00"
CREATED_AFTER_DISPLAY = "2025-07-06"

# All statuses EXCEPT "canceled"
STATUSES_EXCEPT_CANCELED = [
    "unpaid", "pending", "ready_to_ship", "shipped", "delivered",
    "returned", "failed", "topack", "toship", "packed"
]

VENDOR_CHOICES = ["Tick Bags", "Sleek Space", "Other"]

app = Flask(__name__)


@app.template_filter('first_words')
def first_words(s, n=3):
    """Return the first n words of s, adding … if truncated."""
    if not s:
        return ""
    parts = str(s).split()
    n = int(n)
    trimmed = " ".join(parts[:n])
    return trimmed + ("…" if len(parts) > n else "")


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


def _item_key(it: dict) -> str:
    """
    Stable identifier for a product across orders.
    Prefer seller_sku, then lazada_sku, then sku, then name|variation.
    """
    for k in ("seller_sku", "lazada_sku", "sku"):
        v = (it.get(k) or "").strip()
        if v: return v
    return f"{(it.get('name') or '').strip()}|{(it.get('variation') or '').strip()}"


# --- DATABASE CONNECTION (Using your provided function structures) ---

def get_db_connection():
    """Connects to MSSQL using environment variables via pymssql."""
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_DATABASE')
    username = os.getenv('DB_USERNAME')
    password = os.getenv('DB_PASSWORD')
    try:
        connection = pymssql.connect(server=server, user=username, password=password, database=database)
        return connection
    except pymssql.Error as e:
        print(f"Error connecting to the database: {str(e)}")
        # If connection fails, return None for graceful handling in I/O functions
        return None


def check_database_connection():
    """
    Utility function provided by the user. Note: It uses hardcoded credentials,
    but is included for completeness based on the request.
    """
    server = 'tickbags.database.windows.net'
    database = 'TickBags'
    username = 'tickbags_ltd'
    password = 'TB@2024!'

    try:
        print('Connecting to the database...')
        connection = pymssql.connect(server=server, user=username, password=password, database=database)

        print('Connected to the database')
        return connection
    except pymssql.Error as e:
        print(f"Error connecting to the database: {str(e)}")
        time.sleep(5)
        # Recursive retry - simplified here to avoid blocking execution excessively
        # check_database_connection()
        return None


# --- DATABASE I/O FUNCTIONS (Existing/Modified) ---

def _load_db_costs() -> dict:
    """Loads all product costs from the tqm_product_costs table."""
    costs = {}
    sql = f"SELECT item_key, product_cost, packaging, vendor FROM {COSTS_TABLE};"
    try:
        with get_db_connection() as conn:
            if not conn: return {}

            cursor = conn.cursor()
            cursor.execute(sql)
            for row in cursor.fetchall():
                key = row[0]
                # Convert DECIMAL results to string for consistency
                costs[key] = {
                    "product_cost": str(row[1]),
                    "packaging": str(row[2]),
                    "vendor": row[3]
                }
    except Exception as e:
        print(f"[DB ERROR] Failed to load costs: {e}")
    return costs


def _save_db_cost(key: str, pc: str, pk: str, vendor: str):
    """Saves/Updates a single product cost record (UPSERT logic)."""
    # Note: pymssql uses %s placeholders
    sql_update = f"""
        UPDATE {COSTS_TABLE} 
        SET product_cost = %s, packaging = %s, vendor = %s 
        WHERE item_key = %s;
    """
    sql_insert = f"""
        INSERT INTO {COSTS_TABLE} (item_key, product_cost, packaging, vendor) 
        VALUES (%s, %s, %s, %s);
    """
    try:
        with get_db_connection() as conn:
            if not conn: return False

            cursor = conn.cursor()

            # 1. Try to UPDATE (pc and pk are passed as strings/Decimals, pymssql handles type)
            cursor.execute(sql_update, (pc, pk, vendor, key))

            # 2. If no rows were updated, INSERT
            if cursor.rowcount == 0:
                cursor.execute(sql_insert, (key, pc, pk, vendor))

            conn.commit()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to save cost for {key}: {e}")
        return False


# --- VENDOR PAYMENT DATABASE FUNCTIONS ---

def _save_db_payment(vendor: str, amount: Decimal, payment_date: str, user_id: str):
    """Inserts a new payment record into the vendor_payments table."""
    sql_insert = f"""
        INSERT INTO {VENDOR_PAYMENTS_TABLE} (user_id, vendor, amount, payment_date)
        VALUES (%s, %s, %s, %s);
    """
    try:
        with get_db_connection() as conn:
            if not conn: return False

            cursor = conn.cursor()
            # Note: payment_date is YYYY-MM-DD string, amount is Decimal/string
            cursor.execute(sql_insert, (user_id, vendor, amount, payment_date))
            conn.commit()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to record payment to {vendor}: {e}")
        return False


def _load_db_vendor_payments(user_id: str) -> list[dict]:
    """Loads all vendor payment records for history, sorted by timestamp (most recent first)."""
    # Note: We include user_id in the WHERE clause per best practice, though it's
    # part of the security model/context.
    sql = f"""
        SELECT payment_date, vendor, amount
        FROM {VENDOR_PAYMENTS_TABLE}
        WHERE user_id = %s
        ORDER BY timestamp DESC;
    """
    history = []
    try:
        with get_db_connection() as conn:
            if not conn: return []

            cursor = conn.cursor()
            cursor.execute(sql, (user_id,))
            for row in cursor.fetchall():
                # row[0] is DATE object, row[2] is DECIMAL
                history.append({
                    "date": row[0].strftime("%Y-%m-%d"),
                    "vendor": row[1],
                    "amount": str(row[2]),
                    "amount_fmt": _fmt_pkr(row[2])
                })
    except Exception as e:
        print(f"[DB ERROR] Failed to load payment history: {e}")
    return history


def _load_db_payments_total() -> dict[str, Decimal]:
    """
    MODIFIED: Calculates the sum of all payments made, grouped by vendor.
    Returns: A dictionary mapping vendor name (str) to total paid amount (Decimal).
    """
    # Note: We are calculating the sum across all users here for simplicity since user_id is placeholder.
    sql = f"SELECT vendor, SUM(amount) FROM {VENDOR_PAYMENTS_TABLE} GROUP BY vendor;"
    totals = {v: Decimal("0") for v in VENDOR_CHOICES}

    try:
        with get_db_connection() as conn:
            if not conn: return totals

            cursor = conn.cursor()
            cursor.execute(sql)
            for row in cursor.fetchall():
                vendor = row[0]
                amount = _d(row[1])
                if vendor in VENDOR_CHOICES:
                    totals[vendor] = amount
                # Optional: Handle payments to 'Other' if not in VENDOR_CHOICES list itself
                elif vendor:
                    totals['Other'] = totals.get('Other', Decimal('0')) + amount

    except Exception as e:
        print(f"[DB ERROR] Failed to load payment total by vendor: {e}")

    # Ensure all VENDOR_CHOICES are present in the final output dictionary
    for vendor in VENDOR_CHOICES:
        if vendor not in totals:
            totals[vendor] = Decimal("0")

    return totals


# --- END VENDOR PAYMENT DATABASE FUNCTIONS ---


# ---------- API calls (No changes needed) ----------
def _orders_list(created_after_iso: str, statuses=None):
    # ... (API logic remains identical to original code) ...
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
            req.add_api_param('limit', lim)
            req.add_api_param('update_after', created_after_iso)
            req.add_api_param('sort_by', 'updated_at')
            if status:
                req.add_api_param('status', status)

            resp = client.execute(req)
            orders = (getattr(resp, "body", {}) or {}).get('data', {}).get('orders', []) or []

            for o in orders:
                oid = str(o.get('order_id'))
                if oid in seen: continue
                name = f"{o.get('customer_first_name', '') or ''} {o.get('customer_last_name', '') or ''}".strip()
                addr_ship = o.get('address_shipping') or {}
                if not name:
                    name = f"{addr_ship.get('first_name', '') or ''} {addr_ship.get('last_name', '') or ''}".strip()
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


def _finance_for_order(order_id: str, order_date_str: str, order_total_str: str):
    """
    Returns:
      net_total_num (Decimal), net_total_fmt (str), statement_text (str),
      paid_status_label (str), breakdown (list of {label, amount_fmt})
    """
    try:
        od = datetime.strptime(order_date_str or CREATED_AFTER_DISPLAY, "%Y-%m-%d").date()
    except Exception:
        od = date.today()
    start_date = (od - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (od + timedelta(days=120)).strftime("%Y-%m-%d")

    req = LazopRequest('/finance/transaction/details/get', 'GET')
    req.add_api_param('access_token', ACCESS_TOKEN)
    req.add_api_param('offset', '0')
    req.add_api_param('limit', '500')
    req.add_api_param('start_time', start_date)
    req.add_api_param('end_time', end_date)
    req.add_api_param('trade_order_id', order_id)

    res = client.execute(req)
    rows = (getattr(res, "body", {}) or {}).get("data", []) or []

    # 🔒 If there are NO finance rows at all, treat as "invoice not generated"
    if not rows:
        return Decimal("0"), "0", "", "Not Paid", []

    # Otherwise, aggregate what the API returned
    agg = {}
    for r in rows:
        label = (r.get("fee_name") or r.get("transaction_type") or "Other").strip()
        amt = _d(r.get("amount"))
        agg[label] = agg.get(label, Decimal("0")) + amt

    # Inject fallback only when there ARE finance rows
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

    paid_status_label = "Paid" if any(
        str(r.get("paid_status", "")).lower() in ("yes", "paid") for r in rows) else "Not Paid"
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

# Perform a basic check for DB connectivity at startup as well
try:
    # Use a dummy user_id 'placeholder' since auth isn't fully set up here.
    USER_ID_PLACEHOLDER = os.getenv("USER_ID", "default-user-id")

    if not get_db_connection():
        LOAD_ERROR = "Failed to connect to the database at startup. Check environment variables (DB_SERVER, DB_DATABASE, DB_USERNAME, DB_PASSWORD)."
        print(f"[startup] {LOAD_ERROR}")

    # Continue with API data loading (original logic)
    summaries = _orders_list(CREATED_AFTER_ISO, statuses=STATUSES_EXCEPT_CANCELED)
    RAW_ORDERS_CACHE = []
    for s in summaries:
        items_list = _items_with_tracking(s['order_id'], order_statuses=s.get('statuses'))
        # store only raw order summary + raw items; finance computed on-demand & cached into this dict
        RAW_ORDERS_CACHE.append({**s, 'items_list': items_list})
    print(f"[startup] Loaded {len(RAW_ORDERS_CACHE)} unique orders since {CREATED_AFTER_DISPLAY}.")
except Exception as e:
    # This catches Daraz API errors primarily
    if not LOAD_ERROR:  # Don't overwrite DB error if already set
        LOAD_ERROR = str(e)
        print(f"[startup] API Error: {LOAD_ERROR}")


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


def _build_runtime_view(filtered_raw):
    # --- LOAD FROM DATABASE ---
    costs = _load_db_costs()
    # --------------------------

    view = []

    for base in filtered_raw:
        # finance (ensure cached on RAW_ORDERS_CACHE)
        net_num, inv_fmt, statement, paid_status, breakdown = _ensure_finance(base)

        # If invoice not generated, force invoice to 0
        if not inv_fmt or str(inv_fmt).strip() in ("", "None"):
            inv_fmt = "0"
            net_num = Decimal("0")
            breakdown = {}

        # Is whole order returned?
        order_statuses = [str(s or "").lower() for s in (base.get("statuses") or [])]
        is_order_returned = any(
            (s and (
                    s.lower() == "returned"
                    or "return" in s.lower()
                    or "buyer delivery failed" in s.lower()
                    or "package returned" in s.lower()
            ))
            for s in order_statuses
        )

        # recompute costs from latest DB load
        prod_total_eff = Decimal("0")
        pack_total = Decimal("0")
        items = []

        for it in base.get("items_list", []):
            key = it.get("key")
            rec = costs.get(key) if key else None

            # Note: Costs are loaded as strings but _d() handles conversion to Decimal
            pc = _d(rec.get("product_cost")) if rec else Decimal("0")
            pk = _d(rec.get("packaging")) if rec else Decimal("0")
            vend = (rec.get("vendor") if rec else "") or "Other"
            qty = _d(it.get("quantity") or 1)

            status_text = (it.get("status") or "").lower()
            is_item_returned = is_order_returned or ("return" in status_text)

            # --- CRITICAL LOGIC FOR ORDER VIEW (Effective Cost) ---
            # If item is returned/failed, effective product cost is ZERO, only packaging is paid.
            eff_pc = Decimal("0") if is_item_returned else pc
            # ------------------------------------------------------

            prod_total_eff += eff_pc * qty
            pack_total += pk * qty

            items.append({
                **it,
                "product_cost": str(pc),
                "packaging": str(pk),
                "vendor": vend,
                "needs_cost": (rec is None),
                "is_returned": is_item_returned,
            })

        net_profit_num = net_num - prod_total_eff - pack_total

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
            "product_cost_total": _fmt_pkr(prod_total_eff),  # Effective cost (excluding returned product cost)
            "packaging_total": _fmt_pkr(pack_total),
            "net_profit": _fmt_pkr(net_profit_num),
            "net_profit_num": str(net_profit_num),
            "is_order_returned": is_order_returned,  # Added for consistency in stats calculation
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
        except:
            pass
    if end:
        try:
            e = datetime.strptime(end, "%Y-%MM-%d").date()
            if d > e: return False
        except:
            pass
    return True


def _compute_stats(orders_view):
    """
    MODIFIED: Calculates Total Vendor Cost Liability, Payments Made, and Net Payables
    on a per-vendor basis, as well as a grand total.
    """
    # Initialize liability split based on VENDOR_CHOICES
    liability_split = {v: Decimal("0") for v in VENDOR_CHOICES}
    net_profit_collected = Decimal("0")

    # 1. Calculate Total Vendor Cost Liability (per vendor)
    for o in orders_view:
        order_is_returned = o.get("is_order_returned", False)

        for it in o.get("items_list", []):
            qty = _d(it.get("quantity") or 1)
            pc = _d(it.get("product_cost"))
            pk = _d(it.get("packaging"))
            vendor = (it.get("vendor") or "Other")

            # Determine if item is returned based on either order status or item status
            status_text = (it.get("status") or "").lower()
            is_item_returned = order_is_returned or ("return" in status_text)

            # Effective Product Cost: 0 if returned, full cost otherwise.
            eff_pc = Decimal("0") if is_item_returned else pc

            # Total liability for this item = Effective Product Cost + Full Packaging Cost
            line_cost = (eff_pc * qty) + (pk * qty)

            # Accumulate liability per vendor
            if vendor in liability_split:
                liability_split[vendor] += line_cost
            else:
                liability_split["Other"] += line_cost

        # collected net profit (only if finance marked Paid)
        if str(o.get("paid_status", "")).lower().startswith("paid"):
            net_profit_collected += _d(o.get("net_profit_num") or 0)

    # 2. Get Total Payments Made (per vendor)
    payments_made_split = _load_db_payments_total()  # This now returns a dict of vendor: amount

    # 3. Calculate Final Net Payables (per vendor and grand total)
    net_payables_raw_per_vendor = {}
    total_vendor_cost_raw = Decimal("0")
    total_paid_raw = Decimal("0")

    for vendor in VENDOR_CHOICES:
        liability = liability_split.get(vendor, Decimal("0"))
        paid = payments_made_split.get(vendor, Decimal("0"))

        payable = liability - paid
        net_payables_raw_per_vendor[vendor] = payable

        total_vendor_cost_raw += liability
        total_paid_raw += paid

    net_payables_raw = total_vendor_cost_raw - total_paid_raw

    # Prepare final stats output structure
    stats = {
        "vendor_cost_total": _fmt_pkr(total_vendor_cost_raw),
        "total_paid": _fmt_pkr(total_paid_raw),
        "net_payables": _fmt_pkr(net_payables_raw),
        "net_payables_raw": net_payables_raw,
        "net_profit_collected": _fmt_pkr(net_profit_collected),

        # Total Cost Liability Split (Original Card 1 detail)
        "liability_tick": _fmt_pkr(liability_split.get("Tick Bags", Decimal("0"))),
        "liability_sleek": _fmt_pkr(liability_split.get("Sleek Space", Decimal("0"))),
        "liability_other": _fmt_pkr(liability_split.get("Other", Decimal("0"))),

        # NEW: Net Payables Split (For the second card detail)
        "payables_tick": _fmt_pkr(net_payables_raw_per_vendor.get("Tick Bags", Decimal("0"))),
        "payables_sleek": _fmt_pkr(net_payables_raw_per_vendor.get("Sleek Space", Decimal("0"))),
        "payables_other": _fmt_pkr(net_payables_raw_per_vendor.get("Other", Decimal("0"))),
    }

    return stats


# ---------- Routes ----------
@app.route("/")
def page():
    if LOAD_ERROR:
        # Now handles both API and initial DB connection errors
        return f"<h3>Application Startup Error</h3><pre>{LOAD_ERROR}</pre>", 502

    # Date filters (do NOT refetch from Daraz; filter the cached set)
    start_q = request.args.get("from") or CREATED_AFTER_DISPLAY
    end_q = request.args.get("to") or None

    filtered_raw = [o for o in RAW_ORDERS_CACHE if _within_range(o.get("order_date", ""), start_q, end_q)]
    orders_view = _build_runtime_view(filtered_raw)
    stats = _compute_stats(orders_view)

    # Note: tqm.html is not provided, assuming it exists
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
    Saves to tqm_product_costs table.
    """
    data = request.get_json(force=True, silent=True) or {}
    key = (data.get("key") or "").strip()
    if not key:
        return jsonify({"ok": False, "error": "Missing item key"}), 400

    try:
        # Convert to Decimal/string for storage, _d handles cleaning input
        pc = str(_d(data.get("product_cost")))
        pk = str(_d(data.get("packaging")))
    except Exception:
        return jsonify({"ok": False, "error": "Invalid amounts"}), 400

    vendor = (data.get("vendor") or "Other").strip()
    if vendor not in VENDOR_CHOICES:
        vendor = "Other"

    # --- DATABASE SAVE ---
    success = _save_db_cost(key, pc, pk, vendor)
    if not success:
        return jsonify({"ok": False, "error": "Database error saving cost."}), 500
    # ---------------------

    return jsonify({"ok": True})


@app.post("/api/record_payment")
def api_record_payment():
    """
    NEW ENDPOINT: Records a payment to the vendor_payments table.
    Body JSON: {"vendor": "Tick Bags", "amount": 10000.00, "date": "2025-10-24"}
    """
    data = request.get_json(force=True, silent=True) or {}
    vendor = (data.get("vendor") or "").strip()
    date_str = (data.get("date") or "").strip()
    user_id = os.getenv("USER_ID", "default-user-id")  # Using placeholder for user ID

    try:
        amount = _d(data.get("amount"))
        if amount <= 0:
            return jsonify({"ok": False, "error": "Amount must be greater than zero."}), 400
        # Check date format (YYYY-MM-DD)
        datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid amount or date format (use YYYY-MM-DD)."}), 400

    if vendor not in VENDOR_CHOICES:
        return jsonify({"ok": False, "error": "Invalid vendor selected."}), 400

    # --- DATABASE SAVE ---
    # Convert amount to Decimal for storage consistency
    success = _save_db_payment(vendor, amount, date_str, user_id)
    if not success:
        return jsonify({"ok": False, "error": "Database error recording payment."}), 500
    # ---------------------

    return jsonify({"ok": True})


@app.get("/api/get_payments")
def api_get_payments():
    """
    NEW ENDPOINT: Fetches the list of all vendor payments for the history modal.
    """
    user_id = os.getenv("USER_ID", "default-user-id")  # Using placeholder for user ID

    # --- DATABASE LOAD ---
    history = _load_db_vendor_payments(user_id)
    # ---------------------

    return jsonify({"ok": True, "history": history})


if __name__ == "__main__":
    print("Open: http://127.0.0.1:5000/")
    app.run(debug=True)
