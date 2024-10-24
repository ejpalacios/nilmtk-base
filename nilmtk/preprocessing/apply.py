from nilmtk.base.node import Node


class Apply(Node):
    """Apply an arbitrary function to each pd.Series chunk."""

    def __init__(self, upstream=None, generator=None, func=None):
        self.func = func
        super(Apply, self).__init__(upstream, generator)

    def process(self):
        self.check_requirements()
        for chunk in self.upstream.process():
            new_chunk = self.func(chunk)
            new_chunk.attrs["timeframe"] = chunk.attrs["timeframe"]
            if hasattr(chunk, "look_ahead"):
                new_chunk.attrs["look_ahead"] = chunk.attrs["look_ahead"]
            del chunk
            yield new_chunk
