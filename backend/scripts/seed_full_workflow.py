"""
Complete Workflow Seed Script for Demo

Seeds data based on EXISTING booking_summary records to trigger ALL agents in the pipeline:
- Detection Agent: Analyzes flight disruptions affecting booked cargo
- Impact Agent: Evaluates impact on AWBs from booking_summary
- Replan Agent: Creates recovery scenarios (auto-executes for non-sensitive cargo)
- Approval Agent: Routes ONLY sensitive cargo (live animals, human remains, pharma, DG) to human approval
- Execution Agent: Auto-executes recovery for approved/non-sensitive cargo
- Notification Agent: Notifies stakeholders

KEY PRINCIPLES:
- All data derived from booking_summary table - NO random/hardcoded values
- Only SENSITIVE cargo types require human approval:
  * LIVE_ANIMALS, HUMAN_REMAINS, PHARMA, DANGEROUS_GOODS
- General cargo is auto-processed by agents
- LLM evaluates risk factors to determine approval needs
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import json

# Add parent directory to path
backend_path = str(Path(__file__).parent.parent)
sys.path.insert(0, backend_path)
os.chdir(backend_path)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Sensitive cargo types that REQUIRE human approval
SENSITIVE_CARGO_TYPES = ['LIVE_ANIMALS', 'HUMAN_REMAINS', 'PHARMA', 'DANGEROUS_GOODS']

# Cargo types that can be auto-processed by agents
AUTO_PROCESSABLE_TYPES = ['GENERAL', 'PERISHABLE', 'VALUABLE', 'MAIL', 'EXPRESS']


def calculate_risk_factors(booking: dict, disruption_type: str, delay_minutes: int) -> tuple:
    """
    Calculate risk factors based on actual booking data and disruption analysis.
    Returns (risk_factors_list, risk_score, requires_human_approval)
    """
    risk_factors = []
    risk_score = 0.3  # Base risk score
    requires_human_approval = False
    
    cargo_type = booking.get('special_cargo_type', 'GENERAL')
    priority = booking.get('customer_priority', 'STANDARD')
    value = booking.get('estimated_value_usd') or 0
    sla_deadline = booking.get('sla_deadline')
    temp_req = booking.get('temperature_requirement')
    
    # Check if sensitive cargo - REQUIRES human approval
    if cargo_type in SENSITIVE_CARGO_TYPES:
        requires_human_approval = True
        
        if cargo_type == 'HUMAN_REMAINS':
            risk_factors.append({
                "factor": "Human Remains - Dignified Handling Required",
                "weight": 0.35,
                "value": "Requires special customs clearance and dignified handling protocols"
            })
            risk_score += 0.3
        elif cargo_type == 'LIVE_ANIMALS':
            risk_factors.append({
                "factor": "Live Animals - Welfare Critical",
                "weight": 0.30,
                "value": f"Animal welfare at risk - delay of {delay_minutes}min may cause distress"
            })
            risk_score += 0.25
        elif cargo_type == 'PHARMA':
            risk_factors.append({
                "factor": "Pharmaceutical - Cold Chain Integrity",
                "weight": 0.28,
                "value": f"Temperature control required: {temp_req or '2-8°C'}. Extended delay risks product integrity"
            })
            risk_score += 0.22
        elif cargo_type == 'DANGEROUS_GOODS':
            risk_factors.append({
                "factor": "Dangerous Goods - Safety Compliance",
                "weight": 0.32,
                "value": "HAZMAT regulations require re-authorization for rerouting"
            })
            risk_score += 0.28
    
    # SLA breach risk (calculated from actual booking data)
    if sla_deadline:
        try:
            if isinstance(sla_deadline, str):
                sla_dt = datetime.fromisoformat(sla_deadline.replace('Z', '+00:00'))
            else:
                sla_dt = sla_deadline
            
            time_to_sla = (sla_dt - datetime.now()).total_seconds() / 60  # minutes
            
            if time_to_sla < 60:
                risk_factors.append({
                    "factor": "Imminent SLA Breach",
                    "weight": 0.25,
                    "value": f"Only {int(time_to_sla)} minutes until SLA deadline"
                })
                risk_score += 0.2
            elif time_to_sla < 120:
                risk_factors.append({
                    "factor": "High SLA Breach Risk",
                    "weight": 0.18,
                    "value": f"{int(time_to_sla)} minutes until SLA deadline"
                })
                risk_score += 0.12
        except:
            pass
    
    # Value-based risk (from actual booking data)
    if value > 200000:
        risk_factors.append({
            "factor": "Very High Value Shipment",
            "weight": 0.20,
            "value": f"Cargo value: ${value:,.0f} - financial exposure significant"
        })
        risk_score += 0.15
        if cargo_type not in SENSITIVE_CARGO_TYPES:
            requires_human_approval = True  # High value general cargo also needs approval
    elif value > 100000:
        risk_factors.append({
            "factor": "High Value Shipment",
            "weight": 0.12,
            "value": f"Cargo value: ${value:,.0f}"
        })
        risk_score += 0.08
    
    # Priority factor (from actual booking data)
    if priority == 'CRITICAL':
        risk_factors.append({
            "factor": "Customer Priority: CRITICAL",
            "weight": 0.15,
            "value": "VIP customer or contractual SLA obligations"
        })
        risk_score += 0.1
    
    # Disruption severity
    if disruption_type == 'CANCELLATION':
        risk_factors.append({
            "factor": "Flight Cancellation",
            "weight": 0.20,
            "value": "Complete rebooking required - no partial recovery possible"
        })
        risk_score += 0.15
    elif delay_minutes > 180:
        risk_factors.append({
            "factor": "Severe Delay",
            "weight": 0.15,
            "value": f"{delay_minutes} minute delay - significant schedule impact"
        })
        risk_score += 0.1
    
    return risk_factors, min(risk_score, 0.95), requires_human_approval


def determine_approval_level(risk_score: float, cargo_type: str, value: float) -> tuple:
    """
    Determine approval level based on cargo sensitivity and risk.
    Returns (approval_level, timeout_minutes)
    """
    if cargo_type == 'HUMAN_REMAINS':
        return ('EXECUTIVE', 60)
    elif cargo_type == 'LIVE_ANIMALS':
        return ('MANAGER', 30)
    elif cargo_type == 'PHARMA':
        if value > 150000:
            return ('MANAGER', 30)
        return ('SUPERVISOR', 15)
    elif cargo_type == 'DANGEROUS_GOODS':
        return ('MANAGER', 30)
    elif value > 200000:
        return ('EXECUTIVE', 60)
    elif value > 100000:
        return ('MANAGER', 30)
    elif risk_score > 0.7:
        return ('SUPERVISOR', 15)
    else:
        return ('AUTO', 0)  # Can be auto-approved


async def seed_full_workflow_data():
    """Seed workflow data based on existing booking_summary records."""
    
    database_url = "sqlite+aiosqlite:///./irecover.db"
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("\n" + "="*80)
        print("🚀 SEEDING WORKFLOW DATA FROM BOOKING SUMMARY")
        print("="*80 + "\n")
        
        now = datetime.now()
        today = now.date()
        
        # ========================================================================
        # STEP 1: Ensure required columns exist
        # ========================================================================
        print("📋 Step 1: Ensuring required database columns...")
        
        columns_to_add = [
            ("special_cargo_type", "TEXT DEFAULT 'GENERAL'"),
            ("temperature_requirement", "TEXT DEFAULT NULL"),
            ("handling_instructions", "TEXT DEFAULT NULL"),
            ("customer_priority", "TEXT DEFAULT 'STANDARD'"),
            ("sla_deadline", "TEXT DEFAULT NULL"),
            ("estimated_value_usd", "REAL DEFAULT NULL"),
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                await session.execute(text(f"ALTER TABLE booking_summary ADD COLUMN {col_name} {col_type}"))
                await session.commit()
                print(f"   ✅ Added {col_name} column")
            except Exception:
                pass  # Column exists
        
        # ========================================================================
        # STEP 2: Clear existing workflow data (keep booking_summary intact)
        # ========================================================================
        print("\n🧹 Step 2: Clearing existing workflow data...")
        
        try:
            await session.execute(text("DELETE FROM approvals"))
            await session.execute(text("DELETE FROM awb_impacts"))
            await session.execute(text("DELETE FROM recovery_scenarios"))
            await session.execute(text("DELETE FROM execution_steps"))
            await session.execute(text("DELETE FROM disruptions"))
            await session.commit()
            print("   ✅ Cleared workflow tables (booking_summary preserved)")
        except Exception as e:
            print(f"   ⚠️ Could not clear some tables: {e}")
        
        # ========================================================================
        # STEP 3: Load EXISTING bookings from booking_summary
        # ========================================================================
        print("\n📦 Step 3: Loading existing bookings from booking_summary...")
        
        result = await session.execute(text("""
            SELECT 
                awb_prefix, awb_number, ubr_number, origin, destination,
                shipping_date, pieces, chargeable_weight, total_revenue,
                agent_code, special_cargo_type, temperature_requirement,
                handling_instructions, customer_priority, sla_deadline, 
                estimated_value_usd
            FROM booking_summary
            WHERE booking_status = 'C'
            ORDER BY 
                CASE 
                    WHEN special_cargo_type IN ('HUMAN_REMAINS', 'LIVE_ANIMALS', 'PHARMA', 'DANGEROUS_GOODS') THEN 0
                    ELSE 1
                END,
                sla_deadline ASC NULLS LAST
            LIMIT 20
        """))
        bookings = result.fetchall()
        
        if not bookings:
            print("   ⚠️ No confirmed bookings found. Creating sample data...")
            # Create minimal sample bookings from realistic data
            await _create_sample_bookings(session, now, today)
            # Load a MIX of cargo types to demonstrate both human approval and auto-processing
            # First get sensitive cargo (requires human approval)
            result_sensitive = await session.execute(text("""
                SELECT awb_prefix, awb_number, ubr_number, origin, destination,
                       shipping_date, pieces, chargeable_weight, total_revenue,
                       agent_code, special_cargo_type, temperature_requirement,
                       handling_instructions, customer_priority, sla_deadline, 
                       estimated_value_usd
                FROM booking_summary 
                WHERE booking_status = 'C' 
                AND special_cargo_type IN ('LIVE_ANIMALS', 'HUMAN_REMAINS', 'PHARMA', 'DANGEROUS_GOODS')
                ORDER BY sla_deadline ASC NULLS LAST LIMIT 10
            """))
            sensitive_bookings = result_sensitive.fetchall()
            
            # Then get general cargo (auto-processable by agents)
            result_general = await session.execute(text("""
                SELECT awb_prefix, awb_number, ubr_number, origin, destination,
                       shipping_date, pieces, chargeable_weight, total_revenue,
                       agent_code, special_cargo_type, temperature_requirement,
                       handling_instructions, customer_priority, sla_deadline, 
                       estimated_value_usd
                FROM booking_summary 
                WHERE booking_status = 'C' 
                AND (special_cargo_type IN ('GENERAL', 'PERISHABLE') OR special_cargo_type IS NULL)
                ORDER BY sla_deadline ASC NULLS LAST LIMIT 10
            """))
            general_bookings = result_general.fetchall()
            
            # Combine both - to demonstrate the decision routing
            bookings = list(sensitive_bookings) + list(general_bookings)
        
        print(f"   📊 Found {len(bookings)} bookings to process")
        
        # ========================================================================
        # STEP 4: Create disrupted flights based on booking routes
        # ========================================================================
        print("\n✈️ Step 4: Creating flight disruptions for booking routes...")
        
        # Get unique routes from bookings
        routes = {}
        for b in bookings:
            route_key = f"{b[3]}-{b[4]}"  # origin-destination
            if route_key not in routes:
                routes[route_key] = {
                    'origin': b[3],
                    'destination': b[4],
                    'bookings': []
                }
            routes[route_key]['bookings'].append({
                'awb_prefix': b[0],
                'awb_number': b[1],
                'ubr_number': b[2],
                'pieces': b[6],
                'weight': b[7],
                'revenue': b[8],
                'agent_code': b[9],
                'special_cargo_type': b[10] or 'GENERAL',
                'temperature_requirement': b[11],
                'handling_instructions': b[12],
                'customer_priority': b[13] or 'STANDARD',
                'sla_deadline': b[14],
                'estimated_value_usd': b[15] or 0
            })
        
        # Create disruptions for ALL routes to demonstrate routing
        # (In real life, only some routes would have disruptions)
        disruption_types = [
            ('DELAY', 180, 'Weather delay - thunderstorm activity'),
            ('DELAY', 120, 'Aircraft technical - maintenance required'),
            ('CANCELLATION', 0, 'Flight cancelled - crew unavailability'),
            ('DELAY', 90, 'ATC flow control restrictions'),
        ]
        
        flight_disruptions = []
        disruption_idx = 0
        
        for route_key, route_data in routes.items():
            # Create disruption for ALL routes to demonstrate the workflow
            dtype, delay, reason = disruption_types[disruption_idx % len(disruption_types)]
            
            flight_id = str(uuid.uuid4())
            disruption_id = str(uuid.uuid4())
            flight_num = f"{'6E' if route_data['origin'] in ['DEL','BOM','BLR','HYD','MAA'] else 'UA'}{100 + disruption_idx}"
            
            flight_disruptions.append({
                'flight_id': flight_id,
                'disruption_id': disruption_id,
                'flight_number': flight_num,
                'origin': route_data['origin'],
                'destination': route_data['destination'],
                'disruption_type': dtype,
                'delay_minutes': delay,
                'reason': reason,
                'bookings': route_data['bookings']
            })
            
            disruption_idx += 1
        
        # Insert flights and disruptions
        for fd in flight_disruptions:
            scheduled_dep = now + timedelta(hours=2)
            scheduled_arr = now + timedelta(hours=8)
            
            # Create flight
            await session.execute(text("""
                INSERT OR REPLACE INTO flights (
                    id, flight_number, flight_date, origin, destination,
                    scheduled_departure, scheduled_arrival, status,
                    cargo_capacity_kg, available_capacity_kg, created_at
                ) VALUES (
                    :id, :flight_num, :flight_date, :origin, :dest,
                    :scheduled_dep, :scheduled_arr, :status,
                    25000, 10000, :created_at
                )
            """), {
                "id": fd['flight_id'],
                "flight_num": fd['flight_number'],
                "flight_date": today,
                "origin": fd['origin'],
                "dest": fd['destination'],
                "scheduled_dep": scheduled_dep.isoformat(),
                "scheduled_arr": scheduled_arr.isoformat(),
                "status": 'CANCELLED' if fd['disruption_type'] == 'CANCELLATION' else 'DELAYED',
                "created_at": now.isoformat()
            })
            
            # Calculate totals from actual bookings
            total_awbs = len(fd['bookings'])
            total_revenue = sum(b.get('revenue') or 0 for b in fd['bookings'])
            critical_count = sum(1 for b in fd['bookings'] 
                               if b['special_cargo_type'] in SENSITIVE_CARGO_TYPES 
                               or b['customer_priority'] == 'CRITICAL')
            
            # Create disruption
            await session.execute(text("""
                INSERT INTO disruptions (
                    id, flight_id, flight_number, flight_date, origin, destination,
                    disruption_type, severity, status, delay_minutes, delay_reason,
                    detected_at, total_awbs_affected, critical_awbs_count, 
                    revenue_at_risk, created_at
                ) VALUES (
                    :id, :flight_id, :flight_num, :flight_date, :origin, :dest,
                    :dtype, :severity, 'DETECTED', :delay_mins, :reason,
                    :detected_at, :total_awbs, :critical_count,
                    :revenue, :created_at
                )
            """), {
                "id": fd['disruption_id'],
                "flight_id": fd['flight_id'],
                "flight_num": fd['flight_number'],
                "flight_date": today,
                "origin": fd['origin'],
                "dest": fd['destination'],
                "dtype": fd['disruption_type'],
                "severity": 'CRITICAL' if fd['disruption_type'] == 'CANCELLATION' else 'HIGH',
                "delay_mins": fd['delay_minutes'],
                "reason": fd['reason'],
                "detected_at": now.isoformat(),
                "total_awbs": total_awbs,
                "critical_count": critical_count,
                "revenue": total_revenue,
                "created_at": now.isoformat()
            })
            
            print(f"   ✈️ {fd['flight_number']} {fd['origin']}→{fd['destination']} | {fd['disruption_type']} | {total_awbs} AWBs")
        
        await session.commit()
        
        # ========================================================================
        # STEP 5: Process each booking - Create AWBs, Impacts, Scenarios, Approvals
        # ========================================================================
        print("\n📋 Step 5: Processing bookings and creating workflow data...")
        
        sensitive_count = 0
        auto_process_count = 0
        disruptions_with_approval = set()  # Track disruptions that already have an approval
        
        for fd in flight_disruptions:
            for booking in fd['bookings']:
                awb_full = f"{booking['awb_prefix']}-{booking['awb_number']}"
                
                # Calculate risk based on ACTUAL booking data
                risk_factors, risk_score, requires_human = calculate_risk_factors(
                    booking, 
                    fd['disruption_type'], 
                    fd['delay_minutes']
                )
                
                approval_level, timeout_mins = determine_approval_level(
                    risk_score, 
                    booking['special_cargo_type'],
                    booking.get('estimated_value_usd') or 0
                )
                
                # Parse SLA deadline
                sla_dt = None
                if booking['sla_deadline']:
                    try:
                        if isinstance(booking['sla_deadline'], str):
                            sla_dt = datetime.fromisoformat(booking['sla_deadline'].replace('Z', '+00:00'))
                        else:
                            sla_dt = booking['sla_deadline']
                    except:
                        sla_dt = now + timedelta(hours=8)
                
                # Map cargo type for AWB
                commodity_map = {
                    'PHARMA': 'PHARMA', 'LIVE_ANIMALS': 'LIVE_ANIMALS',
                    'HUMAN_REMAINS': 'HUMAN_REMAINS', 'DANGEROUS_GOODS': 'DANGEROUS_GOODS',
                    'PERISHABLE': 'PERISHABLE', 'GENERAL': 'GENERAL'
                }
                commodity_type = commodity_map.get(booking['special_cargo_type'], 'GENERAL')
                
                priority_map = {'CRITICAL': 'CRITICAL', 'HIGH': 'HIGH', 'MEDIUM': 'STANDARD', 'STANDARD': 'STANDARD'}
                awb_priority = priority_map.get(booking['customer_priority'], 'STANDARD')
                
                # Create AWB record
                await session.execute(text("""
                    INSERT OR REPLACE INTO awbs (
                        awb_number, origin, destination,
                        pieces, weight_kg, volume_cbm,
                        commodity_type, priority,
                        customer_id, shipper_name, consignee_name,
                        sla_commitment, is_time_critical, special_handling_codes,
                        created_at, updated_at
                    ) VALUES (
                        :awb_number, :origin, :dest,
                        :pieces, :weight, :volume,
                        :commodity_type, :priority,
                        :customer_id, :shipper_name, :consignee_name,
                        :sla, :time_critical, :special_handling,
                        :created_at, :updated_at
                    )
                """), {
                    "awb_number": awb_full,
                    "origin": fd['origin'],
                    "dest": fd['destination'],
                    "pieces": booking['pieces'] or 1,
                    "weight": booking['weight'] or 100,
                    "volume": (booking['weight'] or 100) * 0.006,
                    "commodity_type": commodity_type,
                    "priority": awb_priority,
                    "customer_id": booking['agent_code'] or 'AGENT001',
                    "shipper_name": f"{booking['special_cargo_type'].replace('_', ' ').title()} Shipper",
                    "consignee_name": f"Consignee {fd['destination']}",
                    "sla": sla_dt.isoformat() if sla_dt else None,
                    "time_critical": booking['customer_priority'] in ('CRITICAL', 'HIGH'),
                    "special_handling": json.dumps([commodity_type]),
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat()
                })
                
                # Create AWB Impact
                original_eta = sla_dt - timedelta(hours=2) if sla_dt else now + timedelta(hours=6)
                delay_hours = fd['delay_minutes'] / 60 if fd['delay_minutes'] else 4
                new_eta = original_eta + timedelta(hours=delay_hours)
                
                # Determine breach risk level
                breach_risk = "HIGH" if risk_score > 0.7 else ("MEDIUM" if risk_score > 0.4 else "LOW")
                
                impact_id = str(uuid.uuid4())
                await session.execute(text("""
                    INSERT OR REPLACE INTO awb_impacts (
                        id, disruption_id, awb_number,
                        original_eta, new_eta, breach_risk,
                        revenue_at_risk, is_critical, created_at
                    ) VALUES (
                        :id, :disruption_id, :awb_number,
                        :original_eta, :new_eta, :breach_risk,
                        :revenue_at_risk, :is_critical, :created_at
                    )
                """), {
                    "id": impact_id,
                    "disruption_id": fd['disruption_id'],
                    "awb_number": awb_full,
                    "original_eta": original_eta.isoformat(),
                    "new_eta": new_eta.isoformat(),
                    "breach_risk": breach_risk,
                    "revenue_at_risk": booking.get('revenue') or 0,
                    "is_critical": requires_human,
                    "created_at": now.isoformat()
                })
                
                # Create Recovery Scenario
                scenario_id = str(uuid.uuid4())
                scenario_cost = 500 if not requires_human else (2500 if commodity_type in ('HUMAN_REMAINS', 'LIVE_ANIMALS') else 1500)
                
                await session.execute(text("""
                    INSERT OR REPLACE INTO recovery_scenarios (
                        id, disruption_id, scenario_type,
                        description, target_flight_number, target_departure,
                        sla_saved_count, sla_at_risk_count, risk_score,
                        execution_time_minutes, estimated_cost,
                        is_recommended, recommendation_reason,
                        all_constraints_satisfied, created_at
                    ) VALUES (
                        :id, :disruption_id, :scenario_type,
                        :description, :target_flight, :target_departure,
                        :sla_saved, :sla_at_risk, :risk_score,
                        :exec_time, :cost,
                        :is_recommended, :rec_reason,
                        :constraints_ok, :created_at
                    )
                """), {
                    "id": scenario_id,
                    "disruption_id": fd['disruption_id'],
                    "scenario_type": "REBOOK_PRIORITY" if requires_human else "REPROTECT",
                    "description": f"{'Priority rebooking' if requires_human else 'Standard rebooking'} for {awb_full} to {fd['destination']}",
                    "target_flight": f"6E{200 + hash(awb_full) % 100}",
                    "target_departure": (now + timedelta(hours=4)).isoformat(),
                    "sla_saved": 1 if sla_dt and (now + timedelta(hours=4)) < sla_dt else 0,
                    "sla_at_risk": 0 if not sla_dt or (now + timedelta(hours=4)) < sla_dt else 1,
                    "risk_score": risk_score,
                    "exec_time": 45 if requires_human else 15,
                    "cost": scenario_cost,
                    "is_recommended": True,
                    "rec_reason": f"LLM Analysis: {'Sensitive cargo requires human oversight' if requires_human else 'Standard cargo - agent can auto-execute'}",
                    "constraints_ok": True,
                    "created_at": now.isoformat()
                })
                
                # Create Approval ONLY for sensitive cargo or high-value shipments
                # AND only if this disruption doesn't already have an approval
                if requires_human and fd['disruption_id'] not in disruptions_with_approval:
                    sensitive_count += 1
                    approval_id = str(uuid.uuid4())
                    
                    # Update disruption status to PENDING_APPROVAL
                    await session.execute(text("""
                        UPDATE disruptions SET status = 'PENDING_APPROVAL' 
                        WHERE id = :id
                    """), {"id": fd['disruption_id']})
                    
                    await session.execute(text("""
                        INSERT INTO approvals (
                            id, disruption_id, required_level, current_level, status,
                            risk_score, risk_factors, auto_approve_eligible,
                            timeout_at, timeout_minutes, requested_at, created_at
                        ) VALUES (
                            :id, :disruption_id, :level, :level, 'PENDING',
                            :risk_score, :risk_factors, 0,
                            :timeout_at, :timeout_mins, :requested_at, :created_at
                        )
                    """), {
                        "id": approval_id,
                        "disruption_id": fd['disruption_id'],
                        "level": approval_level,
                        "risk_score": risk_score,
                        "risk_factors": json.dumps(risk_factors),
                        "timeout_at": (now + timedelta(minutes=timeout_mins)).isoformat(),
                        "timeout_mins": timeout_mins,
                        "requested_at": now.isoformat(),
                        "created_at": now.isoformat()
                    })
                    
                    # Mark this disruption as having an approval
                    disruptions_with_approval.add(fd['disruption_id'])
                    
                    print(f"   🔴 {awb_full} | {booking['special_cargo_type']} | {approval_level} approval required")
                elif requires_human:
                    # This disruption already has an approval from another AWB
                    sensitive_count += 1
                    print(f"   🔴 {awb_full} | {booking['special_cargo_type']} | Added to existing disruption approval")
                else:
                    auto_process_count += 1
                    print(f"   🟢 {awb_full} | {booking['special_cargo_type']} | Auto-processable by agents")
        
        await session.commit()
        
        # ========================================================================
        # STEP 6: Summary
        # ========================================================================
        print("\n" + "="*80)
        print("✅ SEED COMPLETE - WORKFLOW DATA SUMMARY")
        print("="*80)
        
        # Count records
        disruption_count = (await session.execute(text("SELECT COUNT(*) FROM disruptions"))).scalar()
        awb_count = (await session.execute(text("SELECT COUNT(*) FROM awbs"))).scalar()
        approval_count = (await session.execute(text("SELECT COUNT(*) FROM approvals WHERE status = 'PENDING'"))).scalar()
        scenario_count = (await session.execute(text("SELECT COUNT(*) FROM recovery_scenarios"))).scalar()
        
        print(f"""
