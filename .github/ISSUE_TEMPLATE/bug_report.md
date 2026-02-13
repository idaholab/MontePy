---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bugs
type: Bug
assignees: ''

---
<!--
**Reminders**
1. This is not a place to debug your MCNP models
1. MCNP is export controlled and only its 6.2 and 6.3 user manuals are public. Don't include any information about MCNP which is not in those manuals.
1. Your model may be export controlled, or proprietary. Please change specific numbers (e.g., dimensions, material compositions, etc.) in your minimum working examples. -->

## Bug Description

<!-- A clear and concise description of what the bug is. -->

## To Reproduce

<!-- A short code snippet of what you have ran. Please change or remove any specific values or anything that can't be public. For example: --> 

``` python
problem = montepy.read_input("foo.imcnp")
```

## Error Message 

<!-- If an error message was printed please include the entire stacktrace. If it includes any specific values please change or remove them. For example: -->

<details open> 

``` python
In [6]: problem.cells.append(copy.deepcopy(cell))
---------------------------------------------------------------------------
NumberConflictError                       Traceback (most recent call last)
Cell In[6], line 1
----> 1 problem.cells.append(copy.deepcopy(cell))

File ~/dev/montepy/montepy/numbered_object_collection.py:202, in NumberedObjectCollection.append(self, obj)
    200     raise TypeError(f"object being appended must be of type: {self._obj_class}")
    201 if obj.number in self.numbers:
--> 202     raise NumberConflictError(
    203         (
    204             "There was a numbering conflict when attempting to add "
    205             f"{obj} to {type(self)}. Conflict was with {self[obj.number]}"
    206         )
    207     )
    208 else:
    209     self.__num_cache[obj.number] = obj

NumberConflictError: There was a numbering conflict when attempting to add CELL: 3, mat: 3, DENS: 1.0 g/cm3 to <class 'montepy.cells.Cells'>. Conflict was with CELL: 3, mat: 3, DENS: 1.0 g/cm3
```

</details>

## MCNP input file snippet

<!-- If applicable, please include a small section of the input file you were working on. If it includes any specific values please change or remove them. For example: -->

```
Example MCNP Input File
C cells
1 1 20
         -999  $ dollar comment
        imp:n,p=1 $U=350 
        trcl=5
2 0     #1  imp:n,p=0

C surfaces
999 SO 1

C data
C materials
C UO2 5 atpt enriched
m1        92235.80c           5 &
92238.80c          95
c transforms
*tr5  0.0  0.0  1.0 
c run parameters
ksrc  0.0  0.0  1.0
kcode 100 0.1 1 11

Stuff that comes after the data block ignored by MCNP
```

## Version

 - Version [e.g. 0.2.5]

## Additional context

Add any other context about the problem here.
