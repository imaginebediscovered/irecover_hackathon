"""
Reseed booking data with consistent fixed seed
Run this to get the same AWB numbers every time
"""
import asyncio
import random
import string
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def reseed_bookings():
    """Reseed booking_summary with consistent data"""
    database_url = "sqlite+aiosqlite:///./irecover.db"
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.begin() as conn:
        # Clear existing bookings
        await conn.execute(text('DELETE FROM booking_summary'))
        print("🗑️  Cleared existing booking data")
        
        # Set fixed seed for consistent AWB numbers
        random.seed(20260201)
        
        prefixes = ["123", "456", "789", "321", "654"]
        origins = ["JFK", "LAX", "ORD", "DFW", "ATL"]
        destinations = ["HKG", "SIN", "FRA", "LHR", "NRT"]
        agent_codes = ["AGT001", "AGT002", "AGT003"]
        currency = "USD"
        
        bookings_inserted = 0
        for i in range(1, 29):  # Feb 2026 days 1-28
            ship_date = date(2026, 2, i)
            for j in range(5):  # 5 bookings per day
                awb_prefix = random.choice(prefixes)
                awb_number = ''.join(random.choices(string.digits, k=8))
                ubr_number = f"UBR{ship_date.strftime('%d%m')}{j}{i}"
                origin = random.choice(origins)
                dest = random.choice([d for d in destinations if d != origin])
                pieces = random.randint(1, 10)
                chargeable_weight = round(random.uniform(50, 500), 2)
                total_revenue = round(chargeable_weight * random.uniform(2, 10), 2)
                booking_status = random.choice(["C", "Q"])
                agent_code = random.choice(agent_codes)
                
                await conn.execute(text('''
                    INSERT INTO booking_summary (
                        awb_prefix, awb_number, ubr_number, origin, destination, 
                        shipping_date, pieces, chargeable_weight, total_revenue, 
                        currency, booking_status, agent_code
                    ) VALUES (
                        :awb_prefix, :awb_number, :ubr_number, :origin, :destination, 
                        :shipping_date, :pieces, :chargeable_weight, :total_revenue, 
                        :currency, :booking_status, :agent_code
                    )
                '''), {
                    "awb_prefix": awb_prefix,
                    "awb_number": awb_number,
                    "ubr_number": ubr_number,
                    "origin": origin,
                    "destination": dest,
                    "shipping_date": ship_date,
                    "pieces": pieces,
                    "chargeable_weight": chargeable_weight,
                    "total_revenue": total_revenue,
                    "currency": currency,
                    "booking_status": booking_status,
                    "agent_code": agent_code
                })
                bookings_inserted += 1
        
        print(f"✅ Inserted {bookings_inserted} consistent booking records")
        
        # Show first 5 for verification
        result = await conn.execute(text('''
            SELECT awb_prefix, awb_number, ubr_number, origin, destination, shipping_date 
            FROM booking_summary 
            ORDER BY shipping_date 
            LIMIT 5
        '''))
        rows = result.fetchall()
        print("\n📦 First 5 bookings:")
        for row in rows:
            print(f"   AWB {row[0]}-{row[1]} | UBR {row[2]} | {row[3]}→{row[4]} | {row[5]}")
    
    await engine.dispose()
    print("\n🎉 Reseeding complete! Data will be consistent across restarts now.")

if __name__ == "__main__":
    asyncio.run(reseed_bookings())
