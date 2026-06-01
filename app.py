#!/usr/bin/env python3
"""🍳 杜堡堡小厨房 - Kitchen Recipe Manager v2"""

import os, sqlite3, uuid, json, urllib.request, urllib.parse, threading
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template, send_from_directory, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['DATABASE'] = os.path.join(BASE, 'recipes.db')
ALLOWED = {'png','jpg','jpeg','gif','webp'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed(fn): return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED
def get_db():
    d = sqlite3.connect(app.config['DATABASE'])
    d.row_factory = sqlite3.Row
    d.execute("PRAGMA foreign_keys = ON")
    return d

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, icon TEXT DEFAULT '🍽️',
            sort_order INTEGER DEFAULT 0, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS recipes (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, category_id TEXT DEFAULT '',
            description TEXT DEFAULT '', ingredients TEXT DEFAULT '[]',
            steps TEXT DEFAULT '[]', difficulty TEXT DEFAULT '简单',
            cook_time TEXT DEFAULT '', servings TEXT DEFAULT '',
            image TEXT DEFAULT '', tags TEXT DEFAULT '[]',
            monthly_sales INTEGER DEFAULT 0,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY, order_date TEXT NOT NULL,
            meal_type TEXT NOT NULL DEFAULT 'lunch',
            note TEXT DEFAULT '', status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id TEXT PRIMARY KEY, order_id TEXT NOT NULL,
            recipe_id TEXT NOT NULL, recipe_title TEXT DEFAULT '',
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS fridge_items (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            category TEXT DEFAULT '其他', quantity TEXT DEFAULT '',
            expiry_date TEXT DEFAULT '', note TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS discover_items (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, content TEXT DEFAULT '',
            type TEXT DEFAULT 'tip', image TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
    ''')
    # Default categories
    defaults = [
        ('cat_meat','顿顿有肉','🥩',1), ('cat_mix','荤素搭配','🥘',2),
        ('cat_veg','时蔬','🥬',3), ('cat_sweet','糖水','🍵',4),
        ('cat_other','其他','🥡',5),
    ]
    for cid,name,icon,order in defaults:
        db.execute('INSERT OR IGNORE INTO categories(id,name,icon,sort_order,created_at) VALUES(?,?,?,?,?)',
                   (cid,name,icon,order,datetime.now().isoformat()))
    db.commit(); db.close()

init_db()

# ── AI Image Generation ──
def generate_recipe_image(title, ingredients=None, rid=None):
    """Generate a recipe image using Pollinations.ai (free, no API key)"""
    ings = ', '.join(ingredients[:5]) if ingredients else ''
    prompt = f"A beautiful professional food photography of Chinese dish '{title}'"
    if ings:
        prompt += f" made with {ings}"
    prompt += ", plated on a elegant ceramic plate, warm lighting, top-down view, restaurant quality, appetizing, detailed texture, food magazine style, 4k"
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=512&nologo=true&seed={uuid.uuid4().hex[:6]}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            if len(data) < 1000:
                return None
            filename = f"{rid or 'ai_'+uuid.uuid4().hex[:8]}_{uuid.uuid4().hex[:6]}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(data)
            return filename
    except Exception as e:
        print(f"[AI Image] Error: {e}")
        return None

@app.route('/api/generate-image', methods=['POST'])
def api_generate_image():
    """Endpoint for on-demand AI image generation"""
    d = request.get_json()
    title = d.get('title','').strip()
    if not title:
        return jsonify({'error':'需要菜名'}), 400
    ingredients = d.get('ingredients', [])
    rid = d.get('recipe_id', 'ai_'+uuid.uuid4().hex[:8])
    filename = generate_recipe_image(title, ingredients, rid)
    if filename:
        return jsonify({'filename': filename, 'url': f'/uploads/{filename}'})
    return jsonify({'error':'图片生成失败，请稍后重试'}), 500

# ── Frontend ──
@app.route('/')
def index(): return render_template('index.html')
@app.route('/uploads/<fn>')
def uploaded(fn): return send_from_directory(app.config['UPLOAD_FOLDER'], fn)

# ══════════ CATEGORIES ══════════
@app.route('/api/categories')
def get_categories():
    db = get_db()
    cats = [dict(r) for r in db.execute('SELECT * FROM categories ORDER BY sort_order').fetchall()]
    for c in cats:
        c['recipe_count'] = db.execute('SELECT COUNT(*) FROM recipes WHERE category_id=?',(c['id'],)).fetchone()[0]
    db.close()
    return jsonify(cats)

@app.route('/api/categories', methods=['POST'])
def create_category():
    d = request.get_json(); name = d.get('name','').strip()
    if not name: return jsonify({'error':'名称不能为空'}),400
    cid = 'cat_'+uuid.uuid4().hex[:8]
    db = get_db()
    mx = db.execute('SELECT MAX(sort_order) FROM categories').fetchone()[0] or 0
    db.execute('INSERT INTO categories(id,name,icon,sort_order,created_at) VALUES(?,?,?,?,?)',
               (cid,name,d.get('icon','🍽️'),mx+1,datetime.now().isoformat()))
    db.commit(); db.close()
    return jsonify({'id':cid,'message':'创建成功'}),201

@app.route('/api/categories/<cid>', methods=['PUT'])
def update_category(cid):
    d = request.get_json(); db = get_db()
    db.execute('UPDATE categories SET name=?,icon=? WHERE id=?',(d.get('name',''),d.get('icon','🍽️'),cid))
    db.commit(); db.close()
    return jsonify({'message':'更新成功'})

@app.route('/api/categories/<cid>', methods=['DELETE'])
def delete_category(cid):
    db = get_db()
    db.execute("UPDATE recipes SET category_id='' WHERE category_id=?",(cid,))
    db.execute('DELETE FROM categories WHERE id=?',(cid,))
    db.commit(); db.close()
    return jsonify({'message':'删除成功'})

@app.route('/api/categories/reorder', methods=['POST'])
def reorder_categories():
    data = request.get_json()
    ids = data.get('order',[])
    db = get_db()
    for i,cid in enumerate(ids):
        db.execute('UPDATE categories SET sort_order=? WHERE id=?',(i,cid))
    db.commit(); db.close()
    return jsonify({'message':'排序已更新'})

# ══════════ RECIPES ══════════
@app.route('/api/sub_categories')
def get_sub_categories():
    db = get_db(); cat = request.args.get('category','')
    sql = 'SELECT DISTINCT sub_category FROM recipes WHERE sub_category!=""'; params = []
    if cat and cat != 'all': sql += ' AND category_id=?'; params.append(cat)
    sql += ' ORDER BY sub_category'
    rows = [r['sub_category'] for r in db.execute(sql,params).fetchall()]
    db.close()
    return jsonify(rows)

@app.route('/api/recipes')
def get_recipes():
    db = get_db(); cat = request.args.get('category',''); q = request.args.get('search',''); sub = request.args.get('sub','')
    sql = 'SELECT * FROM recipes WHERE 1=1'; params = []
    if cat and cat != 'all': sql += ' AND category_id=?'; params.append(cat)
    if sub: sql += ' AND sub_category=?'; params.append(sub)
    if q: sql += ' AND (title LIKE ? OR description LIKE ? OR ingredients LIKE ?)'; s=f'%{q}%'; params.extend([s,s,s])
    sql += ' ORDER BY updated_at DESC'
    rows = db.execute(sql,params).fetchall()
    recipes = []
    for r in rows:
        d = dict(r)
        for k in ('ingredients','steps','tags'): d[k] = json.loads(d[k]) if d[k] else []
        recipes.append(d)
    db.close()
    return jsonify(recipes)

@app.route('/api/recipes', methods=['POST'])
def create_recipe():
    db = get_db(); now = datetime.now().isoformat(); rid = 'r_'+uuid.uuid4().hex[:8]
    img = ''
    # Check for pre-generated AI image
    ai_img = request.form.get('ai_image','')
    if ai_img:
        ai_path = os.path.join(app.config['UPLOAD_FOLDER'], ai_img)
        if os.path.exists(ai_path):
            img = ai_img
    if 'image' in request.files:
        f = request.files['image']
        if f.filename and allowed(f.filename):
            ext = f.filename.rsplit('.',1)[1].lower(); fn = f"{rid}_{uuid.uuid4().hex[:6]}.{ext}"
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],fn)); img = fn
    title = request.form.get('title','').strip()
    if not title: return jsonify({'error':'菜名不能为空'}),400
    auto_gen = request.form.get('auto_generate','') == 'true'
    ingredients_str = request.form.get('ingredients','[]')
    db.execute('''INSERT INTO recipes(id,title,category_id,sub_category,description,ingredients,steps,
        difficulty,cook_time,servings,image,tags,monthly_sales,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (rid,title,request.form.get('category_id',''),request.form.get('sub_category',''),request.form.get('description',''),
         ingredients_str,request.form.get('steps','[]'),
         request.form.get('difficulty','简单'),request.form.get('cook_time',''),
         request.form.get('servings',''),img,request.form.get('tags','[]'),0,now,now))
    db.commit(); db.close()
    # Auto-generate image in background if no image uploaded
    if not img and auto_gen:
        try:
            ings = json.loads(ingredients_str) if ingredients_str else []
        except: ings = []
        def _gen():
            filename = generate_recipe_image(title, ings, rid)
            if filename:
                c = get_db()
                c.execute('UPDATE recipes SET image=? WHERE id=?', (filename, rid))
                c.commit(); c.close()
        threading.Thread(target=_gen, daemon=True).start()
    return jsonify({'id':rid,'message':'创建成功','auto_generating': not img and auto_gen}),201

@app.route('/api/recipes/<rid>', methods=['GET'])
def get_recipe(rid):
    db = get_db(); r = db.execute('SELECT * FROM recipes WHERE id=?',(rid,)).fetchone(); db.close()
    if not r: return jsonify({'error':'不存在'}),404
    d = dict(r)
    for k in ('ingredients','steps','tags'): d[k] = json.loads(d[k]) if d[k] else []
    return jsonify(d)

@app.route('/api/recipes/<rid>', methods=['PUT'])
def update_recipe(rid):
    db = get_db(); ex = db.execute('SELECT * FROM recipes WHERE id=?',(rid,)).fetchone()
    if not ex: db.close(); return jsonify({'error':'不存在'}),404
    now = datetime.now().isoformat(); img = ex['image']
    # Check for pre-generated AI image
    ai_img = request.form.get('ai_image','')
    if ai_img:
        ai_path = os.path.join(app.config['UPLOAD_FOLDER'], ai_img)
        if os.path.exists(ai_path):
            if img:
                p = os.path.join(app.config['UPLOAD_FOLDER'],img)
                if os.path.exists(p): os.remove(p)
            img = ai_img
    if 'image' in request.files:
        f = request.files['image']
        if f.filename and allowed(f.filename):
            if img:
                p = os.path.join(app.config['UPLOAD_FOLDER'],img)
                if os.path.exists(p): os.remove(p)
            ext = f.filename.rsplit('.',1)[1].lower(); fn = f"{rid}_{uuid.uuid4().hex[:6]}.{ext}"
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],fn)); img = fn
    if request.form.get('remove_image')=='true':
        if img:
            p = os.path.join(app.config['UPLOAD_FOLDER'],img)
            if os.path.exists(p): os.remove(p)
        img = ''
    title = request.form.get('title','').strip()
    if not title: return jsonify({'error':'菜名不能为空'}),400
    db.execute('''UPDATE recipes SET title=?,category_id=?,sub_category=?,description=?,ingredients=?,steps=?,
        difficulty=?,cook_time=?,servings=?,image=?,tags=?,updated_at=? WHERE id=?''',
        (title,request.form.get('category_id',ex['category_id']),
         request.form.get('sub_category',ex['sub_category'] if ex['sub_category'] else ''),
         request.form.get('description',ex['description']),
         request.form.get('ingredients',ex['ingredients']),
         request.form.get('steps',ex['steps']),
         request.form.get('difficulty',ex['difficulty']),
         request.form.get('cook_time',ex['cook_time']),
         request.form.get('servings',ex['servings']),
         img,request.form.get('tags',ex['tags']),now,rid))
    db.commit(); db.close()
    # Auto-generate image if requested and no image
    auto_gen = request.form.get('auto_generate','') == 'true'
    if not img and auto_gen:
        ingredients_str = request.form.get('ingredients', ex['ingredients'])
        try: ings = json.loads(ingredients_str) if ingredients_str else []
        except: ings = []
        def _gen():
            filename = generate_recipe_image(title, ings, rid)
            if filename:
                c = get_db()
                c.execute('UPDATE recipes SET image=? WHERE id=?', (filename, rid))
                c.commit(); c.close()
        threading.Thread(target=_gen, daemon=True).start()
    return jsonify({'message':'更新成功','auto_generating': not img and auto_gen})

@app.route('/api/recipes/<rid>', methods=['DELETE'])
def delete_recipe(rid):
    db = get_db(); ex = db.execute('SELECT * FROM recipes WHERE id=?',(rid,)).fetchone()
    if not ex: db.close(); return jsonify({'error':'不存在'}),404
    if ex['image']:
        p = os.path.join(app.config['UPLOAD_FOLDER'],ex['image'])
        if os.path.exists(p): os.remove(p)
    db.execute('DELETE FROM order_items WHERE recipe_id=?',(rid,))
    db.execute('DELETE FROM recipes WHERE id=?',(rid,))
    db.commit(); db.close()
    return jsonify({'message':'删除成功'})

@app.route('/api/random')
def random_recipe():
    cat = request.args.get('category',''); db = get_db()
    sql = 'SELECT * FROM recipes'; params = []
    if cat and cat != 'all': sql += ' WHERE category_id=?'; params.append(cat)
    r = db.execute(sql+' ORDER BY RANDOM() LIMIT 1',params).fetchone(); db.close()
    if not r: return jsonify({'error':'还没有菜谱哦~'}),404
    d = dict(r)
    for k in ('ingredients','steps','tags'): d[k] = json.loads(d[k]) if d[k] else []
    return jsonify(d)

# ══════════ ORDERS ══════════
MEAL_TYPES = {"breakfast":"🌅 早餐","lunch":"☀️ 午餐","snack":"🍵 下午茶","dinner":"🌙 晚餐","midnight":"🌙 夜宵"}

@app.route('/api/orders')
def get_orders():
    db = get_db()
    query = 'SELECT * FROM orders WHERE 1=1'; params = []
    date_f = request.args.get('date','')
    if date_f: query += ' AND order_date=?'; params.append(date_f)
    meal = request.args.get('meal_type','')
    if meal and meal != 'all': query += ' AND meal_type=?'; params.append(meal)
    query += ' ORDER BY order_date DESC, created_at DESC'
    rows = db.execute(query,params).fetchall()
    orders = []
    for r in rows:
        d = dict(r)
        d['items'] = [dict(i) for i in db.execute('SELECT * FROM order_items WHERE order_id=?',(d['id'],)).fetchall()]
        orders.append(d)
    db.close()
    return jsonify(orders)

@app.route('/api/orders', methods=['POST'])
def create_order():
    d = request.get_json(); db = get_db()
    oid = 'o_'+uuid.uuid4().hex[:8]; now = datetime.now().isoformat()
    order_date = d.get('order_date', date.today().isoformat())
    meal_type = d.get('meal_type','lunch')
    items = d.get('items',[])  # [{recipe_id, recipe_title}]
    db.execute('INSERT INTO orders(id,order_date,meal_type,note,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
               (oid,order_date,meal_type,d.get('note',''),'active',now,now))
    for item in items:
        iid = 'oi_'+uuid.uuid4().hex[:8]
        db.execute('INSERT INTO order_items(id,order_id,recipe_id,recipe_title) VALUES(?,?,?,?)',
                   (iid,oid,item.get('recipe_id',''),item.get('recipe_title','')))
        # Increment monthly_sales
        db.execute('UPDATE recipes SET monthly_sales = monthly_sales + 1 WHERE id=?',(item.get('recipe_id',''),))
    db.commit(); db.close()
    return jsonify({'id':oid,'message':'下单成功 🎉'}),201

@app.route('/api/orders/<oid>', methods=['DELETE'])
def delete_order(oid):
    db = get_db()
    db.execute('DELETE FROM order_items WHERE order_id=?',(oid,))
    db.execute('DELETE FROM orders WHERE id=?',(oid,))
    db.commit(); db.close()
    return jsonify({'message':'已取消'})

# ══════════ FRIDGE ══════════
@app.route('/api/fridge')
def get_fridge():
    db = get_db()
    rows = db.execute('SELECT * FROM fridge_items ORDER BY expiry_date ASC, created_at DESC').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/fridge', methods=['POST'])
def add_fridge():
    d = request.get_json(); name = d.get('name','').strip()
    if not name: return jsonify({'error':'名称不能为空'}),400
    fid = 'f_'+uuid.uuid4().hex[:8]; now = datetime.now().isoformat()
    db = get_db()
    db.execute('INSERT INTO fridge_items(id,name,category,quantity,expiry_date,note,created_at) VALUES(?,?,?,?,?,?,?)',
               (fid,name,d.get('category','其他'),d.get('quantity',''),d.get('expiry_date',''),d.get('note',''),now))
    db.commit(); db.close()
    return jsonify({'id':fid,'message':'已添加'}),201

@app.route('/api/fridge/<fid>', methods=['PUT'])
def update_fridge(fid):
    d = request.get_json(); db = get_db()
    db.execute('UPDATE fridge_items SET name=?,category=?,quantity=?,expiry_date=?,note=? WHERE id=?',
               (d.get('name',''),d.get('category','其他'),d.get('quantity',''),d.get('expiry_date',''),d.get('note',''),fid))
    db.commit(); db.close()
    return jsonify({'message':'已更新'})

@app.route('/api/fridge/<fid>', methods=['DELETE'])
def delete_fridge(fid):
    db = get_db(); db.execute('DELETE FROM fridge_items WHERE id=?',(fid,)); db.commit(); db.close()
    return jsonify({'message':'已删除'})

# ══════════ DISCOVER ══════════
@app.route('/api/discover')
def get_discover():
    db = get_db()
    # Return stats + featured recipes
    total = db.execute('SELECT COUNT(*) FROM recipes').fetchone()[0]
    cats = db.execute('SELECT COUNT(*) FROM categories').fetchone()[0]
    orders_total = db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    fridge_total = db.execute('SELECT COUNT(*) FROM fridge_items').fetchone()[0]
    top_recipes = [dict(r) for r in db.execute('SELECT * FROM recipes ORDER BY monthly_sales DESC LIMIT 5').fetchall()]
    recent = [dict(r) for r in db.execute('SELECT * FROM recipes ORDER BY created_at DESC LIMIT 5').fetchall()]
    db.close()
    return jsonify({
        'stats':{'total_recipes':total,'total_categories':cats,'total_orders':orders_total,'total_fridge':fridge_total},
        'top_recipes':top_recipes,'recent_recipes':recent
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8083, debug=True)
