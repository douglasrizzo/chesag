from collections import OrderedDict

class BoundedDict(OrderedDict):
    def __init__(self, maxlen, *args, **kwargs):
        self.maxlen = maxlen
        super().__init__(*args, **kwargs)
    
    def __setitem__(self, key, value):
        if key in self:
            # Overwrite does not affect order
            super().__setitem__(key, value)
        else:
            if len(self) >= self.maxlen:
                self.popitem(last=False)  # Remove oldest
            super().__setitem__(key, value)