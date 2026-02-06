import sqlite3
import pandas as pd
import os

db_path = "newsletter.db"

if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
else:
    conn = sqlite3.connect(db_path)
    
    # Get all tables
    tables_df = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)
    print("Tables in database:")
    print(tables_df)
    print("\n" + "="*50 + "\n")
    
    for table in tables_df['name']:
        print(f"Table: {table}")
        # Get table schema
        schema = pd.read_sql_query(f"PRAGMA table_info({table});", conn)
        print("Schema:")
        print(schema[['name', 'type']])
        
        # Get first 10 rows
        data = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 10;", conn)
        print("\nSample Data (First 10 rows):")
        if data.empty:
            print("Table is empty.")
        else:
            print(data.to_string(index=False))
        print("\n" + "-"*50 + "\n")
    
    conn.close()