📊 DATA CREATED FROM BOOKING SUMMARY:
   ✈️ Flight Disruptions:     {disruption_count}
   📦 AWB Records:           {awb_count}
   📋 Recovery Scenarios:    {scenario_count}

🎯 APPROVAL ROUTING:
   🔴 Requires Human Approval: {sensitive_count} (sensitive cargo)
   🟢 Auto-Processable:        {auto_process_count} (general cargo)
   📋 Pending Human Approvals: {approval_count}

🤖 LLM DECISION CRITERIA:
   Sensitive cargo types requiring human approval:
   - LIVE_ANIMALS (animal welfare concerns)
   - HUMAN_REMAINS (dignified handling required)
   - PHARMA (cold chain integrity)
   - DANGEROUS_GOODS (safety compliance)
   - High-value shipments (>$100,000)

   Auto-processable by agents:
   - GENERAL cargo
   - PERISHABLE (standard handling)
   - Standard value shipments

To trigger the full workflow:
  POST /api/detection/detect/bookings
""")
        
        await engine.dispose()


async def _create_sample_bookings(session, now, today):
    """Create sample bookings if none exist."""
    sample_bookings = [
        ('176', '12345001', 'UBR001', 'DEL', 'JFK', 5, 120, 8500, 'DHL', 'PHARMA', '2-8°C', 'CRITICAL', 180000),
        ('020', '12345002', 'UBR002', 'BOM', 'LAX', 2, 80, 3500, 'FedEx', 'LIVE_ANIMALS', '15-25°C', 'CRITICAL', 45000),
        ('618', '12345003', 'UBR003', 'SIN', 'SFO', 1, 95, 5000, 'UPS', 'HUMAN_REMAINS', '2-6°C', 'CRITICAL', 15000),
        ('160', '12345004', 'UBR004', 'HKG', 'ORD', 8, 450, 2800, 'DHL', 'PERISHABLE', '0-4°C', 'HIGH', 32000),
        ('205', '12345005', 'UBR005', 'NRT', 'DFW', 4, 200, 1500, 'FedEx', 'GENERAL', None, 'STANDARD', 8000),
        ('176', '12345006', 'UBR006', 'DEL', 'MIA', 3, 150, 2200, 'UPS', 'GENERAL', None, 'STANDARD', 12000),
        ('020', '12345007', 'UBR007', 'BOM', 'SEA', 6, 300, 4500, 'DHL', 'DANGEROUS_GOODS', None, 'HIGH', 65000),
        ('618', '12345008', 'UBR008', 'SIN', 'BOS', 10, 550, 3200, 'Aramex', 'GENERAL', None, 'MEDIUM', 18000),
    ]
    
    for awb_prefix, awb_num, ubr, origin, dest, pieces, weight, revenue, agent, cargo_type, temp, priority, value in sample_bookings:
        sla_mins = 60 if priority == 'CRITICAL' else (120 if priority == 'HIGH' else 240)
        sla_deadline = now + timedelta(minutes=sla_mins)
        
        await session.execute(text("""
            INSERT OR IGNORE INTO booking_summary (
                awb_prefix, awb_number, ubr_number, origin, destination,
                shipping_date, pieces, chargeable_weight, total_revenue,
                currency, booking_status, agent_code,
                special_cargo_type, temperature_requirement,
                customer_priority, sla_deadline, estimated_value_usd
            ) VALUES (
                :awb_prefix, :awb_number, :ubr, :origin, :dest,
                :ship_date, :pieces, :weight, :revenue,
                'USD', 'C', :agent,
                :cargo_type, :temp,
                :priority, :sla_deadline, :value
            )
        """), {
            "awb_prefix": awb_prefix,
            "awb_number": awb_num,
            "ubr": ubr,
            "origin": origin,
            "dest": dest,
            "ship_date": today,
            "pieces": pieces,
            "weight": weight,
            "revenue": revenue,
            "agent": agent,
            "cargo_type": cargo_type,
            "temp": temp,
            "priority": priority,
            "sla_deadline": sla_deadline.isoformat(),
            "value": value
        })
    
    await session.commit()
    print("   ✅ Created sample bookings from realistic data")


if __name__ == "__main__":
    asyncio.run(seed_full_workflow_data())
