"""Parser tests using a real OMIE file captured on 2026-08-30
(marginalpdbc_20240115.1) — no network needed to run these."""
from app.providers.price_feed import parse_omie_marginalpdbc

REAL_OMIE_SAMPLE = """\
MARGINALPDBC;
2024;01;15;1;77.7;77.7;
2024;01;15;2;67;67;
2024;01;15;3;64.99;64.99;
2024;01;15;4;62.04;62.04;
2024;01;15;5;62.1;62.1;
2024;01;15;6;65.1;65.1;
2024;01;15;7;69.13;69.13;
2024;01;15;8;86.74;86.74;
2024;01;15;9;99.52;99.52;
2024;01;15;10;100.33;100.33;
2024;01;15;11;94.92;94.92;
2024;01;15;12;90.3;90.3;
2024;01;15;13;85.7;85.7;
2024;01;15;14;82.41;82.41;
2024;01;15;15;84.99;84.99;
2024;01;15;16;90.1;90.1;
2024;01;15;17;95.82;95.82;
2024;01;15;18;100;100;
2024;01;15;19;112.85;112.85;
2024;01;15;20;113.9;113.9;
2024;01;15;21;107.58;107.58;
2024;01;15;22;100;100;
2024;01;15;23;97.21;97.21;
2024;01;15;24;91;91;
*
"""


def test_parses_all_24_hours():
    prices = parse_omie_marginalpdbc(REAL_OMIE_SAMPLE)
    assert len(prices) == 24


def test_converts_eur_per_mwh_to_eur_per_kwh():
    prices = parse_omie_marginalpdbc(REAL_OMIE_SAMPLE)
    # Hour 1 -> 77.7 EUR/MWh -> 0.0777 EUR/kWh
    assert prices[0] == 0.0777
    # Hour 24 -> 91 EUR/MWh -> 0.091 EUR/kWh
    assert prices[23] == 0.091


def test_cheapest_and_priciest_hours_match_the_file():
    prices = parse_omie_marginalpdbc(REAL_OMIE_SAMPLE)
    assert prices.index(min(prices)) == 3  # hour 4, 62.04
    assert prices.index(max(prices)) == 19  # hour 20, 113.9


def test_raises_on_incomplete_file():
    truncated = "\n".join(REAL_OMIE_SAMPLE.splitlines()[:10])  # only ~8 hours
    try:
        parse_omie_marginalpdbc(truncated)
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("expected ValueError for an incomplete file")
