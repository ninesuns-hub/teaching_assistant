import unittest

from app.core.validators import is_valid_tongji_email


class TongjiEmailValidatorTests(unittest.TestCase):
    def test_accepts_supported_tongji_email_local_parts(self):
        valid_addresses = (
            "2452808@tongji.edu.cn",
            "teacher.name@tongji.edu.cn",
            "department-user@tongji.edu.cn",
            "  Teacher.Name@TONGJI.EDU.CN  ",
        )

        for address in valid_addresses:
            with self.subTest(address=address):
                self.assertTrue(is_valid_tongji_email(address))

    def test_rejects_invalid_or_deceptive_addresses(self):
        invalid_addresses = (
            "@tongji.edu.cn",
            "user@example.com",
            "user@sub.tongji.edu.cn",
            "user@tongji.edu.cn.example.com",
            "user name@tongji.edu.cn",
            "user@name@tongji.edu.cn",
        )

        for address in invalid_addresses:
            with self.subTest(address=address):
                self.assertFalse(is_valid_tongji_email(address))


if __name__ == "__main__":
    unittest.main()
