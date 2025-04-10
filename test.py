from montepy._abc import cow

test = cow.Moo()
test.a = 1

test2 = test.copy()
print(test2.__getattr__)
print(test2._heffer.a)
print(test2.__getattr__("a"))
test2.a 
test2.a = 2
print(test2.a)

class MooDict(cow.Moo, dict):
    pass

MooDict()
