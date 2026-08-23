from tests._util import load
survey = load("engine-prescription", "app.survey")


def test_sensitive_lowers_score():
    m = survey.survey_to_metrics({"skin_type": "sensitive",
                                  "sensitivity": {"a": True, "b": True}})
    assert m["sensitivity"]["source"] == "survey" and m["sensitivity"]["value"] <= 40


def test_non_sensitive_high_score():
    m = survey.survey_to_metrics({"skin_type": "normal"})
    assert m["sensitivity"]["value"] >= 80


def test_combination_type():
    m = survey.survey_to_metrics({"skin_type": "combination"})
    assert m["combination"]["value"] == 55.0


def test_empty_survey():
    assert survey.survey_to_metrics(None) == {}


def test_concerns():
    assert survey.survey_concerns({"concerns": ["redness", "dryness"]}) == ["redness", "dryness"]
