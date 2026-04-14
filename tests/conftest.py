import pytest


@pytest.fixture
def unsorted():
    return [5, 3, 8, 1, 9, 2, 7, 4, 6]


@pytest.fixture
def already_sorted():
    return [1, 2, 3, 4, 5, 6, 7, 8, 9]


@pytest.fixture
def reverse_sorted():
    return [9, 8, 7, 6, 5, 4, 3, 2, 1]


@pytest.fixture
def with_duplicates():
    return [3, 1, 4, 1, 5, 9, 2, 6, 5, 3]
