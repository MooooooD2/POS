
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
from datetime import datetime
import random
import hashlib
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta  # أضف timedelta هنا
import sqlite3
from werkzeug.security import generate_password_hash
import os
import shutil
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = 'supermarket_secret_key_2024'

# دالة الاتصال بقاعدة البيانات
def get_db_connection():
    conn = sqlite3.connect('supermarket.db')
    conn.row_factory = sqlite3.Row
    return conn

# دالة تشفير كلمة المرور
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ========================================
# صفحات عامة
# ========================================

@app.route('/')
def index():
    if 'employee_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        employee = conn.execute('''
            SELECT * FROM employees WHERE username = ?
        ''', (username,)).fetchone()
        conn.close()
        
        if employee and check_password_hash(employee['password'], password):
            session['employee_id'] = employee['id']
            session['username'] = employee['username']
            session['full_name'] = employee['full_name']
            session['role'] = employee['role']
            return jsonify({'success': True, 'redirect': '/'})
        else:
            return jsonify({'success': False, 'message': 'اسم المستخدم أو كلمة المرور غير صحيحة'})
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/get_session_info')
def get_session_info():
    if 'employee_id' in session:
        return jsonify({
            'logged_in': True,
            'username': session['username'],
            'full_name': session['full_name'],
            'role': session['role']
        })
    return jsonify({'logged_in': False})

# ========================================
# نظام المخزن
# ========================================

@app.route('/warehouse')
def warehouse():
    if 'employee_id' not in session:
        return redirect(url_for('login'))
    return render_template('warehouse.html')

# عرض جميع المنتجات في المخزن
@app.route('/api/products', methods=['GET'])
def get_all_products():
    conn = get_db_connection()
    products = conn.execute('''
        SELECT * FROM products ORDER BY id DESC
    ''').fetchall()
    conn.close()
    
    return jsonify({
        'products': [
            {
                'id': p['id'],
                'name': p['name'],
                'price': p['price'],
                'cost_price': p['cost_price'],
                'quantity': p['quantity'],
                'min_stock': p['min_stock'],
                'barcode': p['barcode'],
                'category': p['category'],
                'supplier': p['supplier'],
                'created_at': p['created_at'],
                'updated_at': p['updated_at'],
                'low_stock': p['quantity'] <= p['min_stock']
            }
            for p in products
        ]
    })

# إضافة منتج جديد
@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    name = data.get('name')
    price = float(data.get('price', 0))
    cost_price = float(data.get('cost_price', 0))
    quantity = int(data.get('quantity', 0))
    min_stock = int(data.get('min_stock', 5))
    barcode = data.get('barcode', '')
    category = data.get('category', '')
    supplier = data.get('supplier', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # التحقق من تكرار الباركود
    if barcode:
        existing = conn.execute('SELECT id FROM products WHERE barcode = ?', (barcode,)).fetchone()
        if existing:
            conn.close()
            return jsonify({'success': False, 'message': 'هذا الباركود موجود بالفعل'})
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO products 
        (name, price, cost_price, quantity, min_stock, barcode, category, supplier, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, price, cost_price, quantity, min_stock, barcode, category, supplier, now, now))
    
    product_id = cursor.lastrowid
    
    # تسجيل حركة المخزون
    cursor.execute('''
        INSERT INTO stock_movements 
        (product_id, product_name, quantity, movement_type, reason, employee_id, employee_name, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        product_id, name, quantity, 'add', 'إضافة منتج جديد', 
        session.get('employee_id'), session.get('full_name'),
        now
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم إضافة المنتج بنجاح'})

# تعديل منتج
@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.json
    name = data.get('name')
    price = float(data.get('price', 0))
    cost_price = float(data.get('cost_price', 0))
    min_stock = int(data.get('min_stock', 5))
    barcode = data.get('barcode', '')
    category = data.get('category', '')
    supplier = data.get('supplier', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # التحقق من تكرار الباركود
    if barcode:
        existing = conn.execute('''
            SELECT id FROM products WHERE barcode = ? AND id != ?
        ''', (barcode, product_id)).fetchone()
        if existing:
            conn.close()
            return jsonify({'success': False, 'message': 'هذا الباركود موجود بالفعل'})
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        UPDATE products 
        SET name = ?, price = ?, cost_price = ?, min_stock = ?, 
            barcode = ?, category = ?, supplier = ?, updated_at = ?
        WHERE id = ?
    ''', (name, price, cost_price, min_stock, barcode, category, supplier, now, product_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم تعديل المنتج بنجاح'})

# حذف منتج
@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم حذف المنتج بنجاح'})

# إضافة كمية لمنتج موجود
@app.route('/api/products/<int:product_id>/add_stock', methods=['POST'])
def add_stock(product_id):
    data = request.json
    quantity = int(data.get('quantity', 0))
    reason = data.get('reason', 'إضافة مخزون')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # تحديث الكمية
    cursor.execute('''
        UPDATE products 
        SET quantity = quantity + ?, updated_at = ?
        WHERE id = ?
    ''', (quantity, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), product_id))
    
    # الحصول على اسم المنتج
    product = conn.execute('SELECT name FROM products WHERE id = ?', (product_id,)).fetchone()
    
    # تسجيل حركة المخزون
    cursor.execute('''
        INSERT INTO stock_movements 
        (product_id, product_name, quantity, movement_type, reason, employee_id, employee_name, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        product_id, product['name'], quantity, 'add', reason,
        session.get('employee_id'), session.get('full_name'),
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم إضافة الكمية بنجاح'})

# ========================================
# نظام الكاشير
# ========================================

# البحث عن منتج بالباركود أو الاسم
@app.route('/api/search_product', methods=['POST'])
def search_product():
    data = request.json
    search_term = data.get('search', '')
    
    conn = get_db_connection()
    
    product = conn.execute('''
        SELECT * FROM products 
        WHERE barcode = ? OR name LIKE ?
        AND quantity > 0
    ''', (search_term, f'%{search_term}%')).fetchone()
    
    conn.close()
    
    if product:
        return jsonify({
            'success': True,
            'product': {
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': product['quantity'],
                'category': product['category']
            }
        })
    else:
        return jsonify({'success': False, 'message': 'المنتج غير موجود أو نفذ المخزون'})

# إنشاء فاتورة جديدة
@app.route('/api/create_invoice', methods=['POST'])
def create_invoice():
    if 'employee_id' not in session:
        return jsonify({'success': False, 'message': 'يجب تسجيل الدخول'})
    
    data = request.json
    items = data.get('items', [])
    payment_method = data.get('payment_method', 'كاش')
    discount = float(data.get('discount', 0))
    
    if not items:
        return jsonify({'success': False, 'message': 'لا يوجد منتجات'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # حساب الإجمالي
    subtotal = sum(item['quantity'] * item['price'] for item in items)
    final_total = subtotal - discount
    
    # إنشاء رقم فاتورة فريد
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # حفظ الفاتورة
    cursor.execute('''
        INSERT INTO invoices 
        (invoice_number, total, discount, final_total, payment_method, cashier_id, cashier_name, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        invoice_number, subtotal, discount, final_total, payment_method,
        session['employee_id'], session['full_name'], date
    ))
    
    invoice_id = cursor.lastrowid
    
    # حفظ تفاصيل الفاتورة وخصم الكميات
    for item in items:
        cursor.execute('''
            INSERT INTO invoice_items 
            (invoice_id, product_id, product_name, quantity, price, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            invoice_id,
            item['id'],
            item['name'],
            item['quantity'],
            item['price'],
            item['quantity'] * item['price']
        ))
        
        # خصم الكمية من المخزون
        cursor.execute('''
            UPDATE products 
            SET quantity = quantity - ? 
            WHERE id = ?
        ''', (item['quantity'], item['id']))
        
        # تسجيل حركة المخزون
        cursor.execute('''
            INSERT INTO stock_movements 
            (product_id, product_name, quantity, movement_type, reason, reference_id, employee_id, employee_name, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item['id'], item['name'], item['quantity'], 'sale', 'بيع',
            invoice_id, session['employee_id'], session['full_name'], date
        ))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'invoice_number': invoice_number,
        'total': final_total,
        'items': items,
        'payment_method': payment_method,
        'cashier': session['full_name'],
        'date': date
    })

# ========================================
# التقارير
# ========================================

@app.route('/reports')
def reports():
    if 'employee_id' not in session:
        return redirect(url_for('login'))
    return render_template('reports.html')

# تقرير المبيعات
@app.route('/api/reports/sales', methods=['POST'])
def sales_report():
    data = request.json
    report_type = data.get('type', 'daily')  # daily, weekly, monthly, custom
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    conn = get_db_connection()
    
    # تحديد الفترة الزمنية
    if report_type == 'daily':
        date_filter = datetime.now().strftime('%Y-%m-%d')
        query = '''
            SELECT * FROM invoices 
            WHERE date LIKE ? AND status = 'completed'
            ORDER BY date DESC
        '''
        invoices = conn.execute(query, (f'{date_filter}%',)).fetchall()
    
    elif report_type == 'weekly':
        query = '''
            SELECT * FROM invoices 
            WHERE date >= date('now', '-7 days') AND status = 'completed'
            ORDER BY date DESC
        '''
        invoices = conn.execute(query).fetchall()
    
    elif report_type == 'monthly':
        query = '''
            SELECT * FROM invoices 
            WHERE date >= date('now', '-30 days') AND status = 'completed'
            ORDER BY date DESC
        '''
        invoices = conn.execute(query).fetchall()
    
    elif report_type == 'custom' and start_date and end_date:
        query = '''
            SELECT * FROM invoices 
            WHERE date BETWEEN ? AND ? AND status = 'completed'
            ORDER BY date DESC
        '''
        invoices = conn.execute(query, (start_date, end_date)).fetchall()
    
    # حساب الإحصائيات
    total_sales = sum(inv['final_total'] for inv in invoices)
    total_invoices = len(invoices)
    
    # المنتجات الأعلى مبيعاً
    query = '''
        SELECT product_name, SUM(quantity) as total_quantity, SUM(subtotal) as total_sales
        FROM invoice_items
        WHERE invoice_id IN (
            SELECT id FROM invoices WHERE status = 'completed'
        '''
    
    if report_type == 'daily':
        query += " AND date LIKE '" + datetime.now().strftime('%Y-%m-%d') + "%'"
    elif report_type == 'weekly':
        query += " AND date >= date('now', '-7 days')"
    elif report_type == 'monthly':
        query += " AND date >= date('now', '-30 days')"
    elif report_type == 'custom':
        query += f" AND date BETWEEN '{start_date}' AND '{end_date}'"
    
    query += ")"
    query += " GROUP BY product_name ORDER BY total_quantity DESC LIMIT 10"
    
    top_products = conn.execute(query).fetchall()
    
    conn.close()
    
    return jsonify({
        'success': True,
        'invoices': [
            {
                'invoice_number': inv['invoice_number'],
                'total': inv['final_total'],
                'payment_method': inv['payment_method'],
                'cashier': inv['cashier_name'],
                'date': inv['date']
            }
            for inv in invoices
        ],
        'statistics': {
            'total_sales': total_sales,
            'total_invoices': total_invoices
        },
        'top_products': [
            {
                'name': p['product_name'],
                'quantity': p['total_quantity'],
                'sales': p['total_sales']
            }
            for p in top_products
        ]
    })

# تقرير المخزون
@app.route('/api/reports/stock')
def stock_report():
    conn = get_db_connection()
    
    # المنتجات منخفضة المخزون
    low_stock = conn.execute('''
        SELECT * FROM products WHERE quantity <= min_stock
        ORDER BY quantity ASC
    ''').fetchall()
    
    # المنتجات نفذت
    out_of_stock = conn.execute('''
        SELECT * FROM products WHERE quantity = 0
    ''').fetchall()
    
    # إجمالي عدد المنتجات
    total_products = conn.execute('SELECT COUNT(*) as count FROM products').fetchone()['count']
    total_quantity = conn.execute('SELECT SUM(quantity) as total FROM products').fetchone()['total']
    
    conn.close()
    
    return jsonify({
        'low_stock': [
            {
                'name': p['name'],
                'quantity': p['quantity'],
                'min_stock': p['min_stock'],
                'category': p['category']
            }
            for p in low_stock
        ],
        'out_of_stock': [
            {
                'name': p['name'],
                'category': p['category']
            }
            for p in out_of_stock
        ],
        'summary': {
            'total_products': total_products,
            'total_quantity': total_quantity or 0,
            'low_stock_count': len(low_stock),
            'out_of_stock_count': len(out_of_stock)
        }
    })
# ========================================
# شجرة الحسابات
# ========================================

@app.route('/accounting')
def accounting():
    if 'employee_id' not in session:
        return redirect(url_for('login'))
    return render_template('accounting.html')

# عرض شجرة الحسابات
@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    conn = get_db_connection()
    
    # الحصول على الحسابات الرئيسية
    main_accounts = conn.execute('''
        SELECT * FROM accounts WHERE parent_id IS NULL
        ORDER BY account_code
    ''').fetchall()
    
    # بناء الشجرة بشكل هرمي
    accounts_tree = []
    
    for main_acc in main_accounts:
        account_dict = {
            'id': main_acc['id'],
            'account_code': main_acc['account_code'],
            'account_name': main_acc['account_name'],
            'account_type': main_acc['account_type'],
            'balance': main_acc['balance'],
            'description': main_acc['description'],
            'children': []
        }
        
        # الحصول على الحسابات الفرعية
        sub_accounts = conn.execute('''
            SELECT * FROM accounts 
            WHERE parent_id = ?
            ORDER BY account_code
        ''', (main_acc['id'],)).fetchall()
        
        for sub_acc in sub_accounts:
            account_dict['children'].append({
                'id': sub_acc['id'],
                'account_code': sub_acc['account_code'],
                'account_name': sub_acc['account_name'],
                'account_type': sub_acc['account_type'],
                'balance': sub_acc['balance'],
                'description': sub_acc['description']
            })
        
        accounts_tree.append(account_dict)
    
    conn.close()
    
    return jsonify({'accounts': accounts_tree})

# إضافة حساب جديد
@app.route('/api/accounts', methods=['POST'])
def add_account():
    data = request.json
    account_code = data.get('account_code')
    account_name = data.get('account_name')
    account_type = data.get('account_type')
    parent_id = data.get('parent_id')
    description = data.get('description', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # التحقق من تكرار كود الحساب
    existing = conn.execute('SELECT id FROM accounts WHERE account_code = ?', (account_code,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'success': False, 'message': 'كود الحساب موجود بالفعل'})
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO accounts 
        (account_code, account_name, account_type, parent_id, balance, description, created_at)
        VALUES (?, ?, ?, ?, 0, ?, ?)
    ''', (account_code, account_name, account_type, parent_id, description, now))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم إضافة الحساب بنجاح'})

# تعديل حساب
@app.route('/api/accounts/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    data = request.json
    account_code = data.get('account_code')
    account_name = data.get('account_name')
    description = data.get('description')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # التحقق من تكرار كود الحساب
    existing = conn.execute('''
        SELECT id FROM accounts WHERE account_code = ? AND id != ?
    ''', (account_code, account_id)).fetchone()
    
    if existing:
        conn.close()
        return jsonify({'success': False, 'message': 'كود الحساب موجود بالفعل'})
    
    cursor.execute('''
        UPDATE accounts 
        SET account_code = ?, account_name = ?, description = ?
        WHERE id = ?
    ''', (account_code, account_name, description, account_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم تعديل الحساب بنجاح'})

# حذف حساب
@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # التحقق من وجود حسابات فرعية
    has_children = conn.execute('SELECT id FROM accounts WHERE parent_id = ?', (account_id,)).fetchone()
    if has_children:
        conn.close()
        return jsonify({'success': False, 'message': 'لا يمكن حذف حساب رئيسي يحتوي على حسابات فرعية'})
    
    # التحقق من وجود قيود مرتبطة
    has_entries = conn.execute('''
        SELECT id FROM journal_entry_lines WHERE account_id = ?
    ''', (account_id,)).fetchone()
    
    if has_entries:
        conn.close()
        return jsonify({'success': False, 'message': 'لا يمكن حذف حساب مرتبط بقيود محاسبية'})
    
    cursor.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم حذف الحساب بنجاح'})

# ========================================
# القيود اليومية
# ========================================

# عرض القيود اليومية
@app.route('/api/journal_entries', methods=['GET'])
def get_journal_entries():
    conn = get_db_connection()
    
    entries = conn.execute('''
        SELECT je.*, e.full_name as created_by_name
        FROM journal_entries je
        LEFT JOIN employees e ON je.created_by = e.id
        ORDER BY je.entry_date DESC, je.id DESC
        LIMIT 50
    ''').fetchall()
    
    result = []
    for entry in entries:
        # الحصول على تفصيل القيود
        lines = conn.execute('''
            SELECT jel.*, a.account_code, a.account_name
            FROM journal_entry_lines jel
            JOIN accounts a ON jel.account_id = a.id
            WHERE jel.entry_id = ?
        ''', (entry['id'],)).fetchall()
        
        result.append({
            'id': entry['id'],
            'entry_number': entry['entry_number'],
            'entry_date': entry['entry_date'],
            'description': entry['description'],
            'reference_type': entry['reference_type'],
            'reference_id': entry['reference_id'],
            'created_by': entry['created_by'],
            'created_by_name': entry['created_by_name'],
            'created_at': entry['created_at'],
            'lines': [
                {
                    'id': line['id'],
                    'account_id': line['account_id'],
                    'account_code': line['account_code'],
                    'account_name': line['account_name'],
                    'debit': line['debit'],
                    'credit': line['credit'],
                    'description': line['description']
                }
                for line in lines
            ]
        })
    
    conn.close()
    
    return jsonify({'entries': result})

# إضافة قيد يومي جديد
@app.route('/api/journal_entries', methods=['POST'])
def add_journal_entry():
    data = request.json
    entry_date = data.get('entry_date', datetime.now().strftime('%Y-%m-%d'))
    description = data.get('description', '')
    reference_type = data.get('reference_type', '')
    reference_id = data.get('reference_id')
    lines = data.get('lines', [])
    
    # التحقق من صحة القيود (المدين = الدائن)
    total_debit = sum(line.get('debit', 0) for line in lines)
    total_credit = sum(line.get('credit', 0) for line in lines)
    
    if abs(total_debit - total_credit) > 0.01:
        return jsonify({'success': False, 'message': 'إجمالي المدين يجب أن يساوي إجمالي الدائن'})
    
    if len(lines) < 2:
        return jsonify({'success': False, 'message': 'القيد يجب أن يحتوي على حسابين على الأقل'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # إنشاء رقم قيد فريد
    entry_number = f"JE-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    
    # حفظ القيد الرئيسي
    cursor.execute('''
        INSERT INTO journal_entries 
        (entry_number, entry_date, description, reference_type, reference_id, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        entry_number, entry_date, description, reference_type, reference_id,
        session.get('employee_id'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    
    entry_id = cursor.lastrowid
    
    # حفظ تفصيل القيود وتحديث أرصدة الحسابات
    for line in lines:
        account_id = line.get('account_id')
        debit = float(line.get('debit', 0))
        credit = float(line.get('credit', 0))
        line_description = line.get('description', '')
        
        # حفظ تفصيل القيد
        cursor.execute('''
            INSERT INTO journal_entry_lines 
            (entry_id, account_id, debit, credit, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (entry_id, account_id, debit, credit, line_description))
        
        # تحديث رصيد الحساب
        if debit > 0:
            cursor.execute('''
                UPDATE accounts 
                SET balance = balance + ?
                WHERE id = ?
            ''', (debit, account_id))
        elif credit > 0:
            cursor.execute('''
                UPDATE accounts 
                SET balance = balance - ?
                WHERE id = ?
            ''', (credit, account_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'تم إضافة القيد بنجاح',
        'entry_number': entry_number
    })

# ========================================
# التقارير المالية
# ========================================

@app.route('/financial_reports')
def financial_reports():
    if 'employee_id' not in session:
        return redirect(url_for('login'))
    return render_template('financial_reports.html')

# قائمة الدخل (بيان الربح والخسارة)
@app.route('/api/reports/income_statement', methods=['POST'])
def income_statement():
    data = request.json
    report_type = data.get('type', 'monthly')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    conn = get_db_connection()
    
    # تحديد الفترة
    date_filter = ''
    params = []
    
    if report_type == 'daily':
        date_filter = "AND je.entry_date = ?"
        params.append(datetime.now().strftime('%Y-%m-%d'))
    elif report_type == 'weekly':
        date_filter = "AND je.entry_date >= date('now', '-7 days')"
    elif report_type == 'monthly':
        date_filter = "AND je.entry_date >= date('now', '-30 days')"
    elif report_type == 'custom' and start_date and end_date:
        date_filter = "AND je.entry_date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    
    # الإيرادات
    revenue_query = '''
        SELECT SUM(jel.credit) as total
        FROM journal_entry_lines jel
        JOIN accounts a ON jel.account_id = a.id
        JOIN journal_entries je ON jel.entry_id = je.id
        WHERE a.account_type = 'revenue'
    ''' + date_filter
    
    revenue = conn.execute(revenue_query, params).fetchone()['total'] or 0
    
    # تكلفة البضاعة المباعة
    cogs_query = '''
        SELECT SUM(jel.debit) as total
        FROM journal_entry_lines jel
        JOIN accounts a ON jel.account_id = a.id
        JOIN journal_entries je ON jel.entry_id = je.id
        WHERE a.account_code = '5100'
    ''' + date_filter
    
    cogs = conn.execute(cogs_query, params).fetchone()['total'] or 0
    
    # المصروفات التشغيلية
    expenses_query = '''
        SELECT SUM(jel.debit) as total
        FROM journal_entry_lines jel
        JOIN accounts a ON jel.account_id = a.id
        JOIN journal_entries je ON jel.entry_id = je.id
        WHERE a.account_type = 'expense' AND a.account_code != '5100'
    ''' + date_filter
    
    expenses = conn.execute(expenses_query, params).fetchone()['total'] or 0
    
    # حسابات المصروفات التفصيلية
    expenses_details_query = '''
        SELECT a.account_name, SUM(jel.debit) as amount
        FROM journal_entry_lines jel
        JOIN accounts a ON jel.account_id = a.id
        JOIN journal_entries je ON jel.entry_id = je.id
        WHERE a.account_type = 'expense' AND a.account_code != '5100'
    ''' + date_filter + '''
        GROUP BY a.id, a.account_name
        ORDER BY amount DESC
    '''
    
    expenses_details = conn.execute(expenses_details_query, params).fetchall()
    
    gross_profit = revenue - cogs
    net_profit = gross_profit - expenses
    
    conn.close()
    
    return jsonify({
        'success': True,
        'revenue': revenue,
        'cogs': cogs,
        'gross_profit': gross_profit,
        'expenses': expenses,
        'expenses_details': [
            {'account_name': e['account_name'], 'amount': e['amount']}
            for e in expenses_details
        ],
        'net_profit': net_profit
    })

# الميزانية العمومية
@app.route('/api/reports/balance_sheet')
def balance_sheet():
    conn = get_db_connection()
    
    # الأصول
    assets = conn.execute('''
        SELECT account_name, balance 
        FROM accounts 
        WHERE account_type = 'asset' AND balance != 0
        ORDER BY account_code
    ''').fetchall()
    
    total_assets = sum(a['balance'] for a in assets)
    
    # الخصوم
    liabilities = conn.execute('''
        SELECT account_name, balance 
        FROM accounts 
        WHERE account_type = 'liability' AND balance != 0
        ORDER BY account_code
    ''').fetchall()
    
    total_liabilities = sum(l['balance'] for l in liabilities)
    
    # حقوق الملكية
    equity = conn.execute('''
        SELECT account_name, balance 
        FROM accounts 
        WHERE account_type = 'equity' AND balance != 0
        ORDER BY account_code
    ''').fetchall()
    
    total_equity = sum(e['balance'] for e in equity)
    
    conn.close()
    
    return jsonify({
        'success': True,
        'assets': [
            {'account_name': a['account_name'], 'balance': a['balance']}
            for a in assets
        ],
        'total_assets': total_assets,
        'liabilities': [
            {'account_name': l['account_name'], 'balance': l['balance']}
            for l in liabilities
        ],
        'total_liabilities': total_liabilities,
        'equity': [
            {'account_name': e['account_name'], 'balance': e['balance']}
            for e in equity
        ],
        'total_equity': total_equity,
        'total_liabilities_equity': total_liabilities + total_equity
    })

# كشف الحساب التفصيلي
@app.route('/api/reports/account_statement/<int:account_id>', methods=['POST'])
def account_statement(account_id):
    data = request.json
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    conn = get_db_connection()
    
    # الحصول على معلومات الحساب
    account = conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()
    
    # الحصول على القيود
    date_filter = ''
    params = [account_id]
    
    if start_date and end_date:
        date_filter = "AND je.entry_date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    
    transactions = conn.execute(f'''
        SELECT je.entry_number, je.entry_date, je.description as entry_description,
               jel.debit, jel.credit, jel.description as line_description,
               je.reference_type, je.reference_id
        FROM journal_entry_lines jel
        JOIN journal_entries je ON jel.entry_id = je.id
        WHERE jel.account_id = ?
        {date_filter}
        ORDER BY je.entry_date, je.id
    ''', params).fetchall()
    
    # حساب الرصيد
    balance = account['balance']
    running_balance = 0
    
    # إعادة حساب الرصيد من البداية
    all_transactions = conn.execute('''
        SELECT jel.debit, jel.credit
        FROM journal_entry_lines jel
        WHERE jel.account_id = ?
        ORDER BY jel.id
    ''', (account_id,)).fetchall()
    
    for trans in all_transactions:
        running_balance += trans['debit'] - trans['credit']
    
    conn.close()
    
    return jsonify({
        'success': True,
        'account': {
            'id': account['id'],
            'account_code': account['account_code'],
            'account_name': account['account_name'],
            'balance': balance,
            'running_balance': running_balance
        },
        'transactions': [
            {
                'entry_number': t['entry_number'],
                'entry_date': t['entry_date'],
                'entry_description': t['entry_description'],
                'debit': t['debit'],
                'credit': t['credit'],
                'line_description': t['line_description'],
                'reference_type': t['reference_type'],
                'reference_id': t['reference_id']
            }
            for t in transactions
        ]
    })
    # ========================================
# إدارة الموردين
# ========================================

@app.route('/suppliers')
def suppliers_page():
    if 'employee_id' not in session:
        return redirect(url_for('login'))
    return render_template('suppliers.html')

# عرض جميع الموردين
@app.route('/api/suppliers', methods=['GET'])
def get_suppliers():
    conn = get_db_connection()
    
    suppliers = conn.execute('''
        SELECT s.*, 
               COUNT(po.id) as po_count,
               COALESCE(SUM(sa.balance), 0) as account_balance
        FROM suppliers s
        LEFT JOIN purchase_orders po ON s.id = po.supplier_id
        LEFT JOIN supplier_accounts sa ON s.id = sa.supplier_id
        GROUP BY s.id
        ORDER BY s.id DESC
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'suppliers': [
            {
                'id': s['id'],
                'name': s['name'],
                'phone': s['phone'],
                'address': s['address'],
                'email': s['email'],
                'po_count': s['po_count'],
                'account_balance': s['account_balance'],
                'created_at': s['created_at']
            }
            for s in suppliers
        ]
    })

# إضافة مورد جديد
@app.route('/api/suppliers', methods=['POST'])
def add_supplier():
    data = request.json
    name = data.get('name')
    phone = data.get('phone')
    address = data.get('address')
    email = data.get('email')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # التحقق من تكرار الهاتف
    if phone:
        existing = conn.execute('SELECT id FROM suppliers WHERE phone = ?', (phone,)).fetchone()
        if existing:
            conn.close()
            return jsonify({'success': False, 'message': 'رقم الهاتف موجود بالفعل'})
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO suppliers (name, phone, address, email, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, phone, address, email, now))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم إضافة المورد بنجاح'})

# تعديل مورد
@app.route('/api/suppliers/<int:supplier_id>', methods=['PUT'])
def update_supplier(supplier_id):
    data = request.json
    name = data.get('name')
    phone = data.get('phone')
    address = data.get('address')
    email = data.get('email')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # التحقق من تكرار الهاتف
    if phone:
        existing = conn.execute('''
            SELECT id FROM suppliers WHERE phone = ? AND id != ?
        ''', (phone, supplier_id)).fetchone()
        if existing:
            conn.close()
            return jsonify({'success': False, 'message': 'رقم الهاتف موجود بالفعل'})
    
    cursor.execute('''
        UPDATE suppliers 
        SET name = ?, phone = ?, address = ?, email = ?
        WHERE id = ?
    ''', (name, phone, address, email, supplier_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم تعديل المورد بنجاح'})

# حذف مورد
@app.route('/api/suppliers/<int:supplier_id>', methods=['DELETE'])
def delete_supplier(supplier_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # التحقق من وجود أوامر شراء مرتبطة
    has_po = conn.execute('SELECT id FROM purchase_orders WHERE supplier_id = ?', (supplier_id,)).fetchone()
    if has_po:
        conn.close()
        return jsonify({'success': False, 'message': 'لا يمكن حذف مورد مرتبط بأوامر شراء'})
    
    cursor.execute('DELETE FROM suppliers WHERE id = ?', (supplier_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم حذف المورد بنجاح'})

# ========================================
# أوامر الشراء
# ========================================

@app.route('/purchase_orders')
def purchase_orders_page():
    if 'employee_id' not in session:
        return redirect(url_for('login'))
    return render_template('purchase_orders.html')

# عرض جميع أوامر الشراء
@app.route('/api/purchase_orders', methods=['GET'])
def get_purchase_orders():
    conn = get_db_connection()
    
    purchase_orders = conn.execute('''
        SELECT po.*, s.name as supplier_name
        FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id = s.id
        ORDER BY po.id DESC
        LIMIT 50
    ''').fetchall()
    
    result = []
    for po in purchase_orders:
        # الحصول على تفصيل المنتجات
        items = conn.execute('''
            SELECT * FROM purchase_order_items WHERE po_id = ?
        ''', (po['id'],)).fetchall()
        
        result.append({
            'id': po['id'],
            'po_number': po['po_number'],
            'supplier_id': po['supplier_id'],
            'supplier_name': po['supplier_name'],
            'total_amount': po['total_amount'],
            'discount': po['discount'],
            'final_amount': po['final_amount'],
            'status': po['status'],
            'order_date': po['order_date'],
            'expected_date': po['expected_date'],
            'received_date': po['received_date'],
            'notes': po['notes'],
            'created_by_name': po['created_by_name'],
            'items': [
                {
                    'id': item['id'],
                    'product_id': item['product_id'],
                    'product_name': item['product_name'],
                    'quantity': item['quantity'],
                    'cost_price': item['cost_price'],
                    'selling_price': item['selling_price'],
                    'subtotal': item['subtotal'],
                    'received_quantity': item['received_quantity']
                }
                for item in items
            ]
        })
    
    conn.close()
    
    return jsonify({'purchase_orders': result})

# إنشاء أمر شراء جديد
@app.route('/api/purchase_orders', methods=['POST'])
def create_purchase_order():
    data = request.json
    supplier_id = data.get('supplier_id')
    supplier_name = data.get('supplier_name')
    items = data.get('items', [])
    discount = float(data.get('discount', 0))
    expected_date = data.get('expected_date')
    notes = data.get('notes', '')
    
    if not items:
        return jsonify({'success': False, 'message': 'لا يوجد منتجات'})
    
    if not supplier_id:
        return jsonify({'success': False, 'message': 'يرجى اختيار المورد'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # حساب الإجمالي
    subtotal = sum(item['quantity'] * item['cost_price'] for item in items)
    final_amount = subtotal - discount
    
    # إنشاء رقم أمر شراء فريد
    po_number = f"PO-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    order_date = datetime.now().strftime('%Y-%m-%d')
    
    # حفظ أمر الشراء
    cursor.execute('''
        INSERT INTO purchase_orders 
        (po_number, supplier_id, supplier_name, total_amount, discount, final_amount,
         status, order_date, expected_date, notes, created_by, created_by_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        po_number, supplier_id, supplier_name, subtotal, discount, final_amount,
        'pending', order_date, expected_date, notes,
        session.get('employee_id'), session.get('full_name'),
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    
    po_id = cursor.lastrowid
    
    # حفظ تفصيل المنتجات
    for item in items:
        cursor.execute('''
            INSERT INTO purchase_order_items 
            (po_id, product_id, product_name, quantity, cost_price, selling_price, subtotal)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            po_id,
            item.get('product_id'),
            item['product_name'],
            item['quantity'],
            item['cost_price'],
            item.get('selling_price'),
            item['quantity'] * item['cost_price']
        ))
    
    # تحديث حساب المورد (إضافة مبلغ مستحق)
    cursor.execute('''
        INSERT INTO supplier_accounts 
        (supplier_id, transaction_type, reference_id, reference_number, 
         debit, credit, balance, date, notes, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        supplier_id, 'purchase', po_id, po_number,
        final_amount, 0, final_amount,
        order_date, f'أمر شراء {po_number}',
        session.get('employee_id')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'تم إنشاء أمر الشراء بنجاح',
        'po_number': po_number
    })

# استلام أمر الشراء
@app.route('/api/purchase_orders/<int:po_id>/receive', methods=['POST'])
def receive_purchase_order(po_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # تحديث حالة أمر الشراء
    received_date = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        UPDATE purchase_orders 
        SET status = 'received', received_date = ?
        WHERE id = ?
    ''', (received_date, po_id))
    
    # الحصول على تفصيل المنتجات
    items = conn.execute('''
        SELECT * FROM purchase_order_items WHERE po_id = ?
    ''', (po_id,)).fetchall()
    
    # تحديث المخزون
    for item in items:
        # إضافة الكمية للمخزون
        cursor.execute('''
            UPDATE products 
            SET quantity = quantity + ?, cost_price = ?, price = ?
            WHERE id = ?
        ''', (item['quantity'], item['cost_price'], item['selling_price'], item['product_id']))
        
        # تسجيل حركة المخزون
        cursor.execute('''
            INSERT INTO stock_movements 
            (product_id, product_name, quantity, movement_type, reason, 
             reference_id, employee_id, employee_name, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item['product_id'], item['product_name'], item['quantity'],
            'add', 'استلام أمر شراء',
            po_id, session.get('employee_id'), session.get('full_name'),
            received_date
        ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم استلام الطلب بنجاح'})

# ========================================
# مدفوعات الموردين
# ========================================

@app.route('/supplier_payments')
def supplier_payments_page():
    if 'employee_id' not in session:
        return redirect(url_for('login'))
    return render_template('supplier_payments.html')

# عرض جميع مدفوعات الموردين
@app.route('/api/supplier_payments', methods=['GET'])
def get_supplier_payments():
    conn = get_db_connection()
    
    payments = conn.execute('''
        SELECT sp.*, s.name as supplier_name
        FROM supplier_payments sp
        LEFT JOIN suppliers s ON sp.supplier_id = s.id
        ORDER BY sp.id DESC
        LIMIT 50
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'payments': [
            {
                'id': p['id'],
                'payment_number': p['payment_number'],
                'supplier_id': p['supplier_id'],
                'supplier_name': p['supplier_name'],
                'amount': p['amount'],
                'payment_method': p['payment_method'],
                'payment_date': p['payment_date'],
                'notes': p['notes'],
                'created_by_name': p['created_by_name'],
                'created_at': p['created_at']
            }
            for p in payments
        ]
    })

# إضافة دفعة لمورد
@app.route('/api/supplier_payments', methods=['POST'])
def add_supplier_payment():
    data = request.json
    supplier_id = data.get('supplier_id')
    supplier_name = data.get('supplier_name')
    amount = float(data.get('amount'))
    payment_method = data.get('payment_method')
    notes = data.get('notes', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # إنشاء رقم دفعة فريد
    payment_number = f"PAY-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    payment_date = datetime.now().strftime('%Y-%m-%d')
    
    # حفظ الدفعة
    cursor.execute('''
        INSERT INTO supplier_payments 
        (payment_number, supplier_id, supplier_name, amount, payment_method,
         payment_date, notes, created_by, created_by_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        payment_number, supplier_id, supplier_name, amount, payment_method,
        payment_date, notes,
        session.get('employee_id'), session.get('full_name'),
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    
    # تحديث حساب المورد (خصم المبلغ المدفوع)
    cursor.execute('''
        INSERT INTO supplier_accounts 
        (supplier_id, transaction_type, reference_id, reference_number, 
         debit, credit, balance, date, notes, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        supplier_id, 'payment', cursor.lastrowid, payment_number,
        0, amount, -amount,
        payment_date, f'دفعة {payment_number}',
        session.get('employee_id')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'تم تسجيل الدفعة بنجاح',
        'payment_number': payment_number
    })

# ========================================
# حسابات الموردين
# ========================================

@app.route('/supplier_accounts')
def supplier_accounts_page():
    if 'employee_id' not in session:
        return redirect(url_for('login'))
    return render_template('supplier_accounts.html')

# كشف حساب مورد
@app.route('/api/supplier_accounts/<int:supplier_id>', methods=['GET'])
def get_supplier_account(supplier_id):
    conn = get_db_connection()
    
    # الحصول على معلومات المورد
    supplier = conn.execute('SELECT * FROM suppliers WHERE id = ?', (supplier_id,)).fetchone()
    
    # الحصول على كشف الحساب
    transactions = conn.execute('''
        SELECT * FROM supplier_accounts 
        WHERE supplier_id = ?
        ORDER BY id DESC
        LIMIT 100
    ''', (supplier_id,)).fetchall()
    
    # حساب الرصيد الحالي
    balance = conn.execute('''
        SELECT COALESCE(SUM(debit - credit), 0) as balance
        FROM supplier_accounts 
        WHERE supplier_id = ?
    ''', (supplier_id,)).fetchone()['balance']
    
    conn.close()
    
    return jsonify({
        'success': True,
        'supplier': {
            'id': supplier['id'],
            'name': supplier['name'],
            'phone': supplier['phone'],
            'address': supplier['address'],
            'balance': balance
        },
        'transactions': [
            {
                'id': t['id'],
                'transaction_type': t['transaction_type'],
                'reference_number': t['reference_number'],
                'debit': t['debit'],
                'credit': t['credit'],
                'balance': t['balance'],
                'date': t['date'],
                'notes': t['notes']
            }
            for t in transactions
        ]
    })
# ========================================
# لوحة التحكم (Dashboard)
# ========================================

@app.route('/dashboard')
def dashboard():
    if 'employee_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/api/dashboard_data')
def dashboard_data():
    conn = get_db_connection()
    
    try:
        # مبيعات اليوم
        today = datetime.now().strftime('%Y-%m-%d')
        today_sales = conn.execute('''
            SELECT COUNT(*) as count, COALESCE(SUM(final_total), 0) as total
            FROM invoices 
            WHERE date(date) = ? AND status = 'completed'
        ''', (today,)).fetchone()
        
        # مبيعات الأمس
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_sales = conn.execute('''
            SELECT COUNT(*) as count, COALESCE(SUM(final_total), 0) as total
            FROM invoices 
            WHERE date(date) = ? AND status = 'completed'
        ''', (yesterday,)).fetchone()
        
        # المنتجات منخفضة المخزون
        low_stock = conn.execute('''
            SELECT COUNT(*) as count 
            FROM products 
            WHERE quantity <= min_stock AND quantity > 0
        ''').fetchone()
        
        # المنتجات التي نفذت
        out_of_stock = conn.execute('''
            SELECT COUNT(*) as count 
            FROM products 
            WHERE quantity = 0
        ''').fetchone()
        
        # إجمالي المنتجات
        total_products = conn.execute('SELECT COUNT(*) as count FROM products').fetchone()
        
        # إجمالي الموردين
        total_suppliers = conn.execute('SELECT COUNT(*) as count FROM suppliers').fetchone()
        
        # إجمالي العملاء (باستخدام try/except للتعامل مع الجدول إذا لم يكن موجوداً)
        customers_count = 0
        try:
            total_customers = conn.execute('SELECT COUNT(*) as count FROM customers').fetchone()
            customers_count = total_customers['count']
        except sqlite3.OperationalError:
            # إذا لم يكن جدول العملاء موجوداً
            customers_count = 0
        
        # إجمالي الإيرادات (كل الوقت)
        total_revenue = conn.execute('''
            SELECT COALESCE(SUM(final_total), 0) as total 
            FROM invoices 
            WHERE status = 'completed'
        ''').fetchone()
        
        # آخر 5 فواتير
        recent_invoices = conn.execute('''
            SELECT invoice_number, total, final_total, payment_method, cashier_name, date
            FROM invoices
            WHERE status = 'completed'
            ORDER BY date DESC
            LIMIT 5
        ''').fetchall()
        
        # آخر 5 حركات مخزون
        recent_movements = conn.execute('''
            SELECT sm.product_name, sm.quantity, sm.movement_type, sm.reason, sm.date, sm.employee_name
            FROM stock_movements sm
            ORDER BY sm.date DESC
            LIMIT 5
        ''').fetchall()
        
        # أفضل 5 منتجات مبيعاً اليوم
        top_products = conn.execute('''
            SELECT p.name, SUM(ii.quantity) as total_quantity, SUM(ii.subtotal) as total_sales
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            JOIN products p ON ii.product_id = p.id
            WHERE date(i.date) = ? AND i.status = 'completed'
            GROUP BY p.id, p.name
            ORDER BY total_quantity DESC
            LIMIT 5
        ''', (today,)).fetchall()
        
    except Exception as e:
        print(f"Error in dashboard_data: {str(e)}")  # طباعة الخطأ للتشخيص
        conn.close()
        return jsonify({
            'error': str(e),
            'today_sales_count': 0,
            'today_sales_total': 0,
            'yesterday_sales_total': 0,
            'growth_percentage': 0,
            'low_stock_count': 0,
            'out_of_stock_count': 0,
            'total_products': 0,
            'total_suppliers': 0,
            'total_customers': 0,
            'total_revenue': 0,
            'recent_invoices': [],
            'recent_movements': [],
            'top_products': []
        })
    
    finally:
        conn.close()
    
    # حساب نسبة النمو مقارنة بالأمس
    today_total = today_sales['total'] or 0
    yesterday_total = yesterday_sales['total'] or 0
    growth_percentage = 0
    if yesterday_total > 0:
        growth_percentage = ((today_total - yesterday_total) / yesterday_total) * 100
    
    return jsonify({
        'today_sales_count': today_sales['count'] or 0,
        'today_sales_total': today_total,
        'yesterday_sales_total': yesterday_total,
        'growth_percentage': round(growth_percentage, 2),
        'low_stock_count': low_stock['count'] or 0,
        'out_of_stock_count': out_of_stock['count'] or 0,
        'total_products': total_products['count'] or 0,
        'total_suppliers': total_suppliers['count'] or 0,
        'total_customers': customers_count,
        'total_revenue': total_revenue['total'] or 0,
        'recent_invoices': [
            {
                'invoice_number': inv['invoice_number'],
                'total': inv['total'],
                'final_total': inv['final_total'],
                'payment_method': inv['payment_method'],
                'cashier_name': inv['cashier_name'],
                'date': inv['date']
            }
            for inv in recent_invoices
        ],
        'recent_movements': [
            {
                'product_name': mov['product_name'],
                'quantity': mov['quantity'],
                'movement_type': mov['movement_type'],
                'reason': mov['reason'],
                'date': mov['date'],
                'employee_name': mov['employee_name']
            }
            for mov in recent_movements
        ],
        'top_products': [
            {
                'name': prod['name'],
                'quantity': prod['total_quantity'],
                'sales': prod['total_sales']
            }
            for prod in top_products
        ]
    })
if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=5000, debug=True)

