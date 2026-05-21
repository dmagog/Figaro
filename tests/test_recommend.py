from figaro.services.recommend import (MARATHON_TARGET, CandidateView, Prefs,
                                       filter_candidates, rank, score,
                                       weights_from)


def test_pace_relaxed():
    p = weights_from(Prefs(pace="расслабленно"))
    assert p.target_max_concerts <= 3 and p.w_comfort > 0.34


def test_pace_marathon():
    p = weights_from(Prefs(pace="марафон"))
    assert p.target_max_concerts == MARATHON_TARGET and p.hurry_tolerant


def test_interest_new_diversity_over_depth():
    p = weights_from(Prefs(interest_vector="открывать новое"))
    assert p.w_diversity > p.w_depth


def test_filter_by_day_and_window():
    cands = [CandidateView(1, day=1, window="вечер"), CandidateView(2, day=2, window="вечер"),
             CandidateView(3, day=2, window="день")]
    prof = weights_from(Prefs(available_days=(2,), time_windows=("вечер",)))
    out = filter_candidates(cands, prof)
    assert [c.id for c in out] == [2]


def test_favorites_bonus_not_filter():
    cands = [CandidateView(1, authors=frozenset({"Бах"})), CandidateView(2, authors=frozenset())]
    prof = weights_from(Prefs(favorite_authors=frozenset({"Бах"})))
    ranked = rank(cands, prof)
    assert len(ranked) == 2  # никого не отсекли
    assert score(cands[0], prof) > score(cands[1], prof)  # с Бахом — выше
