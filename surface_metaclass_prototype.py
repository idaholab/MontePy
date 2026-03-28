# Prototype metaclass for creating surface classes

from montepy.mcnp_object import _ExceptionContextAdder
from typing import Dict, List, Set, Any, Callable, Union
from numbers import Real
from dataclasses import dataclass
from montepy.surfaces.surface import Surface, InitInput
from montepy.surfaces.surface_type import SurfaceType
from montepy.utilities import make_prop_val_node
from montepy.exceptions import IllegalState


@dataclass
class SurfaceSpec:
    """Specification for a surface type"""
    surface_types: Set[SurfaceType]
    params: List[Dict[str, Any]]


class SurfaceMeta(_ExceptionContextAdder):
    """Metaclass for creating surface classes from specifications"""

    def __new__(cls, name, bases, namespace, spec: SurfaceSpec = None, **kwargs):
        if spec is None:
            # For base classes or manual classes
            return super().__new__(cls, name, bases, namespace, **kwargs)

        # Create the class
        new_class = super().__new__(cls, name, bases, namespace, **kwargs)

        # Add surface types
        def _allowed_surface_types():
            return spec.surface_types
        new_class._allowed_surface_types = staticmethod(_allowed_surface_types)

        # Calculate number of params
        num_params = 0
        for param in spec.params:
            if param.get('is_tuple', False):
                num_params += param['tuple_length']
            else:
                num_params += 1

        def _number_of_params():
            return num_params
        new_class._number_of_params = staticmethod(_number_of_params)

        # Add __init__ method
        def __init__(self, input: InitInput = None, number: int = None, surface_type: Union[SurfaceType, str] = None):
            # Initialize nodes
            for param in spec.params:
                if param.get('is_tuple', False):
                    # Create list of nodes for tuple
                    nodes = []
                    for i in range(param['tuple_length']):
                        node = self._generate_default_node(param.get('base_type', float), None)
                        nodes.append(node)
                    setattr(self, f'_{param["name"]}', nodes)
                else:
                    # Single node
                    node = self._generate_default_node(param.get('base_type', float), None)
                    setattr(self, f'_{param["name"]}', node)

            # Call super init
            super(new_class, self).__init__(input, number, surface_type)

            # Check number of constants
            expected_params = sum(p.get('tuple_length', 1) for p in spec.params)
            if len(self.surface_constants) != expected_params:
                raise ValueError(f"{name} must have exactly {expected_params} surface constants")

            # Assign constants to nodes
            idx = 0
            for param in spec.params:
                if param.get('is_tuple', False):
                    nodes = getattr(self, f'_{param["name"]}')
                    for i in range(param['tuple_length']):
                        nodes[i] = self._surface_constants[idx]
                        idx += 1
                else:
                    setattr(self, f'_{param["name"]}', self._surface_constants[idx])
                    idx += 1

        new_class.__init__ = __init__

        # Add properties
        for param in spec.params:
            if param.get('is_tuple', False):
                # Special tuple property
                def make_tuple_property(p):
                    def getter(self):
                        nodes = getattr(self, f'_{p["name"]}')
                        return tuple(n.value for n in nodes)

                    def setter(self, value):
                        if not isinstance(value, (list, tuple)):
                            raise TypeError(f"{p['name']} must be a list or tuple")
                        if len(value) != p['tuple_length']:
                            raise ValueError(f"{p['name']} must have exactly {p['tuple_length']} elements")
                        element_types = p.get('element_types', (Real,))
                        for val in value:
                            if not isinstance(val, element_types):
                                raise TypeError(f"Elements of {p['name']} must be {element_types}")
                        nodes = getattr(self, f'_{p["name"]}')
                        for i, val in enumerate(value):
                            nodes[i].value = val

                    return property(getter, setter)

                prop = make_tuple_property(param)
                setattr(new_class, param['name'], prop)

            else:
                # Single value property
                decorator = make_prop_val_node(
                    f'_{param["name"]}',
                    param.get('types', (float, int)),
                    param.get('base_type', float),
                    param.get('validator')
                )
                # Apply decorator to a dummy function
                @decorator
                def prop_func(self):
                    pass
                setattr(new_class, param['name'], prop_func)

        # Add validate method
        def validate(self):
            super(new_class, self).validate()
            for param in spec.params:
                if param.get('is_tuple', False):
                    nodes = getattr(self, f'_{param["name"]}')
                    if any(n.value is None for n in nodes):
                        raise IllegalState(f"Surface: {self.number} does not have {param['name']} set.")
                else:
                    node = getattr(self, f'_{param["name"]}')
                    if node.value is None:
                        raise IllegalState(f"Surface: {self.number} does not have {param['name']} set.")

        new_class.validate = validate

        return new_class


