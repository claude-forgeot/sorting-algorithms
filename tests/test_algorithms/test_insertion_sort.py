from algorithms.insertion_sort import insertion_sort


def test_empty():
    assert insertion_sort([]) == []


def test_single_element():
    assert insertion_sort([42]) == [42]


def test_already_sorted(already_sorted):
    assert insertion_sort(already_sorted) == already_sorted


def test_reverse_sorted(reverse_sorted):
    assert insertion_sort(reverse_sorted) == sorted(reverse_sorted)


def test_with_duplicates(with_duplicates):
    assert insertion_sort(with_duplicates) == sorted(with_duplicates)


def test_matches_sorted(unsorted):
    assert insertion_sort(unsorted) == sorted(unsorted)


def test_callback_called(unsorted):
    events = []
    insertion_sort(
        unsorted, on_step=lambda arr, i, j, event_type: events.append(event_type)
    )
    assert "compare" in events
    assert "set" in events
