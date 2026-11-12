"""Campus Bites: Flask + Firestore backend.
Customers order at  /      Canteen staff manage orders at  /admin
"""
import json, os, secrets
from flask import Flask, request, jsonify, send_from_directory, Response
from google.cloud import firestore

app = Flask(__name__)

# --- Firestore connection -------------------------------------------------
key = os.environ.get("FIREBASE_KEY_JSON")  # paste the service-account JSON here when hosting
db = (firestore.Client.from_service_account_info(json.loads(key))
      if key else firestore.Client())      # locally: uses GOOGLE_APPLICATION_CREDENTIALS

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]   # required, choose a strong one
METHODS = {"wallet", "upi", "card"}
NEXT = {"Preparing": "Ready for Pickup", "Ready for Pickup": "Completed"}


def need_admin(f):
    def wrapper(*a, **kw):
        auth = request.authorization
        ok = (auth and secrets.compare_digest(auth.username or "", ADMIN_USER)
              and secrets.compare_digest(auth.password or "", ADMIN_PASSWORD))
        if not ok:
            return Response("Login required", 401, {"WWW-Authenticate": 'Basic realm="Canteen staff"'})
        return f(*a, **kw)
    wrapper.__name__ = f.__name__
    return wrapper


def to_json(doc):
    d = doc.to_dict()
    d["id"] = doc.id
    for k in ("createdAt", "acceptedAt"):
        if d.get(k):
            d[k] = d[k].isoformat()
    return d


@app.get("/")
def home():
    return send_from_directory("pages", "index.html")


@app.get("/admin")
@need_admin
def admin():
    return send_from_directory("pages", "admin.html")


@app.post("/api/orders")
def create_order():
    b = request.get_json(silent=True) or {}
    name, college = str(b.get("name", "")).strip()[:60], str(b.get("college", "")).strip()[:30]
    items = b.get("items")
    if not name or not college or b.get("method") not in METHODS:
        return jsonify(error="invalid"), 400
    if not isinstance(items, list) or not 1 <= len(items) <= 30:
        return jsonify(error="invalid items"), 400
    clean, amount = [], 0
    for i in items:
        try:
            qty, price = int(i["qty"]), int(i["price"])
            assert 1 <= qty <= 20 and 0 < price <= 2000
            clean.append({"name": str(i["name"])[:60], "qty": qty, "price": price})
            amount += qty * price
        except Exception:
            return jsonify(error="invalid items"), 400
    ref = db.collection("orders").document()
    ref.set({"name": name, "college": college, "canteen": str(b.get("canteen", ""))[:60],
             "items": clean, "amount": amount, "method": b["method"],
             "mins": min(int(b.get("mins") or 10), 120),
             "status": "Pending", "token": None, "createdAt": firestore.SERVER_TIMESTAMP})
    return jsonify(id=ref.id), 201


@app.get("/api/orders/<oid>")
def get_order(oid):
    doc = db.collection("orders").document(oid).get()
    if not doc.exists:
        return jsonify(error="not found"), 404
    d = to_json(doc)
    d.pop("college", None)
    return jsonify(d)


@app.get("/api/admin/orders")
@need_admin
def list_orders():
    q = db.collection("orders").order_by("createdAt", direction=firestore.Query.DESCENDING).limit(100)
    return jsonify([to_json(d) for d in q.stream()])


@firestore.transactional
def _accept(tx, oref, cref):
    o = oref.get(transaction=tx)
    if not o.exists or o.get("status") != "Pending":
        return None
    c = cref.get(transaction=tx)
    n = (c.get("n") if c.exists else 1000) + 1       # tokens: 1001, 1002, ...
    tx.set(cref, {"n": n})
    tx.update(oref, {"status": "Preparing", "token": n, "acceptedAt": firestore.SERVER_TIMESTAMP})
    return n


@app.post("/api/admin/orders/<oid>/<action>")
@need_admin
def act(oid, action):
    oref = db.collection("orders").document(oid)
    if action == "accept":
        n = _accept(db.transaction(), oref, db.collection("meta").document("counter"))
        return (jsonify(token=n), 200) if n else (jsonify(error="not pending"), 409)
    doc = oref.get()
    if not doc.exists:
        return jsonify(error="not found"), 404
    st = doc.get("status")
    if action == "reject" and st == "Pending":
        oref.update({"status": "Rejected"})
    elif action == "advance" and st in NEXT:
        oref.update({"status": NEXT[st]})
    else:
        return jsonify(error="not allowed"), 409
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