# Example usage
def _enforce_positive_radius(self, value):
    if value < 0.0:
        raise ValueError(f"Radius must be positive. {value} given")

# CylinderOnAxis spec
cylinder_on_axis_spec = SurfaceSpec(
    surface_types={SurfaceType.CX, SurfaceType.CY, SurfaceType.CZ},
    params=[
        {
            'name': 'radius',
            'types': (float, int),
            'base_type': float,
            'validator': _enforce_positive_radius
        }
    ]
)

class CylinderOnAxis(Surface, metaclass=SurfaceMeta, spec=cylinder_on_axis_spec):
    """Represents surfaces: CX, CY, CZ"""
    pass

# CylinderParAxis spec
cylinder_par_axis_spec = SurfaceSpec(
    surface_types={SurfaceType.C_X, SurfaceType.C_Y, SurfaceType.C_Z},
    params=[
        {
            'name': 'coordinates',
            'is_tuple': True,
            'tuple_length': 2,
            'types': (list, tuple),
            'element_types': (float, int),
            'base_type': float
        },
        {
            'name': 'radius',
            'types': (float, int),
            'base_type': float,
            'validator': _enforce_positive_radius
        }
    ]
)

class CylinderParAxis(Surface, metaclass=SurfaceMeta, spec=cylinder_par_axis_spec):
    """Represents surfaces: C/X, C/Y, C/Z"""
    pass

# AxisPlane spec
axis_plane_spec = SurfaceSpec(
    surface_types={SurfaceType.PX, SurfaceType.PY, SurfaceType.PZ},
    params=[
        {
            'name': 'location',
            'types': (float, int),
            'base_type': float
        }
    ]
)

class AxisPlane(Surface, metaclass=SurfaceMeta, spec=axis_plane_spec):
    """Represents PX, PY, PZ"""
    pass

# GeneralSphere spec
general_sphere_spec = SurfaceSpec(
    surface_types={SurfaceType.S},
    params=[
        {
            'name': 'x',
            'types': (float, int),
            'base_type': float
        },
        {
            'name': 'y',
            'types': (float, int),
            'base_type': float
        },
        {
            'name': 'z',
            'types': (float, int),
            'base_type': float
        },
        {
            'name': 'radius',
            'types': (float, int),
            'base_type': float,
            'validator': _enforce_positive_radius
        }
    ]
)

class GeneralSphere(Surface, metaclass=SurfaceMeta, spec=general_sphere_spec):
    """Represents S"""
    pass

# SphereOnAxis spec
sphere_on_axis_spec = SurfaceSpec(
    surface_types={SurfaceType.SX, SurfaceType.SY, SurfaceType.SZ},
    params=[
        {
            'name': 'location',
            'types': (float, int),
            'base_type': float
        },
        {
            'name': 'radius',
            'types': (float, int),
            'base_type': float,
            'validator': _enforce_positive_radius
        }
    ]
)

class SphereOnAxis(Surface, metaclass=SurfaceMeta, spec=sphere_on_axis_spec):
    """Represents SX, SY, SZ"""
    pass