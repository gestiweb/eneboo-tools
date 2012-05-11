import re
def parsers():
    import parsers
    return dict([ (x[4:],y) for x,y in parsers.__dict__.iteritems() if x[:4] == "get_" ])

def get_int(x):
    if type(x) is int: return x
    x = str(x)
    if not re.match("-?[0-9]+$",x): raise ValueError, "value %s is not a integer" % repr(x)
    return int(x)

def get_float(x):
    if type(x) is int: return x
    x = str(x)
    if not re.match("[0-9\.]+$",x): raise ValueError, "value %s is not a float" % repr(x)
    return float(x)

def get_hostname(x):
    x = get_string(x)
    if not re.match("[a-z0-9\.]+$",x): raise ValueError, "value %s is not a valid hostname" % repr(x)
    return x

def get_identifier(x):
    if x == "None" or x is None: return None
    x = get_string(x)
    if not re.match("\w+$",x): raise ValueError, "value %s is not a valid identifier" % repr(x)
    return x
    
def get_ipaddress(x):
    x = get_hostname(x)
    vx = x.split(".")
    if len(vx) != 4: raise ValueError, "value %s is not a valid ipaddress" % repr(x)
    for v in vx:
        try: v = int(v)
        except ValueError:
            raise ValueError, "value %s is not a ipaddress" % repr(x)
        if v < 0 or v > 255: raise ValueError, "value %s is not a valid ipaddress" % repr(x)
    return x
    
def get_string(x):
    if not isinstance(x, basestring): raise ValueError, "value %s is not a string" % repr(x)
    return str(x)

def get_bool(x):
    if isinstance(x, basestring):
        x = x.lower()
        if x[0] == "y": return True
        if x[0] == "t": return True
        if x[0] == "f": return False
        if x[0] == "n": return False
        raise ValueError, "Unknown boolean value <%s>" % x
    else:
        return bool(x) 
    
def get_commaStringList(x):
    if type(x) is list: return x
    x = get_string(x)
    return x.split(",")


def get_stringList(x):
    if type(x) is list: return x
    x = get_string(x)
    x = x.split("\n")
    x = [ y.strip() for y in x if y.strip() ]
    return x
