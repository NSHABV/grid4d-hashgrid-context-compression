"""Independent transport tests; no entropy engine or production targets."""
import struct
import unittest

import numpy as np

from research.experiment_bench.hashed_interlevel import dry_model as dm
from research.experiment_bench.models import frequencies


class DryModelTests(unittest.TestCase):
    def fixture(self, classes=10):
        f = np.full((2, classes, 256), 256, dtype=np.uint32)
        # Positive maximum mass allowed by the other 255 mandatory symbols.
        f[0, 0] = 1
        f[0, 0, 255] = 65281
        f[1, 0, :128] = 255
        f[1, 0, 128:] = 257  # A modal tie; choose the smaller default.
        if classes > 1:
            f[0, 1] = frequencies(np.arange(256))
        edges = {
            "mean": np.array([[0., -0., 0., 1., 1., 1., 2.],
                              [-3., -2., -1., 0., 1., 2., 3.]], dtype=np.float64),
            "empty": np.empty((2, 0), dtype=np.float64),
            "std": np.array([np.nextafter(0., 1.), np.finfo(np.float64).max]),
        }
        return f, edges, {"model": "test", "classes": classes}, {"seed": 1, "axes": [0, 1, 2]}

    def encoded(self, storage="dense_u32", classes=10):
        return dm.serialize(*self.fixture(classes), storage)

    def replace_section(self, data, index, new):
        parts, _, _ = dm._parts(data)
        parts[index] = new
        fields = list(dm.HEADER.unpack_from(data))
        fields[6:] = [len(part) for part in parts]
        return dm.HEADER.pack(*fields) + b"".join(parts)

    def test_all_classes_and_storages_exact_roundtrip(self):
        for classes in dm.CLASS_COUNTS:
            for storage in dm.STORAGES:
                with self.subTest(classes=classes, storage=storage):
                    f, edges, spec, meta = self.fixture(classes)
                    data = dm.serialize(f, edges, spec, meta, storage)
                    got, actual, actual_spec, actual_meta = dm.deserialize(data)
                    self.assertEqual(got.dtype, np.uint32)
                    np.testing.assert_array_equal(f, got)
                    for key in edges:
                        self.assertEqual(edges[key].shape, actual[key].shape)
                        self.assertEqual(edges[key].tobytes(), actual[key].tobytes())
                    self.assertEqual(spec, actual_spec)
                    self.assertEqual(meta, actual_meta)
                    self.assertEqual(data, dm.serialize(got, actual, actual_spec, actual_meta, storage))
                    self.assertTrue(np.all(np.cumsum(got, axis=2, dtype=np.uint64)[..., -1] == 65536))

    def test_measured_sections_add_to_actual_length(self):
        for storage in dm.STORAGES:
            data = self.encoded(storage)
            sizes = dm.section_sizes(data)
            self.assertEqual(sizes["total"], len(data))
            self.assertEqual(sum(v for k, v in sizes.items() if k != "total"), len(data))
            self.assertEqual(sizes["header"], 26)
        self.assertEqual(dm.section_sizes(self.encoded())["probability_masses"], 2 * 10 * 256 * 4)
        self.assertEqual(dm.section_sizes(self.encoded("packed_u16"))["probability_masses"], 2 * 10 * 256 * 2)

    def test_uniform_rows_are_present_not_omitted(self):
        for classes in dm.CLASS_COUNTS:
            f = np.full((2, classes, 256), 256, dtype=np.uint32)
            data = dm.serialize(f, {}, {}, {}, "sparse_default_u16")
            parts, _, _ = dm._parts(data)
            self.assertEqual(parts[0], struct.pack("<HH", 256, 0) * 2 * classes)
            np.testing.assert_array_equal(dm.deserialize(data)[0], f)

    def test_sparse_tie_chooses_smallest_mass(self):
        f = np.full((2, 1, 256), 255, dtype=np.uint32)
        f[:, :, 128:] = 257
        parts, _, _ = dm._parts(dm.serialize(f, {}, {}, {}, "sparse_default_u16"))
        self.assertEqual(struct.unpack_from("<HH", parts[0]), (255, 128))

    def test_invalid_mass_inputs(self):
        f, edges, spec, meta = self.fixture()
        for bad in (f.astype(np.uint16), f.astype(np.float64), f[:, :3], f[0]):
            with self.assertRaises(ValueError):
                dm.serialize(bad, edges, spec, meta, "dense_u32")
        for value in (0, 65536, np.iinfo(np.uint32).max):
            bad = f.copy()
            bad[0, 0, 0] = value
            with self.assertRaises(ValueError):
                dm.serialize(bad, edges, spec, meta, "dense_u32")

    def test_invalid_threshold_inputs(self):
        f, _, spec, meta = self.fixture()
        for bad in ({"x": np.array([np.nan])}, {"x": np.array([np.inf])},
                    {"x": np.array([1.], dtype=np.float32)}, {"": np.array([1.])},
                    {"x": np.zeros((1,) * 9)}, {"x": np.zeros(65537)}):
            with self.assertRaises(ValueError):
                dm.serialize(f, bad, spec, meta, "dense_u32")

    def test_json_canonical_order_and_restrictions(self):
        f, edges, _, _ = self.fixture()
        a = dm.serialize(f, edges, {"b": 2, "a": 1}, {"а": True}, "dense_u32")
        b = dm.serialize(f, dict(reversed(list(edges.items()))), {"a": 1, "b": 2}, {"а": True}, "dense_u32")
        self.assertEqual(a, b)
        for invalid in ({1: "a"}, {"nan": float("nan")}, {"tuple": (1, 2)}, []):
            with self.assertRaises(ValueError):
                dm.serialize(f, {}, invalid, {}, "dense_u32")

    def test_header_versions_bounds_and_trailing(self):
        data = self.encoded()
        for index, value in ((0, b"NOPE"), (1, 2), (2, 4), (3, 1), (4, 9), (5, 255), (6, 1 << 30)):
            fields = list(dm.HEADER.unpack_from(data))
            fields[index] = value
            with self.assertRaises(ValueError):
                dm.deserialize(dm.HEADER.pack(*fields) + data[dm.HEADER.size:])
        with self.assertRaises(ValueError):
            dm.deserialize(data + b"x")

    def test_every_truncation_rejected(self):
        for storage in dm.STORAGES:
            data = self.encoded(storage, 1)
            for n in range(len(data)):
                with self.assertRaises(ValueError):
                    dm.deserialize(data[:n])

    def test_malformed_dense_mass_cdf(self):
        data = self.encoded()
        parts, _, _ = dm._parts(data)
        bad = bytearray(parts[0])
        struct.pack_into("<I", bad, 0, 0)
        with self.assertRaises(ValueError):
            dm.deserialize(self.replace_section(data, 0, bytes(bad)))

    def test_malformed_sparse_rows(self):
        data = self.encoded("sparse_default_u16")
        parts, _, _ = dm._parts(data)
        for prefix in (struct.pack("<HH", 0, 1), struct.pack("<HH", 1, 256),
                       struct.pack("<HHBH", 1, 1, 255, 1),
                       struct.pack("<HHBH", 1, 1, 255, 0)):
            with self.assertRaises(ValueError):
                dm.deserialize(self.replace_section(data, 0, prefix + parts[0][len(prefix):]))
        # Build all-valid totals but deliberately choose the larger tied mode.
        row = struct.pack("<HH", 257, 128) + b"".join(struct.pack("<BH", x, 255) for x in range(128))
        f = np.full((2, 1, 256), 256, dtype=np.uint32)
        uniform = dm.serialize(f, {}, {}, {}, "sparse_default_u16")
        with self.assertRaises(ValueError):
            dm.deserialize(self.replace_section(uniform, 0, row * 2))

    def test_duplicate_and_unsorted_sparse_symbols(self):
        data = self.encoded("sparse_default_u16")
        parts, _, _ = dm._parts(data)
        # First row becomes two exceptions with identical symbol IDs.
        malformed = struct.pack("<HHBHBH", 1, 2, 255, 10, 255, 65272) + parts[0][7:]
        with self.assertRaises(ValueError):
            dm.deserialize(self.replace_section(data, 0, malformed))

    def test_malformed_threshold_sections(self):
        data = self.encoded()
        for section in (b"", struct.pack("<H", 65), struct.pack("<HH", 1, 0),
                        struct.pack("<HH", 1, 1) + b"x" + bytes([9]),
                        struct.pack("<HH", 1, 1) + b"x" + bytes([1]) + struct.pack("<I", 65537),
                        struct.pack("<HH", 1, 1) + b"x" + bytes([1]) + struct.pack("<I", 1) + struct.pack("<d", float("nan")),
                        struct.pack("<H", 0) + b"extra"):
            with self.assertRaises(ValueError):
                dm.deserialize(self.replace_section(data, 1, section))

    def test_malformed_json_sections(self):
        data = self.encoded()
        for section in (b'{"a":1,"a":2}', b'{"x":NaN}', b'{ "a": 1 }', b'[]', b'\xff', b'{'):
            with self.assertRaises(ValueError):
                dm.deserialize(self.replace_section(data, 2, section))

    def test_no_input_mutation(self):
        f, edges, spec, meta = self.fixture()
        before = f.tobytes(), {key: value.tobytes() for key, value in edges.items()}
        for storage in dm.STORAGES:
            dm.serialize(f, edges, spec, meta, storage)
        self.assertEqual(before, (f.tobytes(), {key: value.tobytes() for key, value in edges.items()}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
