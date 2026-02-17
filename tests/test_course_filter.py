from course_filter import should_include_course, filter_course_list


def test_coen_included():
    assert should_include_course("COEN", "311") is True
    assert should_include_course("COEN", "212") is True


def test_elec_included():
    assert should_include_course("ELEC", "273") is True
    assert should_include_course("ELEC", "311") is True


def test_elec_excluded():
    for catalog in ["430", "434", "436", "438", "443", "446", "498"]:
        assert should_include_course("ELEC", catalog) is False


def test_engr_290_included():
    assert should_include_course("ENGR", "290") is True


def test_engr_other_excluded():
    assert should_include_course("ENGR", "301") is False


def test_random_subject_excluded():
    assert should_include_course("MATH", "201") is False
    assert should_include_course("COMP", "353") is False


def test_filter_course_list():
    courses = [
        {"subject": "COEN", "catalog": "311"},
        {"subject": "MATH", "catalog": "201"},
        {"subject": "ELEC", "catalog": "273"},
    ]
    filtered, excluded_count = filter_course_list(courses, "subject", "catalog")
    assert len(filtered) == 2
    assert excluded_count == 1
