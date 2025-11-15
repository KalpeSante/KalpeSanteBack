from .development import *
from .production import *   
if DEBUG:
    from .development import *
    print("Development settings are enabled")
else:
    from .production import *
    print("Production settings are enabled")