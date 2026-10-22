from datetime import datetime
from services.validators import slots_overlap

def test_separate_slots_do_not_overlap():
    # Слот A: 10:00 - 11:00
    a_start = datetime(2026, 10, 15, 10, 0)
    a_end = datetime(2026, 10, 15, 11, 0)
    
    # Слот B: 12:00 - 13:00
    b_start = datetime(2026, 10, 15, 12, 0)
    b_end = datetime(2026, 10, 15, 13, 0)
    
    #не перетинаються - очікуємо False
    assert slots_overlap(a_start, a_end, b_start, b_end) is False


def test_overlapping_slots_return_true():
    # Слот A: 10:00 - 12:00
    a_start = datetime(2026, 10, 15, 10, 0)
    a_end = datetime(2026, 10, 15, 12, 0)

    # Слот B: 11:00 - 13:00 
    b_start = datetime(2026, 10, 15, 11, 0)
    b_end = datetime(2026, 10, 15, 13, 0)

    assert slots_overlap(a_start, a_end, b_start, b_end) is True


def test_adjacent_slots_do_not_overlap():
    # Слот A: 14:00 - 15:20
    a_start = datetime(2026, 10, 15, 14, 0)
    a_end = datetime(2026, 10, 15, 15, 20)

    # Слот B: 15:20 - 16:40 
    b_start = datetime(2026, 10, 15, 15, 20)
    b_end = datetime(2026, 10, 15, 16, 40)

    assert slots_overlap(a_start, a_end, b_start, b_end) is False


def test_nested_slots_overlap():
    # Слот A: 10:00 - 14:00 
    a_start = datetime(2026, 10, 15, 10, 0)
    a_end = datetime(2026, 10, 15, 14, 0)

    # Слот B: 11:00 - 12:00 
    b_start = datetime(2026, 10, 15, 11, 0)
    b_end = datetime(2026, 10, 15, 12, 0)

    assert slots_overlap(a_start, a_end, b_start, b_end) is True