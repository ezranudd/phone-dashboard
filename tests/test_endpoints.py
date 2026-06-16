"""Fast endpoint + data-contract tests (no browser needed).

Complements verify_charts.py (the browser render gate) with sub-second checks
that the JSON the frontend depends on is present, well-formed, and sane. Model
outputs are deterministic because main.py fixes random_state=42 everywhere.

Run from the repo root:  python -m pytest
"""
import main
import pytest


@pytest.fixture(scope="module")
def client():
    main.app.config["TESTING"] = True
    return main.app.test_client()


def test_home_ok(client):
    assert client.get("/").status_code == 200


def test_browse_json_is_list(client):
    r = client.get("/browse.json")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list) and len(data) > 0


# --- /data/charts.json (descriptive payload) ---

def test_charts_json_contract(client):
    r = client.get("/data/charts.json")
    assert r.status_code == 200
    d = r.get_json()  # implicitly asserts valid JSON (catches numpy-type regressions)
    for key in ("brand_counts", "os_counts", "battery_type_counts", "video_formats",
                "avg_price_by_brand", "correlation", "yearly_trends",
                "price_by_os", "histograms"):
        assert key in d, f"missing key: {key}"
    # Rare operating systems are bucketed into "Other".
    assert "Other" in d["os_counts"]
    # The boxplot's OS set must match the pie's major-OS set (no drift).
    assert set(d["price_by_os"]) == {k for k in d["os_counts"] if k != "Other"}


def test_correlation_matrix_square(client):
    d = client.get("/data/charts.json").get_json()
    labels, matrix = d["correlation"]["labels"], d["correlation"]["matrix"]
    assert len(matrix) == len(labels)
    assert all(len(row) == len(labels) for row in matrix)


# --- /data/insights.json (modeling payload) ---

@pytest.fixture(scope="module")
def insights(client):
    r = client.get("/data/insights.json")
    assert r.status_code == 200
    return r.get_json()


def test_insights_top_level_keys(insights):
    for key in ("price_model", "value_ranking", "tiers"):
        assert key in insights


def test_price_model_metrics_sane(insights):
    m = insights["price_model"]["metrics"]
    for name in ("linear", "random_forest"):
        r2 = m[name]["r2"]
        assert 0.0 < r2 < 1.0, f"{name} R^2 out of range: {r2}"
        assert m[name]["mae"] > 0
    # Importances are non-negative and roughly normalized (RF feature_importances_).
    imp = insights["price_model"]["importance"]
    assert imp == sorted(imp, key=lambda x: x["importance"], reverse=True)
    assert abs(sum(f["importance"] for f in imp) - 1.0) < 0.05


def test_value_ranking_ordered(insights):
    best = insights["value_ranking"]["best"]
    assert len(best) == 15
    residuals = [p["residual"] for p in best]
    assert residuals == sorted(residuals, reverse=True)
    # "Best value" = priced below prediction, so the top residual is positive.
    assert best[0]["residual"] > 0


def test_tiers_price_ordered(insights):
    summary = insights["tiers"]["summary"]
    assert [t["tier"] for t in summary] == ["Budget", "Mid-range", "Flagship"]
    prices = [t["mean_price"] for t in summary]
    assert prices == sorted(prices), f"tiers not price-ordered: {prices}"
    # Scatter point arrays are aligned and cover the dataset.
    pts = insights["tiers"]["points"]
    assert len(pts["storage"]) == len(pts["price"]) == len(pts["tier"])
