import sqlite3

def create_tables():
    # 데이터베이스 연결 (파일이 없으면 생성됨)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # product 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product (
            product_id VARCHAR(255) PRIMARY KEY,
            url VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            model VARCHAR(255),
            options TEXT,
            image_url VARCHAR(255)
        );
    ''')

    # price_history 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id VARCHAR(255) NOT NULL,
            date DATE NOT NULL,
            original_price DECIMAL,
            employee_price DECIMAL,
            FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE CASCADE
        );
    ''')

    # user_requests 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            url VARCHAR(255) NOT NULL,
            requested_at DATETIME NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            total_hits INTEGER DEFAULT 0,
            hits INTEGER DEFAULT 0
        );
    ''')

    # product_hits 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_hits (
            product_id VARCHAR(255) NOT NULL,
            date DATE NOT NULL,
            daily_hits INTEGER DEFAULT 0,
            total_hits INTEGER,
            PRIMARY KEY (product_id, date),
            FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE CASCADE
        );
    ''')

    # 변경사항 커밋 및 연결 종료
    conn.commit()
    conn.close()
    print("Database and tables created successfully.")

if __name__ == '__main__':
    create_tables()
