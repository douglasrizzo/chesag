"""Small supporting data structures."""

from collections import OrderedDict


class BoundedDict(OrderedDict):
  """Ordered dictionary with a maximum number of entries."""

  def __init__(self, maxlen: int, *args: object, **kwargs: object) -> None:
    """Initialize a bounded ordered dictionary."""
    self.maxlen = maxlen
    super().__init__(*args, **kwargs)

  def __setitem__(self, key: object, value: object) -> None:
    """Insert an item, evicting the oldest entry when full."""
    if key in self:
      # Overwrite does not affect order
      super().__setitem__(key, value)
    else:
      if len(self) >= self.maxlen:
        self.popitem(last=False)  # Remove oldest
      super().__setitem__(key, value)
