"""
Database initialization script for iRecover
Creates tables and seeds sample data for development
"""
import asyncio
import random
import string
from datetime import datetime, timedelta, date
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.config import settings
from app.db.database import Base
from app.models.flight import Flight
from app.models.awb import AWB, AWBBooking, Priority, CommodityType
from app.models.disruption import Disruption, DisruptionType, DisruptionSeverity, DisruptionStatus
from app.models.approval import Approval
from app.models.news import News


async def init_db():
    """Initialize database and create tables"""
    # Use local path instead of config URL (which has absolute path issues on Windows)
    db_path = "sqlite+aiosqlite:///irecover.db"  # Relative path in current directory
    engine = create_async_engine(db_path, echo=False)
    
    # Phase 1: Drop all existing tables
    async with engine.begin() as conn:
        print("🗑️ Dropping existing tables...")
        await conn.execute(text('DROP TABLE IF EXISTS booking_summary'))
        await conn.execute(text('DROP TABLE IF EXISTS weather_disruptions'))
        
        # Create all ORM tables
        print("📦 Creating ORM tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ All ORM tables created")
    
    # Phase 2: Create booking_summary (raw SQL)
    async with engine.begin() as conn:
        print("📝 Creating booking_summary table (raw SQL)...")
        await conn.execute(text('''
            CREATE TABLE booking_summary (
                booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                awb_prefix CHAR(3) NOT NULL,
                awb_number CHAR(8) NOT NULL,
                ubr_number VARCHAR(50) NOT NULL,
                origin CHAR(3) NOT NULL,
                destination CHAR(3) NOT NULL,
                shipping_date DATE NOT NULL,
                pieces INT NOT NULL CHECK (pieces > 0),
                chargeable_weight DECIMAL(10,2) NOT NULL CHECK (chargeable_weight > 0),
                total_revenue DECIMAL(12,2) NOT NULL CHECK (total_revenue >= 0),
                currency CHAR(3) NOT NULL,
                booking_status CHAR(1) NOT NULL,
                agent_code VARCHAR(50) NOT NULL,
                cargo_type VARCHAR(50),
                created_at DATE,
                UNIQUE (awb_prefix, awb_number),
                UNIQUE (ubr_number)
            )
        '''))
        print("✅ booking_summary table created with cargo_type column")
        
        # Create weather_disruptions table
        print("🌤️ Creating weather_disruptions table...")
        await conn.execute(text('''
            CREATE TABLE weather_disruptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                airport_code CHAR(3) NOT NULL,
                disruption_date DATE NOT NULL,
                weather_type VARCHAR(50) NOT NULL,
                severity VARCHAR(10) NOT NULL,
                impact TEXT
            )
        '''))
        print("✅ weather_disruptions table created")
    
    # Phase 3: Seed booking_summary and weather data via raw SQL
    async with engine.begin() as conn:
        print("📊 Seeding booking_summary data...")
        
        # Set fixed seed for consistent data across runs
        random.seed(20260205)
        
        prefixes = ["123", "456", "789", "321", "654"]
        origins = ["JFK", "LAX", "ORD", "DFW", "ATL"]
        destinations = ["HKG", "SIN", "FRA", "LHR", "NRT"]
        agent_codes = ["AGT001", "AGT002", "AGT003"]
        special_cargo_types = [None, None, None, "PERISHABLE", "LIVE_ANIMALS", "PHARMA", "HAZMAT", "HIGH_VALUE"]
        currency = "USD"
        
        # Create 140 bookings across February 2026 (5 per day)
        booking_count = 0
        for i in range(1, 29):  # Feb 2026
            ship_date = date(2026, 2, i)
            for j in range(5):
                awb_prefix = random.choice(prefixes)
                awb_number = ''.join(random.choices(string.digits, k=8))
                ubr_number = f"UBR-{ship_date.strftime('%m%d')}-{j}"
                origin = random.choice(origins)
                dest = random.choice([d for d in destinations if d != origin])
                pieces = random.randint(1, 10)
                chargeable_weight = round(random.uniform(50, 500), 2)
                total_revenue = round(chargeable_weight * random.uniform(2, 10), 2)
                booking_status = random.choice(["C", "Q"])
                agent_code = random.choice(agent_codes)
                cargo_type = random.choice(special_cargo_types)
                
                try:
                    await conn.execute(text('''
                        INSERT INTO booking_summary (
                            awb_prefix, awb_number, ubr_number, origin, destination, 
                            shipping_date, pieces, chargeable_weight, total_revenue, 
                            currency, booking_status, agent_code, cargo_type, created_at
                        ) VALUES (
                            :awb_prefix, :awb_number, :ubr_number, :origin, :destination,
                            :shipping_date, :pieces, :chargeable_weight, :total_revenue,
                            :currency, :booking_status, :agent_code, :cargo_type, :created_at
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
                        "agent_code": agent_code,
                        "cargo_type": cargo_type,
                        "created_at": ship_date
                    })
                    booking_count += 1
                except Exception as e:
                    print(f"⚠️ Error inserting booking: {e}")
        
        print(f"✅ Seeded {booking_count} bookings for Feb 2026")
        
        # Seed weather disruption data
        print("🌩️ Seeding weather disruptions...")
        weather_data = [
            # Good weather days
            ('JFK', '2026-02-01', 'CLEAR', 'LOW', 'Clear skies, no impact'),
            ('LAX', '2026-02-01', 'CLEAR', 'LOW', 'Clear conditions'),
            ('ORD', '2026-02-01', 'PARTLY_CLOUDY', 'LOW', 'Partly cloudy, no delays'),
            ('HKG', '2026-02-01', 'CLEAR', 'LOW', 'Clear skies'),
            ('SIN', '2026-02-01', 'CLEAR', 'LOW', 'Clear conditions'),
            
            # Bad weather - Feb 3-5 (affects multiple bookings)
            ('ORD', '2026-02-03', 'SNOW', 'HIGH', 'Heavy snowfall 15-20cm. De-icing delays.'),
            ('ORD', '2026-02-04', 'SNOW', 'CRITICAL', 'Blizzard conditions. Airport at 30% capacity.'),
            ('ORD', '2026-02-05', 'ICE', 'MEDIUM', 'Freezing conditions. De-icing required.'),
            
            ('JFK', '2026-02-04', 'SNOW', 'HIGH', 'Heavy snowfall. Reduced runway capacity.'),
            ('JFK', '2026-02-05', 'SNOW', 'HIGH', 'Continued snow. Airport partially closed.'),
            
            ('LHR', '2026-02-04', 'FOG', 'CRITICAL', 'Dense fog <200m visibility. CAT III ops only.'),
            ('LHR', '2026-02-05', 'FOG', 'HIGH', 'Persistent fog. Delays 4-6 hours.'),
            
            ('SIN', '2026-02-08', 'THUNDERSTORM', 'MEDIUM', 'Afternoon thunderstorms.'),
            ('HKG', '2026-02-10', 'TYPHOON', 'CRITICAL', 'Typhoon approaching. Airport closed 12+ hours.'),
            ('FRA', '2026-02-12', 'ICE', 'HIGH', 'Freezing rain. De-icing delays.'),
            ('ATL', '2026-02-14', 'THUNDERSTORM', 'MEDIUM', 'Severe thunderstorms.'),
            ('LAX', '2026-02-15', 'CLEAR', 'LOW', 'Perfect weather conditions'),
            ('DFW', '2026-02-18', 'FOG', 'MEDIUM', 'Morning fog. Delays until 10am.'),
            ('ORD', '2026-02-20', 'SNOW', 'HIGH', 'Winter storm. Delays 4-6 hours.'),
            ('JFK', '2026-02-22', 'ICE', 'CRITICAL', 'Ice storm. Airport closed 6+ hours.'),
            ('LHR', '2026-02-25', 'FOG', 'HIGH', 'Heavy fog. Delays 3-5 hours.'),
            
            # Good weather to end the month
            ('JFK', '2026-02-28', 'CLEAR', 'LOW', 'Excellent flying conditions'),
            ('LAX', '2026-02-28', 'CLEAR', 'LOW', 'Clear skies'),
            ('ORD', '2026-02-28', 'PARTLY_CLOUDY', 'LOW', 'Mild conditions'),
            ('HKG', '2026-02-28', 'CLEAR', 'LOW', 'Clear conditions'),
            ('SIN', '2026-02-28', 'CLEAR', 'LOW', 'Clear skies'),
        ]
        
        for airport, date_str, weather, severity, impact in weather_data:
            await conn.execute(text('''
                INSERT INTO weather_disruptions (airport_code, disruption_date, weather_type, severity, impact)
                VALUES (:airport, :date, :weather, :severity, :impact)
            '''), {'airport': airport, 'date': date_str, 'weather': weather, 'severity': severity, 'impact': impact})
        
        print(f"✅ Seeded {len(weather_data)} weather disruption records")
    
    # Phase 4: Seed ORM models (News only - Flights and Disruptions are optional)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        print("📰 Seeding News records...")
        await seed_news(session)
    
    # Close all connections
    await engine.dispose()
    
    print("\n✅✅✅ Database initialization complete! ✅✅✅\n")


async def seed_news(session: AsyncSession):
    """Seed news entries that may cause disruptions"""
    
    # Disruption-causing news
    disruption_news = [
        News(
            headline="JFK Ground Crew Strike Called - Feb 4-5",
            content="Major strike by ground crew at JFK International affecting all cargo operations. Expected duration 48 hours.",
            place="New York, USA",
            date=datetime(2026, 2, 4, 6, 0, 0)
        ),
        News(
            headline="ORD Runway Closure - Winter Damage Repairs",
            content="Chicago O'Hare runway 04/22 closed for emergency repairs after winter damage. Expected duration 72 hours.",
            place="Chicago, USA",
            date=datetime(2026, 2, 3, 8, 0, 0)
        ),
        News(
            headline="LAX Customs Agency Implements Enhanced Screening",
            content="Increased security delays at LAX due to enhanced customs screening. Estimated 2-4 hour additional delays.",
            place="Los Angeles, USA",
            date=datetime(2026, 2, 6, 9, 0, 0)
        ),
        News(
            headline="DFW Ground Equipment Failure",
            content="Critical ground handling equipment failure at Dallas/Fort Worth. Reduced loading capacity affecting cargo operations.",
            place="Dallas, USA",
            date=datetime(2026, 2, 7, 10, 0, 0)
        ),
        News(
            headline="ATL Staff Shortage Impacts Operations",
            content="Atlanta Hartsfield staff shortage due to illness outbreak. Reduced cargo handling capacity for 48 hours.",
            place="Atlanta, USA",
            date=datetime(2026, 2, 9, 7, 0, 0)
        ),
        News(
            headline="SFO Power Outage Affects Terminal Operations",
            content="Power outage at San Francisco International affects cargo terminal systems. Backup systems online but delays expected.",
            place="San Francisco, USA",
            date=datetime(2026, 2, 12, 5, 0, 0)
        ),
        News(
            headline="Miami Port Hazmat Incident - Restricted Operations",
            content="Hazmat spill at Miami cargo facility. Hazmat cargo operations suspended pending investigation.",
            place="Miami, USA",
            date=datetime(2026, 2, 14, 15, 0, 0)
        ),
        News(
            headline="Major Export Embargo Announced",
            content="Government announces embargo on certain commodity types effective immediately. Affected shipments may face hold/seizure.",
            place="International",
            date=datetime(2026, 2, 16, 12, 0, 0)
        ),
        News(
            headline="Singapore Typhoon Warning - Airport Closure Expected",
            content="Tropical Typhoon approaching Singapore. Airport may close for 12-18 hours. All cargo operations suspended.",
            place="Singapore",
            date=datetime(2026, 2, 18, 10, 0, 0)
        ),
        News(
            headline="Hong Kong Customs Action - Increased Inspections",
            content="Hong Kong Customs intensifies inspections on perishable goods. Additional 3-5 hours delay per shipment.",
            place="Hong Kong",
            date=datetime(2026, 2, 20, 8, 0, 0)
        ),
        News(
            headline="Frankfurt Airport Staff Strike",
            content="Frankfurt airport staff union strikes for 24 hours. All cargo operations affected with major delays.",
            place="Frankfurt, Germany",
            date=datetime(2026, 2, 22, 6, 0, 0)
        ),
        News(
            headline="London Heathrow Winter Weather Impact",
            content="Severe winter weather at Heathrow causes runway restrictions. Flights reduced by 50%, major delays expected.",
            place="London, UK",
            date=datetime(2026, 2, 25, 4, 0, 0)
        ),
    ]
    
    # Irrelevant news (different regions, dates, topics)
    irrelevant_news = [
        News(
            headline="Tokyo Olympics - Venues Announced",
            content="Olympic committee announces venues for Tokyo summer games. Construction underway at new facilities.",
            place="Tokyo, Japan",
            date=datetime(2026, 3, 1, 0, 0, 0)
        ),
        News(
            headline="EASA Updates Safety Regulations",
            content="European Aviation Safety Agency releases new regulations affecting aircraft maintenance procedures.",
            place="Brussels, Belgium",
            date=datetime(2026, 2, 15, 10, 0, 0)
        ),
        News(
            headline="Sydney Terminal Expansion Project",
            content="Sydney Airport begins terminal expansion project expected to complete in 2028.",
            place="Sydney, Australia",
            date=datetime(2026, 2, 10, 12, 0, 0)
        ),
        News(
            headline="Abu Dhabi Hub Airline Alliance",
            content="New airline alliance formed for Middle East hub operations. Starts operations Q3 2026.",
            place="Abu Dhabi, UAE",
            date=datetime(2026, 2, 8, 14, 0, 0)
        ),
        News(
            headline="Spring Air Travel Season Begins",
            content="Airlines prepare for busy spring season with increased capacity and new routes.",
            place="Global",
            date=datetime(2026, 2, 20, 9, 0, 0)
        ),
        News(
            headline="Fiji Airport Runway Upgrade",
            content="Fiji International Airport announces runway upgrade project for enhanced capacity.",
            place="Nadi, Fiji",
            date=datetime(2026, 2, 12, 8, 0, 0)
        ),
        News(
            headline="India Pharma Facility Opens",
            content="New pharmaceutical manufacturing facility opens in Bangalore with advanced cold storage.",
            place="Bangalore, India",
            date=datetime(2026, 2, 5, 11, 0, 0)
        ),
        News(
            headline="New Cargo Alliance - Capacity Increase",
            content="Global cargo alliance announces expanded capacity for summer operations.",
            place="Global",
            date=datetime(2026, 2, 25, 10, 0, 0)
        ),
    ]
    
    all_news = disruption_news + irrelevant_news
    session.add_all(all_news)
    await session.commit()
    
    print(f"  ✅ Created {len(disruption_news)} disruption-causing news entries")
    print(f"  ✅ Created {len(irrelevant_news)} irrelevant news entries")


async def seed_flights(session: AsyncSession):
    """Seed sample flights"""
    
    flights = [
        Flight(
            id="AA100-20260205",
            flight_number="AA100",
            flight_date=datetime(2026, 2, 5, 0, 0, 0),
            aircraft_type="B777F",
            origin="JFK",
            destination="HKG",
            scheduled_departure=datetime(2026, 2, 5, 22, 0, 0),
            scheduled_arrival=datetime(2026, 2, 7, 10, 0, 0),
            status="SCHEDULED"
        ),
        Flight(
            id="UA200-20260206",
            flight_number="UA200",
            flight_date=datetime(2026, 2, 6, 0, 0, 0),
            aircraft_type="B747-8F",
            origin="LAX",
            destination="SIN",
            scheduled_departure=datetime(2026, 2, 6, 14, 0, 0),
            scheduled_arrival=datetime(2026, 2, 8, 22, 0, 0),
            status="SCHEDULED"
        ),
        Flight(
            id="FX300-20260204",
            flight_number="FX300",
            flight_date=datetime(2026, 2, 4, 0, 0, 0),
            aircraft_type="A330-200F",
            origin="ORD",
            destination="FRA",
            scheduled_departure=datetime(2026, 2, 4, 1, 0, 0),
            scheduled_arrival=datetime(2026, 2, 4, 12, 0, 0),
            status="SCHEDULED"
        ),
        Flight(
            id="BA400-20260205",
            flight_number="BA400",
            flight_date=datetime(2026, 2, 5, 0, 0, 0),
            aircraft_type="B767-300F",
            origin="LHR",
            destination="ATL",
            scheduled_departure=datetime(2026, 2, 5, 2, 0, 0),
            scheduled_arrival=datetime(2026, 2, 5, 10, 0, 0),
            status="SCHEDULED"
        ),
        Flight(
            id="NH500-20260207",
            flight_number="NH500",
            flight_date=datetime(2026, 2, 7, 0, 0, 0),
            aircraft_type="B777F",
            origin="NRT",
            destination="LAX",
            scheduled_departure=datetime(2026, 2, 7, 16, 0, 0),
            scheduled_arrival=datetime(2026, 2, 8, 8, 0, 0),
            status="SCHEDULED"
        ),
    ]
    
    session.add_all(flights)
    await session.commit()
    print(f"  ✅ Created {len(flights)} flights")


async def seed_disruptions(session: AsyncSession):
    """Seed sample disruptions (optional - can be created via API)"""
    print(f"  ⏭️ Skipping disruptions - they will be created via detection API")


if __name__ == "__main__":
    asyncio.run(init_db())
