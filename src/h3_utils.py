import h3

def get_h3_index(lat: float, lng: float, resolution: int = 11) -> str:
    if hasattr(h3, "latlng_to_cell"):
        return h3.latlng_to_cell(lat, lng, resolution)
    if hasattr(h3, "geo_to_h3"):
        return h3.geo_to_h3(lat, lng, resolution)
    raise RuntimeError("H3 API not found (no latlng_to_cell / geo_to_h3).")


ZONE_COORDINATES = {
    "main_building": (43.2081, 76.6700),
    "dormitory": (43.2075, 76.6695),
    "sports_complex": (43.2088, 76.6710),
    "cafeteria": (43.2078, 76.6705),
    "library": (43.2084, 76.6698),
}

CAMPUS_ZONES = {
    get_h3_index(lat, lng): name
    for name, (lat, lng) in [
        ("Main Building", (43.2081, 76.6700)),
        ("Dormitory", (43.2075, 76.6695)),
        ("Sports Complex", (43.2088, 76.6710)),
        ("Cafeteria", (43.2078, 76.6705)),
        ("Library", (43.2084, 76.6698)),
    ]
}

def get_zone_name(h3_index: str) -> str:
    return CAMPUS_ZONES.get(h3_index, "Unknown Zone")

def get_h3_by_zone_name(zone_name: str) -> str:
    coords = ZONE_COORDINATES.get(zone_name.lower())
    if not coords:
        raise ValueError(f"Unknown zone: {zone_name}. Available zones: {list(ZONE_COORDINATES.keys())}")
    return get_h3_index(coords[0], coords[1])