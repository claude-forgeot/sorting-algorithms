from algorithms.selection_sort import selection_sort


def test_empty():
    assert selection_sort([]) == []


def test_single_element():
    assert selection_sort([42]) == [42]


def test_already_sorted(already_sorted):
    assert selection_sort(already_sorted) == already_sorted


def test_reverse_sorted(reverse_sorted):
    assert selection_sort(reverse_sorted) == sorted(reverse_sorted)


def test_with_duplicates(with_duplicates):
    assert selection_sort(with_duplicates) == sorted(with_duplicates)


def test_matches_sorted(unsorted):
    assert selection_sort(unsorted) == sorted(unsorted)


def test_callback_called(unsorted):
    events = []
    selection_sort(
        unsorted, on_step=lambda arr, i, j, event_type: events.append(event_type)
    )
    assert "compare" in events
    assert "swap" in events
