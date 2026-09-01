"""Golden-path tests: each supplied sample policy resolves to the expected
OD/TP commission with an evidence-backed trace."""
import pytest

CASES = {
    "pvt-car-comprehensive-hdfc-ergo": dict(
        insurer="HDFC ERGO", status="resolved",
        od=(True, 15.0), tp=(True, 0.0),
        cite_contains="page 1",
    ),
    "pvt-car-comprehensive-reliance": dict(
        insurer="Reliance", status="resolved",
        od=(True, 17.5), tp=(True, 0.0),
        cite_contains="PRIVATE CAR COMP, SAOD & STP!",
    ),
    "pvt-car-satp-go-digit": dict(
        insurer="Go Digit", status="resolved",
        od=(False, None), tp=(True, 29.5),
        cite_contains="4W SATP!E293",
    ),
    "pvt-car-satp-tata-aig": dict(
        insurer="Tata AIG", status="resolved",
        od=(False, None), tp=(True, 38.0),
        cite_contains="Pvtcar!V527",
    ),
}


@pytest.mark.parametrize("name,exp", CASES.items())
def test_sample_policy_resolves(analyze, name, exp):
    out = analyze(name)
    assert out["status"] == exp["status"]
    assert out["insurer"] == exp["insurer"]
    assert out["rates"]["od"]["applicable"] is exp["od"][0]
    assert out["rates"]["od"]["percent"] == exp["od"][1]
    assert out["rates"]["tp"]["applicable"] is exp["tp"][0]
    assert out["rates"]["tp"]["percent"] == exp["tp"][1]
    # every decision is traced and cited
    assert len(out["trace"]) >= 3
    all_locators = " ".join(c["locator"] for c in out["citations"])
    assert exp["cite_contains"] in all_locators
    # a resolved result must cite the grid file for the final rate
    assert any(c["kind"] in ("xlsx", "pdf") for c in out["citations"])


def test_standalone_tp_reports_od_not_applicable(analyze):
    for name in ("pvt-car-satp-go-digit", "pvt-car-satp-tata-aig"):
        od = analyze(name)["rates"]["od"]
        assert od["applicable"] is False
        assert od["percent"] is None  # not 0%


def test_comprehensive_reports_both_components(analyze):
    for name in ("pvt-car-comprehensive-hdfc-ergo", "pvt-car-comprehensive-reliance"):
        rates = analyze(name)["rates"]
        assert rates["od"]["applicable"] and rates["tp"]["applicable"]


def test_reliance_sub_1000cc_footnote_applied(analyze):
    out = analyze("pvt-car-comprehensive-reliance")
    titles = [s["title"] for s in out["trace"]]
    assert any("1000 cc" in t or "1000cc" in t for t in titles)
    # 22.5 base - 5 = 17.5
    assert out["rates"]["od"]["percent"] == 17.5


def test_commission_amounts_when_premium_present(analyze):
    out = analyze("pvt-car-satp-go-digit")
    assert out["commission_amounts_inr"]["tp"] == pytest.approx(3466 * 0.295, rel=1e-3)
