import sqlite3
from werkzeug.security import generate_password_hash

# إنشاء قاعدة البيانات
conn = sqlite3.connect('supermarket.db')
cursor = conn.cursor()

# جدول الموظفين
cursor.execute('''
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL
)
''')

# جدول شجرة الحسابات
cursor.execute('''
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_code TEXT UNIQUE NOT NULL,
    account_name TEXT NOT NULL,
    account_type TEXT NOT NULL,
    parent_id INTEGER,
    balance REAL DEFAULT 0,
    description TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES accounts (id)
)
''')

# جدول القيود اليومية
cursor.execute('''
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_number TEXT UNIQUE NOT NULL,
    entry_date TEXT NOT NULL,
    description TEXT,
    reference_type TEXT,
    reference_id INTEGER,
    created_by INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (created_by) REFERENCES employees (id)
)
''')

# جدول تفصيل القيود
cursor.execute('''
CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    description TEXT,
    FOREIGN KEY (entry_id) REFERENCES journal_entries (id),
    FOREIGN KEY (account_id) REFERENCES accounts (id)
)
''')

# جدول المنتجات
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    cost_price REAL DEFAULT 0,
    quantity INTEGER NOT NULL DEFAULT 0,
    min_stock INTEGER DEFAULT 5,
    barcode TEXT UNIQUE,
    category TEXT,
    supplier TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
