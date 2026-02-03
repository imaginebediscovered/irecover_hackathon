"""
Seed critical bookings with imminent SLA breaches for testing
Adds bookings with shipping dates very close to current time to trigger SLA alerts
"""
import asyncio
import random
import string
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def seed_critical_bookings():
    """Add critical bookings with imminent SLA breaches"""
    database_url = "sqlite+aiosqlite:///./irecover.db"
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.begin() as conn:
        print("🚨 Adding critical bookings with SLA breach risk...")
        
        random.seed()  # Use current time for random AWBs
        
        prefixes = ["176", "020", "618"]
        origins = ["DEL", "BOM", "BLR", "HYD", "MAA"]
        destinations = ["JFK", "LAX", "SFO", "ORD", "DFW", "MIA", "SEA", "BOS", "ATL", "DEN", "PHX", "LAS"]
        agent_codes = ["DHL", "FedEx", "UPS", "Aramex"]
        currency = "USD"
        
        now = datetime.now()
        
        # Critical bookings - IMMINENT SLA breach (<1 hour)
        critical_bookings = [
            (25, "JFK", 8, 450, "DHL"),    # 25 min to breach
            (35, "LAX", 6, 380, "FedEx"),  # 35 min to breach
            (45, "SFO", 10, 520, "UPS"),   # 45 min to breach
            (52, "ORD", 7, 410, "DHL"),    # 52 min to breach
        ]
        
        # High risk bookings - <2 hours
        high_risk_bookings = [
            (75, "DFW", 5, 320, "FedEx"),
            (85, "MIA", 9, 480, "UPS"),
            (95, "SEA", 6, 350, "DHL"),
            (105, "BOS", 8, 440, "Aramex"),
            (115, "ATL", 7, 390, "FedEx"),
        ]
        
        # Medium risk bookings - 2-4 hours
        medium_risk_bookings = [
            (145, "DEN", 5, 310, "DHL"),
            (165, "PHX", 8, 460, "UPS"),
            (185, "LAS", 6, 370, "FedEx"),
            (205, "JFK", 9, 490, "DHL"),
            (225, "LAX", 7, 420, "Aramex"),
        ]
        
        all_bookings = critical_bookings + high_risk_bookings + medium_risk_bookings
        bookings_inserted = 0
        
        for minutes, dest, pieces, weight, agent in all_bookings:
            awb_prefix = random.choice(prefixes)
            awb_number = ''.join(random.choices(string.digits, k=8))
            ubr_number = f"CRITICAL_{now.strftime('%H%M%S')}_{random.randint(1000, 9999)}"
            origin = random.choice(origins)
            ship_datetime = now + timedelta(minutes=minutes)
            ship_date = ship_datetime.date()
            
            chargeable_weight = float(weight)
            total_revenue = round(chargeable_weight * random.uniform(3, 8), 2)
            booking_status = "C"  # Confirmed
            
            try:
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
                    "agent_code": agent
                })
                bookings_inserted += 1
                
                # Log the critical ones
                if minutes < 60:
                    print(f"   🔴 CRITICAL: {awb_prefix}-{awb_number} | {origin}→{dest} | {minutes}min to breach | {agent}")
                elif minutes < 120:
                    print(f"   🟠 HIGH: {awb_prefix}-{awb_number} | {origin}→{dest} | {minutes}min to breach | {agent}")
                else:
                    print(f"   🟡 MEDIUM: {awb_prefix}-{awb_number} | {origin}→{dest} | {minutes}min to breach | {agent}")
                    
            except Exception as e:
                print(f"   ⚠️  Error inserting booking: {e}")
        
        print(f"\n✅ Inserted {bookings_inserted} critical bookings")
        
        # Show summary
        result = await conn.execute(text('''
            SELECT COUNT(*) FROM booking_summary
        '''))
        total = result.scalar()
        print(f"📊 Total bookings in database: {total}")
    
    await engine.dispose()
    print("\n🎉 Critical bookings seeded! Check Command Center for SLA alerts.")

if __name__ == "__main__":
    asyncio.run(seed_critical_bookings())
