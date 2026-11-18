import pytest

from app.core.storage import LocalStorage


def test_local_roundtrip(tmp_path):
    storage = LocalStorage(tmp_path)
    storage.put("uploads/abc/notes.txt", b"hello", "text/plain")

    assert storage.read("uploads/abc/notes.txt") == b"hello"
    assert (tmp_path / "uploads/abc/notes.txt").exists()
    assert storage.presigned_url("uploads/abc/notes.txt", "notes.txt") is None

    storage.delete("uploads/abc/notes.txt")
    assert not (tmp_path / "uploads/abc/notes.txt").exists()


def test_delete_missing_file_is_fine(tmp_path):
    LocalStorage(tmp_path).delete("uploads/nope.txt")


@pytest.mark.parametrize("key", ["../outside.txt", "uploads/../../outside.txt"])
def test_keys_cannot_escape_the_folder(tmp_path, key):
    with pytest.raises(ValueError):
        LocalStorage(tmp_path / "root").put(key, b"x", "text/plain")
