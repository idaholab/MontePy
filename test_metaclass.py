#!/usr/bin/env python3

import sys
sys.path.insert(0, '/home/mgale/dev/montepy')

from surface_metaclass_prototype import CylinderOnAxis, CylinderParAxis, AxisPlane, GeneralSphere, SphereOnAxis
from montepy.surfaces.surface_type import SurfaceType

# Test AxisPlane
print("\nTesting AxisPlane...")
try:
    surf3 = AxisPlane(number=3, surface_type=SurfaceType.PX)
    surf3.location = 10.0
    print(f"AxisPlane location: {surf3.location}")
    surf3.validate()
    print("AxisPlane validation passed")
except Exception as e:
    print(f"AxisPlane error: {e}")

# Test GeneralSphere
print("\nTesting GeneralSphere...")
try:
    surf4 = GeneralSphere(number=4, surface_type=SurfaceType.S)
    surf4.x = 1.0
    surf4.y = 2.0
    surf4.z = 3.0
    surf4.radius = 5.0
    print(f"GeneralSphere: x={surf4.x}, y={surf4.y}, z={surf4.z}, radius={surf4.radius}")
    surf4.validate()
    print("GeneralSphere validation passed")
except Exception as e:
    print(f"GeneralSphere error: {e}")

# Test SphereOnAxis
print("\nTesting SphereOnAxis...")
try:
    surf5 = SphereOnAxis(number=5, surface_type=SurfaceType.SX)
    surf5.location = 7.0
    surf5.radius = 4.0
    print(f"SphereOnAxis: location={surf5.location}, radius={surf5.radius}")
    surf5.validate()
    print("SphereOnAxis validation passed")
except Exception as e:
    print(f"SphereOnAxis error: {e}")

# Test CylinderOnAxis
print("Testing CylinderOnAxis...")
try:
    # Create a cylinder on axis surface
    surf = CylinderOnAxis(number=1, surface_type=SurfaceType.CX)
    print(f"Created surface: {surf}")
    print(f"Allowed types: {surf._allowed_surface_types()}")
    print(f"Number of params: {surf._number_of_params()}")
    print(f"Has radius attr: {hasattr(surf, 'radius')}")
except Exception as e:
    print(f"Error: {e}")

# Test CylinderParAxis
print("\nTesting CylinderParAxis...")
try:
    surf2 = CylinderParAxis(number=2, surface_type=SurfaceType.C_X)
    print(f"Created surface: {surf2}")
    print(f"Allowed types: {surf2._allowed_surface_types()}")
    print(f"Number of params: {surf2._number_of_params()}")
    print(f"Has coordinates attr: {hasattr(surf2, 'coordinates')}")
    print(f"Has radius attr: {hasattr(surf2, 'radius')}")
except Exception as e:
    print(f"Error: {e}")

# Test setting values
print("\nTesting setting values...")
try:
    surf.radius = 5.0
    print(f"Set radius to 5.0, got: {surf.radius}")
except Exception as e:
    print(f"Error setting radius: {e}")

try:
    surf2.coordinates = [1.0, 2.0]
    print(f"Set coordinates to [1.0, 2.0], got: {surf2.coordinates}")
    surf2.radius = 3.0
    print(f"Set radius to 3.0, got: {surf2.radius}")
except Exception as e:
    print(f"Error setting coordinates/radius: {e}")

# Test validation
print("\nTesting validation...")
try:
    surf.validate()
    print("CylinderOnAxis validation passed")
except Exception as e:
    print(f"CylinderOnAxis validation failed: {e}")

try:
    surf2.validate()
    print("CylinderParAxis validation passed")
except Exception as e:
    print(f"CylinderParAxis validation failed: {e}")