import sqlite3

DATABASE = "product_data.db"

conn = sqlite3.connect(DATABASE)
cur = conn.cursor()

# URL 테이블
cur.execute("""
CREATE TABLE IF NOT EXISTS url (
    url_id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    status TEXT CHECK(status IN ('active', 'inactive')) NOT NULL DEFAULT 'active',
    added_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
""")

# 상품 테이블
cur.execute("""
CREATE TABLE IF NOT EXISTS product (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    image_url TEXT,
    model_name TEXT,
    options TEXT,
    FOREIGN KEY (url_id) REFERENCES url (url_id) ON DELETE CASCADE
);
""")

# 가격 기록 테이블
cur.execute("""
CREATE TABLE IF NOT EXISTS price_history (
    price_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    date_recorded DATE NOT NULL,
    release_price REAL,
    employee_price REAL,
    FOREIGN KEY (product_id) REFERENCES product (product_id) ON DELETE CASCADE
);
""")

# 크롤링 로그 테이블
cur.execute("""
CREATE TABLE IF NOT EXISTS crawl_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_id INTEGER NOT NULL,
    attempt_time DATETIME NOT NULL,
    status TEXT CHECK(status IN ('Success', 'Failed')) NOT NULL,
    error_message TEXT,
    FOREIGN KEY (url_id) REFERENCES url (url_id) ON DELETE CASCADE
);
""")

# 사용자 요청 테이블
cur.execute("""
CREATE TABLE IF NOT EXISTS user_request (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_id INTEGER NOT NULL,
    status TEXT CHECK(status IN ('Pending', 'Complete')) NOT NULL DEFAULT 'Pending',
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (url_id) REFERENCES url (url_id) ON DELETE CASCADE
);
""")

conn.commit()
conn.close()
