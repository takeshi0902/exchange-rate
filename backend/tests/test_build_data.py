"""
build_data 離線測試（不連線銀行）。
執行：python -m unittest discover -s backend/tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_data as BD                      # noqa: E402
from scrapers.base import currency_code, to_float  # noqa: E402


def bank(code, **rates):
    return {"bank_code": code, "bank_name": code, "rates": {c: dict(r) for c, r in rates.items()}}


USD = {"spot_buy": 32.3, "spot_sell": 32.4}


class TestSanity(unittest.TestCase):
    def test_inverted_quote_removed(self):
        b = bank("X", JPY={"spot_buy": 0.21, "spot_sell": 0.20, "cash_buy": 0.19, "cash_sell": 0.22})
        problems = BD.drop_inverted(b)
        self.assertEqual(len(problems), 1)
        self.assertEqual(b["rates"]["JPY"], {"cash_buy": 0.19, "cash_sell": 0.22})

    def test_outlier_removed(self):
        # 曾發生：台新「黃金XAU(USD)」被誤判為美元，即期變成 4145
        banks = [bank("A", USD=USD), bank("B", USD=USD), bank("C", USD=USD),
                 bank("BAD", USD={"spot_buy": 4145.13, "spot_sell": 4185.89})]
        problems = BD.drop_outliers(banks)
        self.assertEqual(len(problems), 2)
        self.assertNotIn("USD", banks[3]["rates"])
        self.assertEqual(banks[0]["rates"]["USD"], USD)

    def test_outlier_needs_three_banks(self):
        banks = [bank("A", USD=USD), bank("BAD", USD={"spot_buy": 4145.0, "spot_sell": 4185.0})]
        self.assertEqual(BD.drop_outliers(banks), [])


class TestOutput(unittest.TestCase):
    def test_rates_json_shape(self):
        latest = {"A": bank("A", USD=USD, JPY={"spot_buy": 0.2, "spot_sell": 0.21}) | {"updated_at": "T"}}
        out = BD.build_rates_json(latest, "NOW")
        r = out["rates"][0]
        self.assertEqual(r["bank"], "A")                 # 前端以 b.bank 顯示
        self.assertEqual(r["USD"]["updated_at"], "T")    # 失敗沿用舊資料時保留原時間
        self.assertIsNone(r["USD"]["cash_sell"])
        self.assertEqual(out["usd_jpy"], round(32.4 / 0.21, 2))


class TestParsing(unittest.TestCase):
    def test_currency_code(self):
        cases = {"黃金XAU(USD)": None, "黃金XAU(TWD)": None, "美元USD": "USD", "日圓 (JPY)": "JPY",
                 "美金現鈔 (USD-C)": "USD", "日元": "JPY", "泰國銖": "THB", "USD|01": "USD"}
        for text, expected in cases.items():
            self.assertEqual(currency_code(text), expected, text)

    def test_to_float(self):
        self.assertEqual(to_float("0.2030 近30日最高"), 0.203)
        self.assertEqual(to_float("31,475"), 31475.0)
        self.assertIsNone(to_float("--"))
        self.assertIsNone(to_float("0"))


if __name__ == "__main__":
    unittest.main()
