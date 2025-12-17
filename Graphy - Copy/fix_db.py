import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    password TEXT NOT NULL
);
""")

# Create user_access table
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    devices BOOLEAN DEFAULT FALSE,
    chatbox BOOLEAN DEFAULT FALSE,
    projects INTEGER DEFAULT 0,
    settings BOOLEAN DEFAULT FALSE,
    programming BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (username) REFERENCES users (username)
);
""")

# Insert default admin user
cursor.execute("""
INSERT OR IGNORE INTO users (username, name, email, is_admin, password)
VALUES ('admin', 'Alexis Elias', 'admin@example.com', 1, '$2b$12$8o0cZK4lQY5ZtGpEtjAOk.9l0A3v47aH3QdQn7R0jzF6b8yEMhQ4i') 
""")

# Insert default access for admin
cursor.execute("""
INSERT OR IGNORE INTO user_access (username, devices, chatbox, projects, settings, programming)
VALUES ('admin', 1, 1, 1, 1, 1)
""")

conn.commit()
conn.close()

print("✅ Fresh users.db created successfully!")
