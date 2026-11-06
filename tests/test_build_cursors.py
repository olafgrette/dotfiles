"""Check cursor scaling without a display or image-processing dependencies."""

import importlib.util
import io
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("build_cursors", ROOT / "dots-sh/build_cursors.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildCursorsTest(unittest.TestCase):
    def original(self):
        pixels = b"".join(struct.pack("<I", index) for index in range(32 * 32))
        frames = [struct.pack("<9I", 36, builder.IMAGE, 32, 1, 32, 32, 7, 19, delay) + pixels
                  for delay in (150, 300)]
        header = struct.pack("<4I", 0x72756358, 16, 0x10000, len(frames))
        offset = 16 + 12 * len(frames)
        toc = []
        for frame in frames:
            toc.append(struct.pack("<3I", builder.IMAGE, 32, offset))
            offset += len(frame)
        return header + b"".join(toc + frames)

    def test_two_times_scaling_preserves_pixels_hotspot_and_delay(self):
        frame = builder.images(self.original())[0]
        size, width, height, x, y, delay, pixels = builder.resize(frame, 64)
        self.assertEqual((size, width, height, x, y, delay), (64, 64, 64, 14, 38, 150))
        for row in range(64):
            for column in range(64):
                value = struct.unpack_from("<I", pixels, (row * 64 + column) * 4)[0]
                self.assertEqual(value, (row // 2) * 32 + column // 2)

    def test_all_sizes_preserve_animation_and_original_chunks(self):
        original = self.original()
        result = builder.upscale(original)
        count = struct.unpack_from("<I", result, 12)[0]
        self.assertEqual(count, 10)
        for index in range(count):
            kind, size, offset = struct.unpack_from("<3I", result, 16 + index * 12)
            chunk = struct.unpack_from("<9I", result, offset)
            self.assertEqual(kind, builder.IMAGE)
            self.assertEqual(size, (32, 48, 64, 96, 128)[index // 2])
            self.assertEqual(chunk[2], size)
            self.assertEqual(chunk[8], (150, 300)[index % 2])
            self.assertLess(chunk[6], chunk[4])
            self.assertLess(chunk[7], chunk[5])
            if index < 2:
                old_offset = struct.unpack_from("<3I", original, 16 + index * 12)[2]
                length = 36 + 32 * 32 * 4
                self.assertEqual(result[offset:offset + length], original[old_offset:old_offset + length])

    def test_archive_is_reproducible_and_preserves_theme_and_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "original.tar.gz"
            with tarfile.open(source, "w:gz") as tar:
                for name, content in (("broodwar/index.theme", b"[Icon Theme]\nName=broodwar\n"),
                                      ("broodwar/cursors/left_ptr", self.original())):
                    member = tarfile.TarInfo(name)
                    member.size = len(content)
                    tar.addfile(member, io.BytesIO(content))
                link = tarfile.TarInfo("broodwar/cursors/default")
                link.type = tarfile.SYMTYPE
                link.linkname = "left_ptr"
                tar.addfile(link)
            a, b = root / "a.tar.gz", root / "b.tar.gz"
            builder.build(source, a)
            builder.build(source, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with tarfile.open(a) as tar:
                self.assertEqual(tar.extractfile("broodwar/index.theme").read(), b"[Icon Theme]\nName=broodwar\n")
                self.assertEqual(tar.getmember("broodwar/cursors/default").linkname, "left_ptr")


if __name__ == "__main__":
    unittest.main()
