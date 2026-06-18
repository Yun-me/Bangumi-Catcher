"""模型 computed_field 测试。"""
from bangumi_catcher.models import Subject, CollectionItem


def test_subject_year_and_season():
    s = Subject(id=1, name="x", date="2021-07-08")
    assert s.year == 2021
    assert s.season == "Q3"


def test_collection_type_name():
    it = CollectionItem(subject_id=1, type=2)
    assert it.collection_type_name == "看过"
