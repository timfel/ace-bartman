def cache_decorator(func):
    def wrapper(self):
        if not hasattr(self, "_cache"):
            self._cache = {}
        result = self._cache.get(func, None)
        if not result:
            result = self._cache[func] = func(self)
        return result
    return wrapper
