import sqlite3
import os

db_path = '/backend/irecover.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check booking_summary schema
    cursor.execute("PRAGMA table_info(booking_summary)")
    columns = cursor.fetchall()
    print('✅ booking_summary columns:')
    for col in columns:
        print(f'  {col[1]}: {col[2]}')
    
    # Check row counts
    cursor.execute('SELECT COUNT(*) FROM booking_summary')
    bs_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM news')
    news_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM weather_disruptions')
    weather_count = cursor.fetchone()[0]
    
    print(f'\n✅ Data counts:')
    print(f'  booking_summary: {bs_count} rows')
    print(f'  news: {news_count} rows')
    print(f'  weather_disruptions: {weather_count} rows')
    
    # Check for cargo_type values
    cursor.execute('SELECT DISTINCT cargo_type FROM booking_summary WHERE cargo_type IS NOT NULL')
    cargo_types = cursor.fetchall()
    print(f'\n✅ cargo_type values found:')
    if cargo_types:
        for ct in cargo_types:
            print(f'  {ct[0]}')
    else:
        print('  (none)')
    
    # Sample booking with cargo_type
    cursor.execute('SELECT awb_prefix, awb_number, cargo_type FROM booking_summary WHERE cargo_type IS NOT NULL LIMIT 3')
    samples = cursor.fetchall()
    print(f'\n✅ Sample bookings with cargo_type:')
    for s in samples:
        print(f'  AWB {s[0]}-{s[1]}: {s[2]}')
    
    conn.close()
else:
    print(f'❌ Database not found at {db_path}')
