"""The expected numbers written in the SQL scripts' check queries must match the CSVs.

Each script states expectations as comment lines:  -- expect <name>: <number>
These tests recompute every number from the raw Zillow files in data/, so a
script's checks can't silently drift from the data (CONSTITUTION.md Article 4).
"""
import csv
import datetime
import functools
import re
import unittest

from tests.helpers import REPO

DATA = REPO / "data"
SQL = REPO / "sql"
ZHVI = "Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
ZORI = "Metro_zori_uc_sfrcondomfr_sm_month.csv"
INVENTORY = "Metro_invt_fs_uc_sfrcondo_sm_month.csv"
DAYS_TO_PENDING = "Metro_mean_doz_pending_uc_sfrcondo_sm_month.csv"
US_REGION_ID = "102001"


@functools.lru_cache(maxsize=None)
def zillow_long(file: str) -> dict[tuple[str, str], float]:
    """Non-blank cells of a wide Zillow CSV as {(RegionID, 'YYYY-MM-DD'): value}."""
    with open(DATA / file, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    header = rows[0]
    return {(row[0], month): float(value)
            for row in rows[1:]
            for month, value in zip(header[5:], row[5:]) if value.strip()}


@functools.lru_cache(maxsize=None)
def zillow_metros(file: str) -> dict[str, dict[str, str]]:
    """RegionID -> {RegionName, RegionType, StateName, SizeRank} for a Zillow CSV."""
    with open(DATA / file, newline="", encoding="utf-8") as handle:
        return {row["RegionID"]: row for row in csv.DictReader(handle)}


def expectations(script: str) -> dict[str, str]:
    """{name: value} from '-- expect name: value' lines in sql/<script>."""
    text = (SQL / script).read_text(encoding="utf-8")
    return dict(re.findall(r"--\s*expect\s+([a-z0-9_]+)\s*:\s*(\S+)", text))


def months_back(month: str, years: int = 1) -> str:
    """Month-end date the given number of years earlier (Zillow dates are month ends)."""
    day = datetime.date.fromisoformat(month)
    first_of_next = datetime.date(day.year - years + (day.month == 12), day.month % 12 + 1, 1)
    return (first_of_next - datetime.timedelta(days=1)).isoformat()


class LoadScriptTests(unittest.TestCase):
    def test_load_checks_match_csv(self):
        expect = expectations("01_load_zillow.sql")
        inventory = zillow_long(INVENTORY)
        last_month = max(month for _, month in inventory)
        atlanta = next(rid for rid, row in zillow_metros(INVENTORY).items() if row["RegionName"] == "Atlanta, GA")
        self.assertEqual(int(expect["inventory_rows"]), len(inventory))
        self.assertEqual(int(expect["days_to_pending_rows"]), len(zillow_long(DAYS_TO_PENDING)))
        self.assertEqual(int(expect["zhvi_rows"]), len(zillow_long(ZHVI)))
        self.assertEqual(int(expect["zori_rows"]), len(zillow_long(ZORI)))
        self.assertEqual(expect["inventory_last_month"], last_month)
        self.assertEqual(int(expect["inventory_last_month_rows"]),
                         sum(1 for _, month in inventory if month == last_month))
        self.assertEqual(float(expect["atlanta_inventory_2026_09"]), inventory[(atlanta, "2026-09-30")])

    def test_load_script_never_replaces_existing_tables(self):
        text = (SQL / "01_load_zillow.sql").read_text(encoding="utf-8")
        self.assertIn("already has data", text)
        self.assertNotRegex(text.upper(), r"DROP\s+TABLE\s+(IF\s+EXISTS\s+)?DBO\.(ZHVI_HOMEVALUE|ZORI_RENTALS|INVENTORY_FORSALE|DAYSTOPENDING)")
        self.assertNotRegex(text.upper(), r"TRUNCATE\s+TABLE")


class LoadSafetyTests(unittest.TestCase):
    """The SQL can't be run here, so these pin the safety features the final review asked for."""

    def setUp(self):
        self.text = (SQL / "01_load_zillow.sql").read_text(encoding="utf-8")

    def test_create_and_insert_happen_in_one_transaction(self):
        begin = self.text.index("BEGIN TRANSACTION")
        commit = self.text.index("COMMIT TRANSACTION")
        for step in ("EXEC sp_executesql @create;", "EXEC sp_executesql @insert;"):
            self.assertLess(begin, self.text.index(step), step)
            self.assertLess(self.text.index(step), commit, step)
        self.assertEqual(self.text.count("EXEC sp_executesql @create"), 1)
        self.assertIn("SET XACT_ABORT ON", self.text)
        self.assertIn("ROLLBACK TRANSACTION", self.text)

    def test_an_empty_leftover_table_is_reloaded_not_kept(self):
        self.assertIn("is empty", self.text)
        self.assertIn("already has data - left unchanged", self.text)

    def test_long_paths_are_not_passed_through_quotename(self):
        self.assertNotIn("QUOTENAME(@file", self.text)
        self.assertIn("@content IS NULL", self.text)

    def test_bad_rows_stop_the_load(self):
        self.assertIn("MAXERRORS = 0", self.text)

    def test_read_error_explains_access(self):
        self.assertIn("access denied", self.text.lower())


ALL_FILES = (ZHVI, ZORI, INVENTORY, DAYS_TO_PENDING)


class DimensionTests(unittest.TestCase):
    def test_dim_metro_checks_match_csv(self):
        expect = expectations("02_dim_metro.sql")
        ids = set().union(*(zillow_metros(f) for f in ALL_FILES))
        self.assertEqual(int(expect["dim_metro_rows"]), len(ids))
        self.assertEqual(int(expect["dim_metro_distinct_ids"]), len(ids))
        self.assertEqual(int(expect["metros_missing_from_dim_metro"]), 0)

    def test_metro_details_agree_across_files(self):
        """dim_metro keeps one row per metro; that is only safe if the files agree on its details."""
        for region_id in set().union(*(zillow_metros(f) for f in ALL_FILES)):
            details = {tuple(zillow_metros(f)[region_id][k] for k in ("RegionName", "RegionType", "StateName", "SizeRank"))
                       for f in ALL_FILES if region_id in zillow_metros(f)}
            self.assertEqual(len(details), 1, region_id)

    def test_dim_date_checks_match_csv(self):
        expect = expectations("03_dim_date.sql")
        months = sorted({month for f in ALL_FILES for _, month in zillow_long(f)})
        first = datetime.date(int(months[0][:4]), 1, 1)
        last = datetime.date(int(months[-1][:4]), 12, 31)
        self.assertEqual(expect["dim_date_first"], first.isoformat())
        self.assertEqual(expect["dim_date_last"], last.isoformat())
        self.assertEqual(int(expect["dim_date_days"]), (last - first).days + 1)

    def test_fact_views_use_the_database(self):
        for script in ("04_fact_home_values.sql", "05_fact_rent.sql"):
            self.assertIn("USE [Housing Data];", (SQL / script).read_text(encoding="utf-8"), script)


def pearson(pairs: list[tuple[float, float]]) -> float:
    n = len(pairs)
    sx = sum(x for x, _ in pairs)
    sy = sum(y for _, y in pairs)
    sxy = sum(x * y for x, y in pairs)
    sxx = sum(x * x for x, _ in pairs)
    syy = sum(y * y for _, y in pairs)
    return (n * sxy - sx * sy) / ((n * sxx - sx * sx) * (n * syy - sy * sy)) ** 0.5


def market_question_pairs() -> dict[str, list[tuple[float, float]]]:
    """README question 3, as 07_analysis.sql computes it: for each metro (not the US row) in the latest
    home-value month, YoY % home value change against YoY % inventory change and days-to-pending change."""
    home, inventory, days = zillow_long(ZHVI), zillow_long(INVENTORY), zillow_long(DAYS_TO_PENDING)
    latest = max(month for _, month in home)
    prior = months_back(latest)
    metros = {rid for rid, row in zillow_metros(ZHVI).items() if row["RegionType"] == "msa"}
    pairs = {"inventory": [], "days": []}
    for rid in metros:
        if (rid, latest) not in home or (rid, prior) not in home:
            continue
        home_yoy = (home[(rid, latest)] / home[(rid, prior)] - 1) * 100
        if inventory.get((rid, prior)) and (rid, latest) in inventory:
            pairs["inventory"].append((home_yoy, (inventory[(rid, latest)] / inventory[(rid, prior)] - 1) * 100))
        if (rid, prior) in days and (rid, latest) in days:
            pairs["days"].append((home_yoy, days[(rid, latest)] - days[(rid, prior)]))
    return pairs


class MarketTests(unittest.TestCase):
    def test_fact_market_checks_match_csv(self):
        expect = expectations("06_fact_market.sql")
        inventory, days = zillow_long(INVENTORY), zillow_long(DAYS_TO_PENDING)
        keys = set(inventory) | set(days)
        atlanta = next(rid for rid, row in zillow_metros(INVENTORY).items() if row["RegionName"] == "Atlanta, GA")
        self.assertEqual(int(expect["fact_market_rows"]), len(keys))
        self.assertEqual(int(expect["fact_market_rows_with_both"]), len(set(inventory) & set(days)))
        self.assertEqual(int(expect["fact_market_metros"]), len({rid for rid, _ in keys}))
        self.assertEqual(expect["fact_market_first_month"], min(month for _, month in keys))
        self.assertEqual(expect["fact_market_last_month"], max(month for _, month in keys))
        self.assertEqual(float(expect["atlanta_inventory_2026_09"]), inventory[(atlanta, "2026-09-30")])
        self.assertEqual(float(expect["atlanta_days_to_pending_2026_09"]), days[(atlanta, "2026-09-30")])

    def test_q10_correlations_match_csv(self):
        expect = expectations("07_analysis.sql")
        pairs = market_question_pairs()
        self.assertEqual(int(expect["q10_metros_inventory"]), len(pairs["inventory"]))
        self.assertEqual(int(expect["q10_metros_days"]), len(pairs["days"]))
        self.assertAlmostEqual(float(expect["q10_corr_home_vs_inventory"]), pearson(pairs["inventory"]), places=3)
        self.assertAlmostEqual(float(expect["q10_corr_home_vs_days"]), pearson(pairs["days"]), places=3)

    def test_dax_has_market_measures(self):
        dax = (REPO / "powerbi" / "core_measures.dax").read_text(encoding="utf-8")
        self.assertIn("Avg Inventory = AVERAGE ( fact_market[inventory] )", dax)
        self.assertIn("Avg Days to Pending = AVERAGE ( fact_market[days_to_pending] )", dax)


if __name__ == "__main__":
    unittest.main()
