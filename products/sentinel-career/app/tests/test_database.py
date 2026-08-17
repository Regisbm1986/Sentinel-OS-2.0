
import pytest
import sys
if __name__ == "__main__":
    import pytest; raise SystemExit(pytest.main([__file__]))
import os
from products.sentinel_career.backend.database.models import HistoryRecord
from products.sentinel_career.backend.database.repository import HistoryRepository
from products.sentinel_career.backend.database.analytics import (
    calculate_trend, calculate_growth, calculate_average, calculate_improvement, calculate_history_summary
)
from products.sentinel_career.backend.database.storage import JSONStorage
from products.sentinel_career.backend.database.exceptions import DatabaseError, RecordNotFoundError

TEST_JSON = 'test_history.json'

@pytest.fixture(autouse=True)
def cleanup():
    if os.path.exists(TEST_JSON):
        os.remove(TEST_JSON)
    yield
    if os.path.exists(TEST_JSON):
        os.remove(TEST_JSON)

def test_save_and_load():
    repo = HistoryRepository(storage=JSONStorage(TEST_JSON))
    record = HistoryRecord(id='', user_id='u1', engine='ATS', timestamp='2024-06-27T00:00:00', score=88, raw_data={}, metadata={})
    repo.save(record)
    loaded = repo.list(user_id='u1')
    assert loaded and loaded[0].user_id == 'u1'
    found = repo.load(loaded[0].id)
    assert found.user_id == 'u1'

def test_update_and_delete():
    repo = HistoryRepository(storage=JSONStorage(TEST_JSON))
    record = HistoryRecord(id='', user_id='x', engine='Career', timestamp='2024-06-27T00:00:00', score=72, raw_data={}, metadata={})
    repo.save(record)
    rec = repo.list(user_id='x')[0]
    repo.update(rec.id, {'score': 90})
    rec2 = repo.load(rec.id)
    assert rec2.score == 90
    repo.delete(rec.id)
    with pytest.raises(RecordNotFoundError):
        repo.load(rec.id)

def test_analytics():
    from datetime import datetime, timedelta
    repo = HistoryRepository(storage=JSONStorage(TEST_JSON))
    now = datetime.now()
    for i, v in enumerate([70, 72, 76, 83, 95]):
        rec = HistoryRecord(id='', user_id='ana', engine='Job', timestamp=(now).isoformat(), score=v, raw_data={}, metadata={})
        repo.save(rec)
    hist = [r.to_dict() for r in repo.list(user_id='ana')]
    summary = calculate_history_summary(hist)
    assert summary['trend'] == 'up'
    assert summary['growth'] == 25
    assert summary['average'] > 70
    assert summary['improvement'] == 25

def test_storage_exception(tmp_path):
    invalid_path = tmp_path / "invalid_dir"
    invalid_path.mkdir(parents=True, exist_ok=True)

    repo = HistoryRepository(storage=JSONStorage(invalid_path))
    with pytest.raises(DatabaseError):
        repo.save(HistoryRecord(id='', user_id='fail', engine='Career', timestamp='now', score=11, raw_data={}, metadata={}))
