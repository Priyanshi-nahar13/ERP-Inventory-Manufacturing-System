# ERP — Inventory & Manufacturing System
A complete small-business ERP built with Python Flask + SQLite.

## Quick Start

### 1. Install Python (3.9+)
Download from https://python.org

### 2. Install Flask
```bash
pip install flask
```

### 3. Run the app
```bash
python app.py
```

### 4. Open in browser
Go to: http://127.0.0.1:5000

### 5. Login
- Username: **admin**
- Password: **admin123**

---

## Modules

| Module | What it does |
|--------|-------------|
| Dashboard | Overview of all KPIs, alerts, sales |
| Raw Materials | Add/edit/delete materials, track quantities |
| Products | Manage finished goods and prices |
| Bill of Materials | Define which materials make each product |
| Manufacturing | Run production — auto-deducts materials |
| Sales | Record sales — auto-deducts product stock |
| Reports | Profit & revenue analytics per product |

---

## File Structure

```
erp/
├── app.py              # Main Flask app (all backend logic)
├── erp.db              # SQLite database (auto-created on first run)
├── requirements.txt    # Python dependencies
└── templates/
    ├── base.html       # Sidebar layout shared by all pages
    ├── login.html      # Login page
    ├── dashboard.html  # Main dashboard
    ├── materials.html  # Raw materials management
    ├── products.html   # Product management
    ├── bom.html        # Bill of Materials
    ├── manufacturing.html  # Production runs
    ├── sales.html      # Sales recording
    └── reports.html    # Profit reports
```

---

## How Manufacturing Works
1. User selects a product and quantity
2. System looks up the BOM (Bill of Materials)
3. Checks if enough raw materials exist
4. If yes → deducts materials, adds to product stock, logs the run
5. If no → shows which materials are short

## How Sales Work
1. User selects a product and quantity to sell
2. System checks product stock
3. If sufficient → deducts stock, records sale with revenue
4. Revenue is calculated as: quantity × selling_price
