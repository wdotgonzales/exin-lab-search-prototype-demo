from app.ingest.lab_ids import LabId, find_lab_ids, normalise


def test_finds_each_kind():
    found = find_lab_ids("Mouse M-042 got virus V-003 in EXP-007, cohort C-12.")
    assert found == {
        LabId("M-042", "mouse"): 1,
        LabId("V-003", "virus_batch"): 1,
        LabId("EXP-007", "experiment"): 1,
        LabId("C-12", "cohort"): 1,
    }


def test_spellings_are_normalised_and_counted():
    found = find_lab_ids("m-42, M-042, M_042 and M\u2013042 are all the same mouse")
    assert found == {LabId("M-042", "mouse"): 4}


def test_padding_rules():
    assert normalise("exp", "7").code == "EXP-007"
    assert normalise("C", "3").code == "C-03"
    assert normalise("M", "1234").code == "M-1234"  # never truncated


def test_ignores_lookalikes():
    text = "ABC-12, M-0421a, M42, item-M, PM-100, version 3-1"
    assert find_lab_ids(text) == {}


def test_empty_text():
    assert find_lab_ids("") == {}
