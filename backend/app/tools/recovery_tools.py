"""
Recovery Tools

Tools for generating and evaluating recovery options:
- Interline partner availability
- Road feeder (truck) service options
- Route optimization
- Capacity allocation
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


# Mock data for partner airlines and truck services
INTERLINE_PARTNERS = {
    "CX": {  # Cathay Pacific
        "partners": ["BA", "AA", "QF", "JL", "SQ", "LH", "AF"],
        "hubs": {
            "BA": ["LHR", "JFK"],
            "AA": ["DFW", "MIA", "LAX"],
            "QF": ["SYD", "MEL"],
            "JL": ["NRT", "HND"],
            "SQ": ["SIN"],
            "LH": ["FRA", "MUC"],
            "AF": ["CDG"]
        }
    }
}

TRUCK_SERVICE_PROVIDERS = {
    "EUROPE": {
        "providers": ["DHL_RFS", "GEODIS", "DSV", "KUHNE_NAGEL"],
        "max_distance_km": 800,
        "routes": {
            "FRA-AMS": {"distance_km": 450, "transit_hours": 6, "cost_per_kg": 0.45},
            "FRA-CDG": {"distance_km": 480, "transit_hours": 6, "cost_per_kg": 0.48},
            "LHR-AMS": {"distance_km": 400, "transit_hours": 5, "cost_per_kg": 0.50},
            "LHR-CDG": {"distance_km": 350, "transit_hours": 5, "cost_per_kg": 0.45},
            "FRA-MUC": {"distance_km": 400, "transit_hours": 5, "cost_per_kg": 0.40},
        }
    },
    "ASIA": {
        "providers": ["YAMATO", "KINTETSU", "NIPPON_EXPRESS"],
        "max_distance_km": 500,
        "routes": {
            "NRT-HND": {"distance_km": 80, "transit_hours": 2, "cost_per_kg": 0.60},
            "HKG-SZX": {"distance_km": 100, "transit_hours": 2, "cost_per_kg": 0.35},
            "SIN-KUL": {"distance_km": 350, "transit_hours": 5, "cost_per_kg": 0.40},
        }
    },
    "NORTH_AMERICA": {
        "providers": ["FEDEX_RFS", "UPS_RFS", "XPO"],
        "max_distance_km": 600,
        "routes": {
            "JFK-EWR": {"distance_km": 30, "transit_hours": 1, "cost_per_kg": 0.55},
            "LAX-SFO": {"distance_km": 600, "transit_hours": 8, "cost_per_kg": 0.50},
            "ORD-DTW": {"distance_km": 450, "transit_hours": 6, "cost_per_kg": 0.45},
        }
    }
}


async def check_interline_availability(
    origin: str,
    destination: str,
    departure_after: datetime,
    required_capacity_kg: float,
    cargo_type: str = "GENERAL"
) -> Dict[str, Any]:
    """
    Check availability on partner airline flights.
    
    Args:
        origin: Origin airport code
        destination: Destination airport code
        departure_after: Earliest acceptable departure time
        required_capacity_kg: Required cargo capacity in kg
        cargo_type: Type of cargo (GENERAL, PHARMA, DG, PERISHABLE)
        
    Returns:
        Dictionary with available interline options
    """
    logger.info(
        "Checking interline availability",
        origin=origin,
        destination=destination,
        capacity=required_capacity_kg
    )
    
    # In real implementation, would call partner airline APIs
    # For now, generate mock options
    
    options = []
    partners = INTERLINE_PARTNERS.get("CX", {}).get("partners", [])
    
    for partner in partners[:3]:  # Limit to top 3 partners
        # Generate mock flight option
        flight_time = departure_after + timedelta(hours=2 + len(options))
        
        option = {
            "partner_airline": partner,
            "flight_number": f"{partner}{100 + len(options) * 10}",
            "departure": flight_time.isoformat(),
            "arrival": (flight_time + timedelta(hours=8)).isoformat(),
            "available_capacity_kg": required_capacity_kg * 1.2,  # Some margin
            "cost_per_kg": 2.5 + (len(options) * 0.3),
            "handling_fee": 150.0,
            "interline_agreement": True,
            "dg_capable": partner in ["BA", "LH", "SQ"],
            "temp_controlled": partner in ["SQ", "LH", "QF"],
            "booking_deadline_hours": 4,
            "cutoff_time": (flight_time - timedelta(hours=3)).isoformat()
        }
        options.append(option)
    
    return {
        "origin": origin,
        "destination": destination,
        "search_time": datetime.utcnow().isoformat(),
        "options_found": len(options),
        "options": options,
        "best_option": options[0] if options else None,
        "cargo_type_supported": cargo_type != "LIVE_ANIMALS"  # Most partners don't handle live animals
    }


async def check_truck_options(
    origin: str,
    destination: str,
    required_capacity_kg: float,
    pickup_after: datetime,
    delivery_deadline: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Check road feeder service (truck) options.
    
    Args:
        origin: Origin airport code
        destination: Destination airport code (can be airport or city)
        required_capacity_kg: Required cargo capacity in kg
        pickup_after: Earliest pickup time
        delivery_deadline: Latest acceptable delivery time
        
    Returns:
        Dictionary with available truck options
    """
    logger.info(
        "Checking truck options",
        origin=origin,
        destination=destination,
        capacity=required_capacity_kg
    )
    
    # Determine region
    region = None
    for reg, data in TRUCK_SERVICE_PROVIDERS.items():
        route_key = f"{origin}-{destination}"
        if route_key in data["routes"]:
            region = reg
            break
    
    if not region:
        # Check reverse route
        for reg, data in TRUCK_SERVICE_PROVIDERS.items():
            route_key = f"{destination}-{origin}"
            if route_key in data["routes"]:
                region = reg
                break
    
    options = []
    
    if region:
        providers = TRUCK_SERVICE_PROVIDERS[region]["providers"]
        route_key = f"{origin}-{destination}"
        route_data = TRUCK_SERVICE_PROVIDERS[region]["routes"].get(route_key)
        
        if route_data:
            for i, provider in enumerate(providers[:2]):  # Top 2 providers
                pickup_time = pickup_after + timedelta(hours=1 + i)
                transit_hours = route_data["transit_hours"]
                arrival_time = pickup_time + timedelta(hours=transit_hours)
                
                # Check if meets deadline
                meets_deadline = True
                if delivery_deadline and arrival_time > delivery_deadline:
                    meets_deadline = False
                
                cost = required_capacity_kg * route_data["cost_per_kg"]
                
                option = {
                    "provider": provider,
                    "service_type": "Road Feeder Service",
                    "origin": origin,
                    "destination": destination,
                    "pickup_time": pickup_time.isoformat(),
                    "estimated_arrival": arrival_time.isoformat(),
                    "transit_hours": transit_hours,
                    "distance_km": route_data["distance_km"],
                    "max_capacity_kg": 20000,  # Typical truck capacity
                    "available_capacity_kg": 20000 - (i * 5000),  # Some already used
                    "cost_estimate": round(cost, 2),
                    "cost_per_kg": route_data["cost_per_kg"],
                    "meets_deadline": meets_deadline,
                    "tracking_available": True,
                    "temp_controlled_available": True,
                    "dg_approved": provider in ["DHL_RFS", "FEDEX_RFS"]
                }
                options.append(option)
    
    # Generate fallback generic option if no specific route
    if not options:
        options.append({
            "provider": "CHARTER_TRUCK",
            "service_type": "Charter Truck Service",
            "origin": origin,
            "destination": destination,
            "pickup_time": (pickup_after + timedelta(hours=2)).isoformat(),
            "estimated_arrival": (pickup_after + timedelta(hours=10)).isoformat(),
            "transit_hours": 8,
            "distance_km": 500,
            "available_capacity_kg": 15000,
            "cost_estimate": required_capacity_kg * 0.75,
            "meets_deadline": True,
            "is_charter": True,
            "note": "Charter option - higher cost but guaranteed capacity"
        })
    
    return {
        "origin": origin,
        "destination": destination,
        "region": region or "UNKNOWN",
        "search_time": datetime.utcnow().isoformat(),
        "options_found": len(options),
        "options": options,
        "recommended_option": options[0] if options else None,
        "truck_feasible": len(options) > 0
    }


