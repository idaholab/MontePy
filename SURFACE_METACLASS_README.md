# Surface Metaclass Prototype

This is a prototype metaclass for automatically generating MontePy surface classes based on specifications.

## Overview

The `SurfaceMeta` metaclass allows creating surface classes by providing a `SurfaceSpec` that defines:
- Which surface types the class handles
- What parameters the surface has
- Properties for each parameter (types, validators, etc.)

## SurfaceSpec

A `SurfaceSpec` is created with:
- `surface_types`: Set of `SurfaceType` enums
- `params`: List of parameter dictionaries

Each parameter dict can have:
- `name`: Property name
- `types`: Tuple of acceptable types for setter
- `base_type`: Type to convert to
- `validator`: Validation function
- `is_tuple`: True if parameter is a tuple of values
- `tuple_length`: Number of elements in tuple
- `element_types`: Types for tuple elements

## Examples

### Simple parameter (CylinderOnAxis)
```python
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
```

### Tuple parameter (CylinderParAxis)
```python
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
```

## Generated Features

For each spec, the metaclass generates:
- `_allowed_surface_types()` static method
- `_number_of_params()` static method
- `__init__()` method that initializes parameter nodes
- Properties for each parameter using `make_prop_val_node`
- `validate()` method that checks all parameters are set

## Usage

```python
class MySurface(Surface, metaclass=SurfaceMeta, spec=my_spec):
    pass

surf = MySurface(number=1, surface_type=SurfaceType.SOME_TYPE)
surf.param1 = value1
surf.param2 = value2
surf.validate()  # Checks all params are set
```

## Integration into MontePy

To integrate this into MontePy:

1. Move `SurfaceMeta` and `SurfaceSpec` to `montepy/surfaces/`
2. Create specs for all surface types from Table 5.1
3. Update `surface_builder.py` to use the new classes
4. Ensure backward compatibility

## Benefits

- Eliminates repetitive code for surface classes
- Consistent property interfaces
- Easy to add new surface types
- Automatic validation and type checking

## Limitations

- `find_duplicate_surfaces` not implemented (would need spec extension)
- Special coordinate mappings (like COORDINATE_PAIRS) not handled
- Complex surfaces may need manual implementation</content>
<parameter name="filePath">/home/mgale/dev/montepy/SURFACE_METACLASS_README.md