"""Static histograms with a separate decoder-available context/order interface."""
import numpy as np

PRECISION = 16
TOTAL = 1 << PRECISION
ALPHABET = 256


def frequencies(counts):
    """Laplace + deterministic largest-remainder normalization, minimum mass=1."""
    c = np.asarray(counts, dtype=np.float64)
    if c.shape != (256,) or np.any(c < 0) or not np.isfinite(c).all():
        raise ValueError('Invalid histogram')
    p = (c + 1.) / (c.sum() + 256.)
    scaled = p * (TOTAL - 256)
    floor = np.floor(scaled)
    freq = floor.astype(np.uint32) + 1
    remainder = TOTAL - int(freq.sum())
    order = np.argsort(-(scaled-floor), kind='stable')
    freq[order[:remainder]] += 1
    validate_frequencies(freq[None, :])
    return freq


def validate_frequencies(freq):
    if (freq.ndim != 2 or freq.shape[1] != 256 or not np.issubdtype(freq.dtype, np.integer)
            or np.any(freq < 1) or np.any(freq.astype(np.uint64).sum(axis=1) != TOTAL)):
        raise ValueError('Invalid finite histogram/CDF')


def context_class(first):
    """No access to q1, floats, level coordinates, or future symbols."""
    x = np.asarray(first)
    if x.dtype != np.uint8 or x.ndim != 1:
        raise ValueError('Context accepts only decoded uint8 q0')
    return np.right_shift(x, 4)


class HistogramModel:
    """Implementations supply plan_second(q0), fit, and serializable distributions."""
    name = 'iid'
    distributions = 2

    def __init__(self, freq, metadata=None):
        self.freq = np.asarray(freq, dtype=np.uint32)
        self.metadata = metadata
        if self.freq.shape != (self.distributions, 256):
            raise ValueError('Model shape mismatch')
        validate_frequencies(self.freq)

    @classmethod
    def fit(cls, symbols, metadata=None):
        hist = [np.bincount(symbols[:, 0], minlength=256)]
        provisional = cls(np.full((cls.distributions, 256), 256, dtype=np.uint32), metadata)
        for distribution, indices in provisional.plan_second(symbols[:, 0]):
            hist.append(np.bincount(symbols[indices, 1], minlength=256))
        return cls(np.stack([frequencies(h) for h in hist]), metadata)

    def plan_second(self, decoded_first):
        # Common IID order: all q0 rows, then all q1 rows in original row order.
        context_class(decoded_first)  # validates decoder-side dtype/domain
        return [(1, np.arange(decoded_first.size))]

    def distribution(self, index):
        return self.freq[index].astype(np.float32) / TOTAL

    def to_bytes(self):
        return self.freq.astype('<u4').tobytes()

    @classmethod
    def from_bytes(cls, data, metadata=None):
        if len(data) != cls.distributions * 256 * 4:
            raise ValueError('Model byte length mismatch')
        return cls(np.frombuffer(data, dtype='<u4').reshape(cls.distributions, 256).copy(), metadata)


class ChannelContext(HistogramModel):
    name = 'channel_context'
    distributions = 17

    def plan_second(self, decoded_first):
        classes = context_class(decoded_first)
        # Stable row order within each class; class traversal 0..15 is public.
        return [(c+1, np.flatnonzero(classes == c)) for c in range(16)]


MODELS = {'iid': HistogramModel, 'channel_context': ChannelContext}
