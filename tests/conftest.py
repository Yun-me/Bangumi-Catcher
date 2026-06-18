"""共享 fixtures：构造一个小型 UserCollection 供测试使用。"""
import pytest
from bangumi_catcher.models import (
    CollectionItem, RatingInfo, Subject, UserCollection,
)


def _item(sid, ctype, rate, year, score, eps=12, ep_status=12):
    subj = Subject(id=sid, name=f"Anime{sid}", name_cn=f"动画{sid}",
                   date=f"{year}-04-05", eps=eps, total_episodes=eps,
                   rating=RatingInfo(score=score))
    return CollectionItem(subject_id=sid, subject=subj, type=ctype, rate=rate,
                          ep_status=ep_status, tags=["原创"])


@pytest.fixture
def sample_collection():
    items = [
        _item(1, 2, 8, 2020, 7.5),
        _item(2, 2, 0, 2020, 8.0),   # 看过但未评分
        _item(3, 2, 6, 2021, 6.5),
        _item(4, 1, 0, 2021, 7.0),   # 想看
        _item(5, 3, 0, 2022, 8.2, ep_status=4),  # 在看
    ]
    return UserCollection(username="tester", total=len(items), items=items)
