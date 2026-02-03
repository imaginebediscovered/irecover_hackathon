"""
Seed weather disruption data for testing
Run this script to populate weather_disruptions table with sample data
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.config import settings


async def seed_weather_data():
    """Seed weather disruption data for Feb 2026 bookings"""
    engine = create_async_engine(settings.database_url, echo=False)
    
    async with engine.begin() as conn:
        # Create weather_disruptions table
        await conn.execute(text('''
            CREATE TABLE IF NOT EXISTS weather_disruptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                airport_code CHAR(3) NOT NULL,
                disruption_date DATE NOT NULL,
                weather_type VARCHAR(50) NOT NULL,
                severity VARCHAR(10) NOT NULL,
                impact TEXT
            )
        '''))
        print("✅ weather_disruptions table created")
        
        # Clear existing data
        await conn.execute(text('DELETE FROM weather_disruptions'))
        
        # Weather data for Feb 2026 - mix of good and bad weather
        weather_data = [
            # Good weather days
            ('DXB', '2026-02-01', 'CLEAR', 'LOW', 'Clear skies, no impact'),
            ('JFK', '2026-02-01', 'CLEAR', 'LOW', 'Clear conditions'),
            ('LHR', '2026-02-01', 'PARTLY_CLOUDY', 'LOW', 'Partly cloudy, no delays'),
            
            # Bad weather - Feb 3-5 (affects multiple bookings)
            ('DXB', '2026-02-03', 'SANDSTORM', 'HIGH', 'Severe sandstorm reducing visibility to <500m. Flight delays expected 4-6 hours.'),
            ('DXB', '2026-02-04', 'SANDSTORM', 'CRITICAL', 'Ongoing sandstorm. Airport operating at 30% capacity. Delays 6-12 hours.'),
            ('DXB', '2026-02-05', 'DUST', 'MEDIUM', 'Residual dust. Reduced capacity, delays 2-4 hours.'),
            
            ('JFK', '2026-02-04', 'SNOW', 'HIGH', 'Heavy snowfall 15-20cm. De-icing delays, reduced runway capacity.'),
            ('JFK', '2026-02-05', 'SNOW', 'HIGH', 'Blizzard conditions. Airport partially closed. Delays 8+ hours.'),
            
            ('LHR', '2026-02-04', 'FOG', 'CRITICAL', 'Dense fog <200m visibility. CAT III operations only. Massive delays.'),
            ('LHR', '2026-02-05', 'FOG', 'HIGH', 'Persistent fog. Reduced capacity, delays 4-6 hours.'),
            
            # More scattered disruptions
            ('SIN', '2026-02-08', 'THUNDERSTORM', 'MEDIUM', 'Afternoon thunderstorms causing 1-2 hour delays'),
            ('HKG', '2026-02-10', 'TYPHOON', 'CRITICAL', 'Typhoon approaching. Airport closed for 12+ hours. All flights cancelled.'),
            ('FRA', '2026-02-12', 'ICE', 'HIGH', 'Freezing rain. De-icing delays 3-5 hours.'),
            ('CDG', '2026-02-14', 'SNOW', 'MEDIUM', 'Light snow. Delays 1-2 hours.'),
            ('SYD', '2026-02-15', 'CLEAR', 'LOW', 'Perfect weather conditions'),
            ('BOM', '2026-02-18', 'FOG', 'MEDIUM', 'Morning fog. Delays until 10am.'),
            
            # Late Feb chaos
            ('DXB', '2026-02-20', 'SANDSTORM', 'HIGH', 'Another sandstorm event. Delays 4-6 hours.'),
            ('JFK', '2026-02-22', 'ICE', 'CRITICAL', 'Ice storm. Airport closed 6+ hours.'),
            ('LHR', '2026-02-25', 'FOG', 'HIGH', 'Heavy fog. Delays 3-5 hours.'),
            
            # Good weather to end the month
            ('DXB', '2026-02-28', 'CLEAR', 'LOW', 'Excellent flying conditions'),
            ('JFK', '2026-02-28', 'CLEAR', 'LOW', 'Clear skies'),
            ('LHR', '2026-02-28', 'PARTLY_CLOUDY', 'LOW', 'Mild conditions'),
        ]
        
        for airport, date, weather, severity, impact in weather_data:
            await conn.execute(text('''
                INSERT INTO weather_disruptions (airport_code, disruption_date, weather_type, severity, impact)
                VALUES (:airport, :date, :weather, :severity, :impact)
            '''), {'airport': airport, 'date': date, 'weather': weather, 'severity': severity, 'impact': impact})
        
        print(f"✅ Seeded {len(weather_data)} weather disruption records")
        
        # Show summary
        result = await conn.execute(text('''
            SELECT airport_code, COUNT(*) as disruptions, 
                   SUM(CASE WHEN severity IN ('HIGH', 'CRITICAL') THEN 1 ELSE 0 END) as severe
            FROM weather_disruptions
            GROUP BY airport_code
            ORDER BY disruptions DESC
        '''))
        
        print("\n📊 Weather Disruptions Summary:")
        for row in result:
            print(f"  {row[0]}: {row[1]} total disruptions ({row[2]} severe)")
    
    await engine.dispose()
    print("\n✅ Weather data seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_weather_data())
