from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os

APP_TITLE = "دنگ حساب کن"
DATA_FILE = os.path.join(os.path.dirname(__file__), "members.json")

app = Flask(__name__)
app.secret_key = "replace-me-with-a-random-secret" 


def load_members():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            cleaned = []
            for item in data:
                name = str(item.get("name", "")).strip()
                try:
                    paid = float(item.get("paid", 0))
                except (TypeError, ValueError):
                    paid = 0.0
                if name:
                    cleaned.append({"name": name, "paid": round(paid, 2)})
            return cleaned
    except json.JSONDecodeError:
        return []


def save_members(members):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(members, f, ensure_ascii=False, indent=2)


def calculate_shares(members):
    n = len(members)
    total = round(sum(m["paid"] for m in members), 2)
    if n == 0:
        return 0.0, 0.0, []
    per_share = round(total / n, 2)

    balances = [{"name": m["name"], "paid": round(m["paid"], 2), "balance": round(m["paid"] - per_share, 2)} for m in members]
    return total, per_share, balances


def compute_transfers(balances):
    """Greedy pairing of debtors and creditors. Not necessarily minimal, but valid.
    Returns list of dicts: {"from": debtor, "to": creditor, "amount": x}
    """
    debtors = [{"name": b["name"], "amount": round(-b["balance"], 2)} for b in balances if b["balance"] < 0]
    creditors = [{"name": b["name"], "amount": round(b["balance"], 2)} for b in balances if b["balance"] > 0]

    transfers = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        d = debtors[i]
        c = creditors[j]
        amount = round(min(d["amount"], c["amount"]), 2)
        if amount > 0:
            transfers.append({"from": d["name"], "to": c["name"], "amount": amount})
            d["amount"] = round(d["amount"] - amount, 2)
            c["amount"] = round(c["amount"] - amount, 2)
        if d["amount"] <= 1e-9:
            i += 1
        if c["amount"] <= 1e-9:
            j += 1
    return transfers


@app.route("/")
def index():
    members = load_members()
    return render_template("index.html", title=APP_TITLE, members=members)


@app.route("/add", methods=["POST"])
def add_member():
    name = (request.form.get("name") or "").strip()
    paid_str = (request.form.get("paid") or "0").strip().replace(",", ".")
    try:
        paid = float(paid_str)
    except ValueError:
        paid = 0.0
    members = load_members()
    if not name:
        flash("نام نمی‌تواند خالی باشد.", "warning")
        return redirect(url_for("index"))
    members.append({"name": name, "paid": round(paid, 2)})
    save_members(members)
    flash("عضو جدید اضافه شد.", "success")
    return redirect(url_for("index"))


@app.route("/delete/<int:idx>", methods=["POST"])
def delete_member(idx):
    members = load_members()
    if 0 <= idx < len(members):
        removed = members.pop(idx)
        save_members(members)
        flash(f"عضو «{removed['name']}» حذف شد.", "info")
    return redirect(url_for("index"))


@app.route("/edit/<int:idx>", methods=["POST"])
def edit_member(idx):
    members = load_members()
    if 0 <= idx < len(members):
        paid_str = (request.form.get("paid") or "0").strip().replace(",", ".")
        try:
            paid = float(paid_str)
        except ValueError:
            paid = members[idx]["paid"]
        members[idx]["paid"] = round(paid, 2)
        save_members(members)
        flash(f"هزینهٔ «{members[idx]['name']}» به‌روزرسانی شد.", "success")
    return redirect(url_for("index"))


@app.route("/reset", methods=["POST"])
def reset_members():
    save_members([])
    flash("لیست اعضا ریست شد.", "info")
    return redirect(url_for("index"))


@app.route("/shares")
def shares():
    members = load_members()
    total, per_share, balances = calculate_shares(members)
    transfers = compute_transfers(balances)
    return render_template(
        "shares.html",
        title=APP_TITLE,
        members=members,
        total=total,
        per_share=per_share,
        balances=balances,
        transfers=transfers,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
