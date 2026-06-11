import io
import unittest

from PIL import Image

from app.db.repos import users as users_repo
from app.services.avatars import AvatarError, load_avatar, process_image, save_avatar

from .db_helper import seeded_db


def png_bytes(w=800, h=600, color=(0, 200, 120)) -> bytes:
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestAvatars(unittest.TestCase):
    def test_png_vira_jpeg_quadrado_pequeno(self):
        out = process_image(png_bytes())
        img = Image.open(io.BytesIO(out))
        self.assertEqual(img.format, "JPEG")
        self.assertEqual(img.width, img.height)
        self.assertLessEqual(img.width, 256)
        self.assertNotIn("exif", img.info)

    def test_rejeita_nao_imagem(self):
        for data in (b"", b"texto qualquer", b"PK\x03\x04zipfake",
                     b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"):
            with self.assertRaises(AvatarError):
                process_image(data)

    def test_rejeita_acima_de_2mb(self):
        with self.assertRaises(AvatarError):
            process_image(b"\x89PNG" + b"0" * (2 * 1024 * 1024 + 1))

    def test_save_no_banco_e_roundtrip(self):
        conn = seeded_db()
        uid = users_repo.create(conn, "a@b.c", "Alice")
        self.assertIsNone(load_avatar(conn, uid))
        v1 = save_avatar(conn, uid, png_bytes())
        self.assertEqual(v1, 1)
        stored = load_avatar(conn, uid)
        self.assertIsInstance(stored, bytes)
        img = Image.open(io.BytesIO(stored))
        self.assertEqual(img.format, "JPEG")
        # re-upload substitui (UPSERT) e bumpa versao
        v2 = save_avatar(conn, uid, png_bytes(color=(255, 0, 0)))
        self.assertEqual(v2, 2)
        stored2 = load_avatar(conn, uid)
        self.assertNotEqual(stored, stored2)
        conn.close()


if __name__ == "__main__":
    unittest.main()