async def optimize_cargo_allocation(
    awbs: List[Dict[str, Any]],
    available_flights: List[Dict[str, Any]],
    constraints: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Optimize cargo allocation across multiple flights.
    
    Uses a greedy algorithm (would use OR-Tools in production) to:
    - Maximize SLA compliance
    - Respect capacity constraints
    - Consider priority and special handling
    
    Args:
        awbs: List of AWBs to allocate
        available_flights: List of available flight options
        constraints: Allocation constraints (DG, temp, etc.)
        
    Returns:
        Optimized allocation plan
    """
    logger.info(
        "Optimizing cargo allocation",
        awb_count=len(awbs),
        flight_options=len(available_flights)
    )
    
    # Sort AWBs by priority (CRITICAL first)
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_awbs = sorted(awbs, key=lambda x: priority_order.get(x.get("priority", "LOW"), 3))
    
    # Sort flights by departure time (earliest first)
    sorted_flights = sorted(available_flights, key=lambda x: x.get("departure", ""))
    
    # Greedy allocation
    allocations = []
    unallocated = []
    flight_remaining_capacity = {f["flight_id"]: f.get("available_capacity_kg", 0) for f in sorted_flights}
    
    for awb in sorted_awbs:
        weight = awb.get("weight", 0)
        allocated = False
        
        for flight in sorted_flights:
            flight_id = flight["flight_id"]
            remaining = flight_remaining_capacity.get(flight_id, 0)
            
            if remaining >= weight:
                # Check constraints
                constraints_ok = True
                
                # DG check
                if awb.get("is_dg") and not flight.get("dg_capable"):
                    constraints_ok = False
                
                # Temperature check
                if awb.get("requires_temp_control") and not flight.get("temp_controlled"):
                    constraints_ok = False
                
                if constraints_ok:
                    allocations.append({
                        "awb_id": awb["id"],
                        "awb_number": awb.get("awb_number"),
                        "flight_id": flight_id,
                        "flight_number": flight.get("flight_number"),
                        "weight": weight,
                        "priority": awb.get("priority")
                    })
                    flight_remaining_capacity[flight_id] -= weight
                    allocated = True
                    break
        
        if not allocated:
            unallocated.append({
                "awb_id": awb["id"],
                "awb_number": awb.get("awb_number"),
                "weight": weight,
                "priority": awb.get("priority"),
                "reason": "No suitable flight with capacity"
            })
    
    # Calculate metrics
    total_weight_allocated = sum(a["weight"] for a in allocations)
    total_weight_requested = sum(a.get("weight", 0) for a in awbs)
    critical_allocated = len([a for a in allocations if a.get("priority") == "CRITICAL"])
    critical_total = len([a for a in awbs if a.get("priority") == "CRITICAL"])
    
    return {
        "optimization_id": f"OPT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "total_awbs": len(awbs),
        "allocated_count": len(allocations),
        "unallocated_count": len(unallocated),
        "allocations": allocations,
        "unallocated": unallocated,
        "metrics": {
            "allocation_rate": len(allocations) / len(awbs) if awbs else 0,
            "weight_allocated_kg": total_weight_allocated,
            "weight_requested_kg": total_weight_requested,
            "weight_allocation_rate": total_weight_allocated / total_weight_requested if total_weight_requested else 0,
            "critical_allocation_rate": critical_allocated / critical_total if critical_total else 1.0
        },
        "solver": "GREEDY",  # Would be "OR-TOOLS" in production
        "optimization_time_ms": 50
    }


async def score_recovery_scenario(
    scenario: Dict[str, Any],
    impact_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Score a recovery scenario based on multiple criteria.
    
    Scoring weights:
    - SLA Protection: 40%
    - Cost Efficiency: 20%
    - Execution Risk: 20%
    - Customer Impact: 20%
    
    Args:
        scenario: Recovery scenario to score
        impact_data: Impact analysis data
        
    Returns:
        Scored scenario with detailed breakdown
    """
    # Extract scenario details
    scenario_type = scenario.get("type", "REPROTECT")
    awbs_recovered = scenario.get("awbs_recovered", 0)
    total_awbs = impact_data.get("total_awbs", 1)
    estimated_cost = scenario.get("estimated_cost", 0)
    execution_time = scenario.get("execution_time_minutes", 60)
    
    # SLA Score (40%) - percentage of AWBs saved from SLA breach
    sla_at_risk = impact_data.get("sla_breach_count", 0)
    sla_saved = min(awbs_recovered, sla_at_risk)
    sla_score = (sla_saved / sla_at_risk * 100) if sla_at_risk > 0 else 100
    
    # Cost Score (20%) - lower cost = higher score
    revenue_at_risk = impact_data.get("total_revenue_at_risk", 10000)
    cost_ratio = estimated_cost / revenue_at_risk if revenue_at_risk > 0 else 1
    cost_score = max(0, 100 - (cost_ratio * 100))
    
    # Execution Risk Score (20%) - based on scenario complexity
    risk_factors = {
        "REPROTECT": 10,  # Lowest risk
        "REROUTE": 25,
        "INTERLINE": 35,
        "TRUCK": 30,
        "SPLIT": 45,  # Highest complexity
    }
    base_risk = risk_factors.get(scenario_type, 50)
    time_risk = min(20, execution_time / 10)  # More time = more risk
    execution_score = 100 - base_risk - time_risk
    
    # Customer Impact Score (20%) - critical customer satisfaction
    critical_awbs = impact_data.get("critical_awbs_count", 0)
    critical_recovered = scenario.get("critical_awbs_recovered", 0)
    customer_score = (critical_recovered / critical_awbs * 100) if critical_awbs > 0 else 100
    
    # Weighted total
    total_score = (
        sla_score * 0.40 +
        cost_score * 0.20 +
        execution_score * 0.20 +
        customer_score * 0.20
    )
    
    # Risk score (inverse of total, 0-1 scale, lower is better)
    risk_score = 1 - (total_score / 100)
    
    return {
        "scenario_id": scenario.get("id"),
        "scenario_type": scenario_type,
        "total_score": round(total_score, 2),
        "risk_score": round(risk_score, 3),
        "score_breakdown": {
            "sla_protection": {
                "score": round(sla_score, 2),
                "weight": 0.40,
                "weighted_score": round(sla_score * 0.40, 2),
                "detail": f"{sla_saved}/{sla_at_risk} SLAs protected"
            },
            "cost_efficiency": {
                "score": round(cost_score, 2),
                "weight": 0.20,
                "weighted_score": round(cost_score * 0.20, 2),
                "detail": f"${estimated_cost:,.0f} cost vs ${revenue_at_risk:,.0f} at risk"
            },
            "execution_risk": {
                "score": round(execution_score, 2),
                "weight": 0.20,
                "weighted_score": round(execution_score * 0.20, 2),
                "detail": f"{scenario_type} with {execution_time}min execution"
            },
            "customer_impact": {
                "score": round(customer_score, 2),
                "weight": 0.20,
                "weighted_score": round(customer_score * 0.20, 2),
                "detail": f"{critical_recovered}/{critical_awbs} critical customers served"
            }
        },
        "recommendation": "RECOMMENDED" if total_score >= 70 else "ACCEPTABLE" if total_score >= 50 else "NOT_RECOMMENDED"
    }
