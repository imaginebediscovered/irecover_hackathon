"""
Constraint Tools

Tools for checking cargo handling constraints.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


# Mock data for constraint checking
# In real implementation, these would query actual regulatory databases

DG_COMPATIBILITY_MATRIX = {
    # DG class -> compatible aircraft types
    "1": ["B777F", "B747F"],  # Explosives - freighter only
    "2": ["B777F", "B747F", "A330F"],  # Gases
    "3": ["B777F", "B747F", "A330F", "B787"],  # Flammable liquids
    "4": ["B777F", "B747F", "A330F"],  # Flammable solids
    "5": ["B777F", "B747F", "A330F", "B787"],  # Oxidizers
    "6": ["B777F", "B747F", "A330F", "B787", "A350"],  # Toxic substances
    "7": ["B777F", "B747F"],  # Radioactive - freighter only
    "8": ["B777F", "B747F", "A330F", "B787"],  # Corrosives
    "9": ["B777F", "B747F", "A330F", "B787", "A350", "B737"],  # Miscellaneous
}

EMBARGO_RESTRICTIONS = {
    # Country code -> restricted product types
    "RU": ["ELECTRONICS", "AEROSPACE", "DUAL_USE"],
    "BY": ["ELECTRONICS", "AEROSPACE", "DUAL_USE"],
    "KP": ["ALL"],
    "IR": ["ALL"],
    "SY": ["ALL"],
}


async def check_dg_compatibility(
    dg_class: str,
    aircraft_type: str,
    origin: str,
    destination: str
) -> Dict[str, Any]:
    """
    Check if dangerous goods can be transported on a specific aircraft/route.
    
    Args:
        dg_class: UN dangerous goods class (1-9)
        aircraft_type: IATA aircraft type code
        origin: Origin airport code
        destination: Destination airport code
        
    Returns:
        Dictionary containing:
        - compatible: boolean indicating if DG can be transported
        - restrictions: list of any applicable restrictions
        - regulatory_reference: applicable regulation
    """
    compatible_aircraft = DG_COMPATIBILITY_MATRIX.get(dg_class, [])
    is_compatible = aircraft_type in compatible_aircraft
    
    restrictions = []
    
    if not is_compatible:
        restrictions.append(f"Aircraft type {aircraft_type} not approved for DG class {dg_class}")
    
    # Check for route-specific restrictions
    if dg_class in ["1", "7"]:
        restrictions.append("Requires special handling approval")
        restrictions.append("48-hour advance notification required")
    
    return {
        "compatible": is_compatible and len(restrictions) == 0,
        "dg_class": dg_class,
        "aircraft_type": aircraft_type,
        "approved_aircraft": compatible_aircraft,
        "restrictions": restrictions,
        "regulatory_reference": "IATA DGR 65th Edition",
        "requires_shipper_declaration": True,
        "requires_special_approval": dg_class in ["1", "7"]
    }


async def check_temperature_requirements(
    required_min: float,
    required_max: float,
    aircraft_type: str,
    transit_time_hours: float
) -> Dict[str, Any]:
    """
    Check if temperature requirements can be met.
    
    Args:
        required_min: Minimum required temperature (Celsius)
        required_max: Maximum required temperature (Celsius)
        aircraft_type: IATA aircraft type code
        transit_time_hours: Expected transit time
        
    Returns:
        Dictionary containing:
        - can_maintain: boolean indicating if requirements can be met
        - available_range: temperature range available
        - container_required: type of container needed
    """
    # Aircraft temperature control capabilities
    aircraft_capabilities = {
        "B777F": {"min": -20, "max": 25, "has_active_control": True},
        "B747F": {"min": -20, "max": 25, "has_active_control": True},
        "A330F": {"min": -15, "max": 25, "has_active_control": True},
        "B787": {"min": 2, "max": 25, "has_active_control": False},
        "A350": {"min": 2, "max": 25, "has_active_control": False},
        "B737": {"min": 10, "max": 25, "has_active_control": False},
    }
    
    capability = aircraft_capabilities.get(aircraft_type, {"min": 10, "max": 25, "has_active_control": False})
    
    can_maintain = (
        capability["min"] <= required_min and
        capability["max"] >= required_max
    )
    
    # Determine container type
    if required_min < 2:
        container = "ACTIVE_CONTAINER"  # e.g., Envirotainer
    elif required_min < 8:
        container = "PASSIVE_CONTAINER"  # e.g., Cool Dolly
    else:
        container = "THERMAL_BLANKET"
    
    # Transit time considerations
    warnings = []
    if transit_time_hours > 24 and not capability["has_active_control"]:
        warnings.append("Extended transit may require active container")
    
    if transit_time_hours > 48 and required_min < 8:
        warnings.append("Consider dry ice replenishment")
    
    return {
        "can_maintain": can_maintain,
        "required_range": {"min": required_min, "max": required_max},
        "aircraft_range": {"min": capability["min"], "max": capability["max"]},
        "has_active_control": capability["has_active_control"],
        "container_required": container,
        "transit_time_hours": transit_time_hours,
        "warnings": warnings
    }


async def check_embargo_restrictions(
    origin: str,
    destination: str,
    transit_points: List[str],
    product_type: str,
    shipper_country: str,
    consignee_country: str
) -> Dict[str, Any]:
    """
    Check for embargo and trade restrictions on a shipment.
    
    Args:
        origin: Origin airport code
        destination: Destination airport code
        transit_points: List of transit airport codes
        product_type: Type of product being shipped
        shipper_country: Country code of shipper
        consignee_country: Country code of consignee
        
    Returns:
        Dictionary containing:
        - clear: boolean indicating if no restrictions apply
        - restrictions: list of applicable restrictions
        - required_licenses: list of required export/import licenses
    """
    # Extract country codes from airport codes (simplified)
    # In real implementation, would use airport-to-country mapping
    all_countries = set()
    
    # Get countries for all points in routing
    for airport in [origin, destination] + transit_points:
        # Simplified: use first 2 chars as country proxy
        country = airport[:2] if len(airport) >= 2 else airport
        all_countries.add(country)
    
    # Check embargos
    restrictions = []
    required_licenses = []
    
    for country in all_countries:
        if country in EMBARGO_RESTRICTIONS:
            restricted_products = EMBARGO_RESTRICTIONS[country]
            if "ALL" in restricted_products or product_type in restricted_products:
                restrictions.append(f"Embargo restriction for {country}")
    
    # Check consignee country
    if consignee_country in EMBARGO_RESTRICTIONS:
        restricted = EMBARGO_RESTRICTIONS[consignee_country]
        if "ALL" in restricted:
            restrictions.append(f"Complete embargo on shipments to {consignee_country}")
        elif product_type in restricted:
            restrictions.append(f"Product type {product_type} restricted to {consignee_country}")
    
    # Export license requirements
    if product_type in ["ELECTRONICS", "AEROSPACE", "DUAL_USE"]:
        required_licenses.append("Export License Required")
    
    return {
        "clear": len(restrictions) == 0,
        "routing_checked": {
            "origin": origin,
            "destination": destination,
            "transit_points": transit_points
        },
        "product_type": product_type,
        "restrictions": restrictions,
        "required_licenses": required_licenses,
        "regulatory_basis": "EAR/ITAR Compliance Check"
    }


async def validate_all_constraints(
    awb_data: Dict[str, Any],
    flight_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate all constraints for an AWB on a specific flight.
    
    Args:
        awb_data: Dictionary containing AWB details
        flight_data: Dictionary containing flight details
        
    Returns:
        Dictionary containing:
        - all_satisfied: boolean indicating if all constraints pass
        - constraint_results: detailed results for each constraint
        - blocking_constraints: list of constraints that failed
    """
    results = {}
    blocking = []
    
    # DG check
    if awb_data.get("is_dangerous_goods") and awb_data.get("dg_class"):
        dg_result = await check_dg_compatibility(
            dg_class=awb_data["dg_class"],
            aircraft_type=flight_data.get("aircraft_type", ""),
            origin=awb_data.get("origin", ""),
            destination=awb_data.get("destination", "")
        )
        results["dg_compatibility"] = dg_result
        if not dg_result["compatible"]:
            blocking.append("dg_compatibility")
    else:
        results["dg_compatibility"] = {"compatible": True, "not_applicable": True}
    
    # Temperature check
    if awb_data.get("requires_temperature_control"):
        temp_result = await check_temperature_requirements(
            required_min=awb_data.get("temperature_min", 2),
            required_max=awb_data.get("temperature_max", 8),
            aircraft_type=flight_data.get("aircraft_type", ""),
            transit_time_hours=flight_data.get("transit_time_hours", 24)
        )
        results["temperature"] = temp_result
        if not temp_result["can_maintain"]:
            blocking.append("temperature")
    else:
        results["temperature"] = {"can_maintain": True, "not_applicable": True}
    
    # Capacity check
    capacity_ok = (
        flight_data.get("available_capacity_kg", 0) >= 
        awb_data.get("weight_kg", 0)
    )
    results["capacity"] = {
        "sufficient": capacity_ok,
        "required_kg": awb_data.get("weight_kg", 0),
        "available_kg": flight_data.get("available_capacity_kg", 0)
    }
    if not capacity_ok:
        blocking.append("capacity")
    
    # Embargo check
    embargo_result = await check_embargo_restrictions(
        origin=awb_data.get("origin", ""),
        destination=awb_data.get("destination", ""),
        transit_points=[],
        product_type=awb_data.get("product_type", "GENERAL"),
        shipper_country=awb_data.get("shipper_country", ""),
        consignee_country=awb_data.get("consignee_country", "")
    )
    results["embargo"] = embargo_result
    if not embargo_result["clear"]:
        blocking.append("embargo")
    
    return {
        "all_satisfied": len(blocking) == 0,
        "constraint_results": results,
        "blocking_constraints": blocking,
        "total_constraints_checked": len(results),
        "constraints_passed": len(results) - len(blocking)
    }