''')

# جدول الفواتير
cursor.execute('''
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    total REAL NOT NULL,
    discount REAL DEFAULT 0,
    final_total REAL NOT NULL,
    payment_method TEXT NOT NULL,
    cashier_id INTEGER,
    cashier_name TEXT,
    date TEXT NOT NULL,
    status TEXT DEFAULT 'completed',
    FOREIGN KEY (cashier_id) REFERENCES employees (id)
)
''')

# جدول تفاصيل الفاتورة
cursor.execute('''
CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER,
    product_id INTEGER,
    product_name TEXT,
    quantity INTEGER,
    price REAL,
    subtotal REAL,
    FOREIGN KEY (invoice_id) REFERENCES invoices (id),
    FOREIGN KEY (product_id) REFERENCES products (id)
)
''')

# جدول حركة المخزون
cursor.execute('''
CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    product_name TEXT,
    quantity INTEGER,
    movement_type TEXT NOT NULL,
    reason TEXT,
    reference_id INTEGER,
    employee_id INTEGER,
    employee_name TEXT,
    date TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products (id),
    FOREIGN KEY (employee_id) REFERENCES employees (id)
)
''')

# جدول الموردين
cursor.execute('''
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    email TEXT,
    created_at TEXT NOT NULL
)
''')

# إضافة شجرة الحسابات الافتراضية
accounts = [
    # الأصول
    ('1000', 'الأصول', 'asset', None, 0, 'الحسابات الرئيسية للأصول'),
    ('1100', 'النقدية', 'asset', 1, 0, 'الصندوق النقدي'),
    ('1200', 'البنوك', 'asset', 1, 0, 'حسابات البنوك'),
    ('1300', 'المخزون', 'asset', 1, 0, 'قيمة المخزون'),
    ('1400', 'أصول ثابتة', 'asset', 1, 0, 'أصول ثابتة'),
    
    # الخصوم
    ('2000', 'الخصوم', 'liability', None, 0, 'الحسابات الرئيسية للخصوم'),
    ('2100', 'حسابات دائنة (موردين)', 'liability', 7, 0, 'حسابات الموردين'),
    ('2200', 'قروض', 'liability', 7, 0, 'القروض طويلة الأجل'),
    
    # حقوق الملكية
    ('3000', 'حقوق الملكية', 'equity', None, 0, 'حقوق الملكية'),
    ('3100', 'رأس المال', 'equity', 10, 0, 'رأس المال المدفوع'),
    ('3200', 'الأرباح المحتجزة', 'equity', 10, 0, 'الأرباح المحتجزة'),
    
    # الإيرادات
    ('4000', 'الإيرادات', 'revenue', None, 0, 'الحسابات الرئيسية للإيرادات'),
    ('4100', 'مبيعات', 'revenue', 13, 0, 'إيرادات المبيعات'),
    ('4200', 'إيرادات أخرى', 'revenue', 13, 0, 'إيرادات أخرى'),
    
    # المصروفات
    ('5000', 'المصروفات', 'expense', None, 0, 'الحسابات الرئيسية للمصروفات'),
    ('5100', 'تكلفة البضاعة المباعة', 'expense', 16, 0, 'تكلفة البضاعة المباعة'),
    ('5200', 'مرتبات', 'expense', 16, 0, 'مرتبات الموظفين'),
    ('5300', 'إيجار', 'expense', 16, 0, 'مصروفات الإيجار'),
    ('5400', 'مرافق', 'expense', 16, 0, 'مصروفات المرافق'),
    ('5500', 'مصروفات أخرى', 'expense', 16, 0, 'مصروفات تشغيلية أخرى'),
]

cursor.executemany('''
    INSERT OR IGNORE INTO accounts 
    (account_code, account_name, account_type, parent_id, balance, description, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', [(acc[0], acc[1], acc[2], acc[3], acc[4], acc[5], '2024-01-01') for acc in accounts])

# إضافة موظف افتراضي (مسؤول)
admin_password = generate_password_hash('admin123')
cursor.execute('''
    INSERT OR IGNORE INTO employees 
    (username, password, full_name, role, created_at)
    VALUES (?, ?, ?, ?, ?)
''', ('admin', admin_password, 'المسؤول الرئيسي', 'admin', '2024-01-01'))

# إضافة منتجات تجريبية
products = [
    ('أرز 1 كيلو', 25.0, 18.0, 100, 10, '123456789001', 'أغذية', 'شركة النور', '2024-01-01', '2024-01-01'),
    ('سكر 1 كيلو', 15.0, 10.0, 150, 15, '123456789002', 'أغذية', 'شركة السكر', '2024-01-01', '2024-01-01'),
    ('زيت ذرة 1 لتر', 35.0, 25.0, 80, 8, '123456789003', 'أغذية', 'شركة الزيوت', '2024-01-01', '2024-01-01'),
    ('صابون سائل', 12.0, 7.0, 200, 20, '123456789004', 'منظفات', 'شركة النظافة', '2024-01-01', '2024-01-01'),
    ('شامبو 250 مل', 45.0, 30.0, 60, 6, '123456789005', 'مستحضرات', 'شركة التجميل', '2024-01-01', '2024-01-01'),
]

cursor.executemany('''
    INSERT OR IGNORE INTO products 
    (name, price, cost_price, quantity, min_stock, barcode, category, supplier, created_at, updated_at) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', products)

# إضافة موردين تجريبيين
suppliers = [
    ('شركة النور للأغذية', '01000000001', 'القاهرة', 'nour@company.com', '2024-01-01'),
    ('شركة السكر المصرية', '01000000002', 'الجيزة', 'sugar@company.com', '2024-01-01'),
]

cursor.executemany('''
    INSERT OR IGNORE INTO suppliers (name, phone, address, email, created_at)
    VALUES (?, ?, ?, ?, ?)
''', suppliers)
# جدول أوامر الشراء
cursor.execute('''
CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_number TEXT UNIQUE NOT NULL,
    supplier_id INTEGER,
    supplier_name TEXT NOT NULL,
    total_amount REAL NOT NULL,
    discount REAL DEFAULT 0,
    final_amount REAL NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, received, cancelled
    order_date TEXT NOT NULL,
    expected_date TEXT,
    received_date TEXT,
    notes TEXT,
    created_by INTEGER,
    created_by_name TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
    FOREIGN KEY (created_by) REFERENCES employees (id)
)
''')

# جدول تفصيل أوامر الشراء
cursor.execute('''
CREATE TABLE IF NOT EXISTS purchase_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id INTEGER NOT NULL,
    product_id INTEGER,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    cost_price REAL NOT NULL,
    selling_price REAL,
    subtotal REAL NOT NULL,
    received_quantity INTEGER DEFAULT 0,
    FOREIGN KEY (po_id) REFERENCES purchase_orders (id),
    FOREIGN KEY (product_id) REFERENCES products (id)
)
''')

# جدول حسابات الموردين
cursor.execute('''
CREATE TABLE IF NOT EXISTS supplier_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL, -- purchase, payment, return
    reference_id INTEGER, -- po_id or payment_id
    reference_number TEXT,
    debit REAL DEFAULT 0, -- المبالغ المستحقة
    credit REAL DEFAULT 0, -- المبالغ المدفوعة
    balance REAL DEFAULT 0,
    date TEXT NOT NULL,
    notes TEXT,
    created_by INTEGER,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
    FOREIGN KEY (created_by) REFERENCES employees (id)
)
''')

# جدول مدفوعات الموردين
cursor.execute('''
CREATE TABLE IF NOT EXISTS supplier_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_number TEXT UNIQUE NOT NULL,
    supplier_id INTEGER NOT NULL,
    supplier_name TEXT NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT NOT NULL, -- cash, bank_transfer, check
    payment_date TEXT NOT NULL,
    notes TEXT,
    created_by INTEGER,
    created_by_name TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
    FOREIGN KEY (created_by) REFERENCES employees (id)
)
''')

# جدول المرتجعات للموردين
cursor.execute('''
CREATE TABLE IF NOT EXISTS supplier_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_number TEXT UNIQUE NOT NULL,
    supplier_id INTEGER NOT NULL,
    supplier_name TEXT NOT NULL,
    po_id INTEGER,
    po_number TEXT,
    total_amount REAL NOT NULL,
    reason TEXT,
    status TEXT DEFAULT 'pending', -- pending, approved, rejected
    return_date TEXT NOT NULL,
    created_by INTEGER,
    created_by_name TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
    FOREIGN KEY (po_id) REFERENCES purchase_orders (id),
    FOREIGN KEY (created_by) REFERENCES employees (id)
)
''')

# جدول تفصيل مرتجعات الموردين
cursor.execute('''
CREATE TABLE IF NOT EXISTS supplier_return_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id INTEGER NOT NULL,
    product_id INTEGER,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    cost_price REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY (return_id) REFERENCES supplier_returns (id),
    FOREIGN KEY (product_id) REFERENCES products (id)
)
''')
conn.commit()
conn.close()

print("✅ تم إنشاء قاعدة البيانات بنجاح!")
print("✅ تم إضافة شجرة الحسابات!")
print("✅ تم إضافة موظف افتراضي: اسم المستخدم: admin | كلمة المرور: admin123")
print("✅ تم إضافة منتجات تجريبية!")
print("✅ تم إضافة موردين تجريبيين!")
print("✅ تم إعداد قاعدة البيانات بالكامل وجاهزة للاستخدام!")