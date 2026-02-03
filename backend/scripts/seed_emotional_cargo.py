"""
Seed Emotional/Priority Cargo Data for iRecover Testing

This script creates comprehensive test data including:
- Special cargo types (live animals, pharma, perishables, DG, human remains)
- Weather disruptions
- Diverse booking scenarios
- All scenarios to test the full agent workflow

Run with: python -m scripts.seed_emotional_cargo
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
backend_path = str(Path(__file__).parent.parent)
sys.path.insert(0, backend_path)
os.chdir(backend_path)

# Import after path setup
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Now import app modules
from app.config import settings


async def seed_emotional_cargo_data():
    """Seed comprehensive test data for emotional intelligence testing."""

    print("\n" + "="*80)
    print("SEEDING EMOTIONAL CARGO TEST DATA")
    print("="*80 + "\n")

    # Create engine
    engine = create_engine(settings.database_url.replace('sqlite+aiosqlite:', 'sqlite:'))

    with Session(engine) as session:
        # ========================================================================
        # STEP 1: Add columns to booking_summary if they don't exist
        # ========================================================================
        print("📋 Step 1: Adding special cargo columns to booking_summary...")

        try:
            session.execute(text("""
                ALTER TABLE booking_summary ADD COLUMN special_cargo_type TEXT DEFAULT 'GENERAL'
            """))
            session.commit()
            print("   ✅ Added special_cargo_type column")
        except Exception:
            print("   ℹ️  special_cargo_type column already exists")

        try:
            session.execute(text("""
                ALTER TABLE booking_summary ADD COLUMN temperature_requirement TEXT DEFAULT NULL
            """))
            session.commit()
            print("   ✅ Added temperature_requirement column")
        except Exception:
            print("   ℹ️  temperature_requirement column already exists")

        try:
            session.execute(text("""
                ALTER TABLE booking_summary ADD COLUMN handling_instructions TEXT DEFAULT NULL
            """))
            session.commit()
            print("   ✅ Added handling_instructions column")
        except Exception:
            print("   ℹ️  handling_instructions column already exists")

        try:
            session.execute(text("""
                ALTER TABLE booking_summary ADD COLUMN customer_priority TEXT DEFAULT 'STANDARD'
            """))
            session.commit()
            print("   ✅ Added customer_priority column")
        except Exception:
            print("   ℹ️  customer_priority column already exists")

        # ========================================================================
        # STEP 2: Update existing bookings with diverse cargo types
        # ========================================================================
        print("\n📦 Step 2: Creating diverse emotional cargo scenarios...")

        # Get tomorrow's date for urgent shipments
        tomorrow = (datetime.now() + timedelta(days=1)).date()

        # Scenario 1: LIVE ANIMALS - Dogs (most emotional)
        session.execute(text("""
            UPDATE booking_summary 
            SET 
                special_cargo_type = 'LIVE_ANIMALS',
                handling_instructions = 'Live dogs - require water and ventilation every 4 hours. Cannot be exposed to extreme temperatures.',
                customer_priority = 'CRITICAL',
                temperature_requirement = '15-25C',
                shipping_date = :ship_date
            WHERE awb_number = '98964306'
        """), {"ship_date": tomorrow})

        print("   🐕 AWB 123-98964306: LIVE ANIMALS (Dogs)")
        print("      Priority: CRITICAL, Temp: 15-25C")
        print("      Ships: TOMORROW (urgent!)")

        # Scenario 2: PHARMA - Life-saving vaccines
        session.execute(text("""
            UPDATE booking_summary 
            SET 
                special_cargo_type = 'PHARMA',
                handling_instructions = 'Temperature-sensitive COVID-19 vaccines - must maintain 2-8C cold chain at all times. Lives depend on this shipment.',
                customer_priority = 'CRITICAL',
                temperature_requirement = '2-8C',
                shipping_date = :ship_date
            WHERE awb_number = '17249506'
        """), {"ship_date": tomorrow})

        print("   💉 AWB 321-17249506: PHARMA (Vaccines)")
        print("      Priority: CRITICAL, Temp: 2-8C cold chain")
        print("      Ships: TOMORROW (urgent!)")

        # Scenario 3: PERISHABLE - Fresh seafood
        session.execute(text("""
            UPDATE booking_summary 
            SET 
                special_cargo_type = 'PERISHABLE',
                handling_instructions = 'Fresh seafood - 24hr shelf life remaining. Must maintain 0-4C. Spoilage means total loss.',
                customer_priority = 'HIGH',
                temperature_requirement = '0-4C',
                shipping_date = :ship_date
            WHERE awb_number = '05802058'
        """), {"ship_date": tomorrow})

        print("   🐟 AWB 123-05802058: PERISHABLE (Seafood)")
        print("      Priority: HIGH, Temp: 0-4C, 24hr shelf life")
        print("      Ships: TOMORROW (urgent!)")

        # Scenario 4: DANGEROUS GOODS - Lithium batteries
        session.execute(text("""
            UPDATE booking_summary 
            SET 
                special_cargo_type = 'DANGEROUS_GOODS',
                handling_instructions = 'Lithium ion batteries - UN3480, Class 9 Dangerous Goods. Special handling and packaging required per IATA regulations.',
                customer_priority = 'HIGH',
                temperature_requirement = NULL,
                shipping_date = :ship_date
            WHERE awb_number = '48524227'
        """), {"ship_date": tomorrow})

        print("   🔋 AWB 456-48524227: DANGEROUS GOODS (Li-ion Batteries)")
        print("      Priority: HIGH, Class 9 DG")
        print("      Ships: TOMORROW (urgent!)")

        # Scenario 5: HUMAN REMAINS - Most sensitive
        session.execute(text("""
            UPDATE booking_summary 
            SET 
                special_cargo_type = 'HUMAN_REMAINS',
                handling_instructions = 'Human remains - family awaiting their loved one. Requires dignity, respect, and special documentation. Handle with utmost care.',
                customer_priority = 'CRITICAL',
                temperature_requirement = NULL,
                shipping_date = :ship_date
            WHERE awb_number = '51293326'
        """), {"ship_date": tomorrow})

        print("   ⚰️  AWB 654-51293326: HUMAN REMAINS")
        print("      Priority: CRITICAL, Dignity required")
        print("      Ships: TOMORROW (urgent!)")

        # Add a few more diverse scenarios

        # Scenario 6: High-value electronics (standard but valuable)
        result = session.execute(text("""
            SELECT awb_number FROM booking_summary 
            WHERE awb_number NOT IN ('98964306', '17249506', '05802058', '48524227', '51293326')
            LIMIT 1
        """))
        awb = result.scalar()

        if awb:
            session.execute(text("""
                UPDATE booking_summary 
                SET 
                    special_cargo_type = 'HIGH_VALUE',
                    handling_instructions = 'High-value electronics - $500K declared value. Require secure handling and tracking.',
                    customer_priority = 'HIGH',
                    shipping_date = :ship_date
                WHERE awb_number = :awb
            """), {"ship_date": (datetime.now() + timedelta(days=2)).date(), "awb": awb})

            print(f"   💎 AWB XXX-{awb}: HIGH VALUE (Electronics)")
            print("      Priority: HIGH, $500K value")

        session.commit()

        # ========================================================================
        # STEP 3: Create weather disruptions for tomorrow
        # ========================================================================
        print("\n🌩️  Step 3: Creating weather disruptions for tomorrow...")

        # Clear old weather data
        session.execute(text("DELETE FROM weather_disruptions WHERE disruption_date >= :today"), 
                       {"today": datetime.now().date()})

        weather_data = [
            {
                "airport": "LAX",
                "type": "THUNDERSTORM",
                "severity": "HIGH",
                "impact": "Severe thunderstorms causing flight delays of 3-6 hours. Lightning and heavy rain. Ground operations suspended.",
                "date": tomorrow
            },
            {
                "airport": "FRA",
                "type": "FOG",
                "severity": "MEDIUM",
                "impact": "Dense fog reducing visibility to 100m. Flight delays and diversions expected. All-weather operations only.",
                "date": tomorrow
            },
            {
                "airport": "DFW",
                "type": "TORNADO",
                "severity": "CRITICAL",
                "impact": "Tornado warning - airport operations suspended. All flights cancelled or diverted. Safety critical.",
                "date": tomorrow
            },
            {
                "airport": "SIN",
                "type": "THUNDERSTORM",
                "severity": "HIGH",
                "impact": "Heavy monsoon rain and lightning. Flight delays of 2-4 hours. Cargo operations impacted.",
                "date": tomorrow
            },
            {
                "airport": "HKG",
                "type": "TYPHOON",
                "severity": "CRITICAL",
                "impact": "Typhoon approaching - Signal 8 raised. Airport closure imminent. All operations suspended.",
                "date": tomorrow
            },
            {
                "airport": "JFK",
                "type": "SNOWSTORM",
                "severity": "HIGH",
                "impact": "Heavy snow accumulation 12+ inches. De-icing delays. Runway capacity reduced by 50%.",
                "date": tomorrow
            },
            {
                "airport": "LHR",
                "type": "ICE_STORM",
                "severity": "HIGH",
                "impact": "Freezing rain creating hazardous conditions. Ground handling limited. Cold chain facilities operational.",
                "date": tomorrow
            }
        ]

        for weather in weather_data:
            session.execute(text("""
                INSERT INTO weather_disruptions (airport_code, weather_type, severity, disruption_date, impact)
                VALUES (:airport, :type, :severity, :date, :impact)
            """), weather)

            severity_emoji = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡"
            }
            emoji = severity_emoji.get(weather["severity"], "⚪")
            print(f"   {emoji} {weather['airport']}: {weather['type']} ({weather['severity']})")

        session.commit()

        # ========================================================================
        # STEP 4: Verification
        # ========================================================================
        print("\n✅ Step 4: Verifying seeded data...")

        # Count special cargo bookings
        result = session.execute(text("""
            SELECT 
                special_cargo_type,
                COUNT(*) as count,
                COUNT(CASE WHEN customer_priority = 'CRITICAL' THEN 1 END) as critical_count
            FROM booking_summary
            WHERE special_cargo_type != 'GENERAL'
            GROUP BY special_cargo_type
        """))

        print("\n📊 Special Cargo Distribution:")
        for row in result:
            cargo_type, count, critical = row
            print(f"   • {cargo_type}: {count} booking(s), {critical} CRITICAL")

        # Count weather disruptions
        result = session.execute(text("""
            SELECT COUNT(*) FROM weather_disruptions WHERE disruption_date = :tomorrow
        """), {"tomorrow": tomorrow})

        weather_count = result.scalar()
        print(f"\n🌦️  Weather Disruptions for tomorrow: {weather_count} airports")

        # Show bookings shipping tomorrow
        result = session.execute(text("""
            SELECT 
                awb_prefix || '-' || awb_number as awb,
                origin,
                destination,
                special_cargo_type,
                customer_priority
            FROM booking_summary
            WHERE shipping_date = :tomorrow
            AND special_cargo_type != 'GENERAL'
            ORDER BY 
                CASE customer_priority
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    ELSE 3
                END
        """), {"tomorrow": tomorrow})

        print(f"\n📅 Bookings Shipping Tomorrow ({tomorrow}):")
        for row in result:
            awb, origin, dest, cargo_type, priority = row
            priority_emoji = "🔴" if priority == "CRITICAL" else "🟠" if priority == "HIGH" else "🟢"
            print(f"   {priority_emoji} {awb}: {origin}→{dest} ({cargo_type})")

    print("\n" + "="*80)
    print("✅ SEEDING COMPLETE!")
    print("="*80)
    print("\nYou can now test with:")
    print("  curl -X POST 'http://localhost:8000/api/detect/bookings?limit=10'")
    print("\nExpected disruptions: 5-7 bookings")
    print("  • LIVE_ANIMALS: Tornado + weather → CRITICAL with human approval")
    print("  • PHARMA: Severe weather → CRITICAL cold chain risk")
    print("  • PERISHABLE: Delays → HIGH spoilage risk")
    print("  • DANGEROUS_GOODS: Tornado → HIGH safety concern")
    print("  • HUMAN_REMAINS: Any delay → CRITICAL dignity concern")
    print("\n")


if __name__ == "__main__":
    asyncio.run(seed_emotional_cargo_data())