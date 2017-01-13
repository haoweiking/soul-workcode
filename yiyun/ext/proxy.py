

class LocalProxy(object):
    """
    Proxy class useful for situations when you wish to defer the initialization
    of an object.
    """
    __slots__ = ['_obj', '_callbacks']

    def __init__(self, obj=None):
        self.initialize(obj)

    def initialize(self, obj):
        self._obj = obj

    def __call__(self, *args, **kwargs):
        if self._obj is not None:
            return self._obj.__call__(*args, **kwargs)

    def __getattr__(self, attr):
        if self._obj is None:
            raise AttributeError('Cannot use uninitialized Proxy.')
        return getattr(self._obj, attr)

    def __setattr__(self, attr, value):

        if attr in self.__slots__:
            return super(LocalProxy, self).__setattr__(attr, value)

        if self._obj is not None:
            return setattr(self._obj, attr, value)
