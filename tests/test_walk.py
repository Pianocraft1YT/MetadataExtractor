"""Tests for MetadataExtractor.walk_to_depth."""

from pathlib import Path


def test_depth_zero_only_root(extractor, tmp_path):
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)

    results = list(extractor.walk_to_depth(str(root), 0))
    paths = [Path(p) for p, _, _ in results]
    assert paths == [root]


def test_depth_one_includes_root_and_children(extractor, tmp_path):
    root = tmp_path / "root"
    (root / "a" / "b").mkdir(parents=True)
    (root / "c").mkdir()

    results = list(extractor.walk_to_depth(str(root), 1))
    paths = [Path(p) for p, _, _ in results]
    assert root in paths
    assert (root / "a") in paths
    assert (root / "c") in paths
    assert (root / "a" / "b") not in paths


def test_depth_two_includes_grandchildren(extractor, tmp_path):
    root = tmp_path / "root"
    (root / "a" / "b" / "c").mkdir(parents=True)

    results = list(extractor.walk_to_depth(str(root), 2))
    paths = [Path(p) for p, _, _ in results]
    assert (root / "a" / "b") in paths
    assert (root / "a" / "b" / "c") not in paths


def test_skips_hidden_folders(extractor, tmp_path):
    root = tmp_path / "root"
    (root / ".hidden").mkdir(parents=True)
    (root / "visible").mkdir()

    results = list(extractor.walk_to_depth(str(root), 5))
    paths = [Path(p) for p, _, _ in results]
    assert (root / "visible") in paths
    assert (root / ".hidden") not in paths


def test_skips_system_folders(extractor, tmp_path):
    root = tmp_path / "root"
    (root / "System Volume Information").mkdir(parents=True)
    (root / "$RECYCLE.BIN").mkdir()
    (root / "normal").mkdir()

    results = list(extractor.walk_to_depth(str(root), 5))
    paths = [Path(p) for p, _, _ in results]
    assert (root / "normal") in paths
    assert (root / "System Volume Information") not in paths
    assert (root / "$RECYCLE.BIN") not in paths


def test_alphabetical_ordering(extractor, tmp_path):
    root = tmp_path / "root"
    for name in ["c", "a", "b"]:
        (root / name).mkdir(parents=True)

    results = list(extractor.walk_to_depth(str(root), 1))
    names = [Path(p).name for p, _, _ in results]
    assert names == ["root", "a", "b", "c"]


def test_yields_files_per_folder(extractor, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "photo.jpg").write_bytes(b"fake")

    results = list(extractor.walk_to_depth(str(root), 0))
    _, _, files = results[0]
    assert "photo.jpg" in files


def test_skips_hidden_files(extractor, tmp_path):
    """Hidden files are filtered before reaching sort_and_extract."""
    (tmp_path / "visible.jpg").write_bytes(b"fake")
    (tmp_path / ".hidden.jpg").write_bytes(b"fake")

    results = list(extractor.walk_to_depth(str(tmp_path), 0))
    _, _, files = results[0]
    assert "visible.jpg" in files
    assert ".hidden.jpg" not in files


def test_skips_non_media_files(extractor, tmp_path):
    (tmp_path / "photo.jpg").write_bytes(b"fake")
    (tmp_path / "readme.txt").write_bytes(b"fake")

    results = list(extractor.walk_to_depth(str(tmp_path), 0))
    _, _, files = results[0]
    assert "photo.jpg" in files
    assert "readme.txt" not in files


def test_natural_sort_order(extractor, tmp_path):
    """IMG_9 should sort before IMG_10 (not lexicographic)."""
    for name in ["IMG_10.jpg", "IMG_9.jpg", "IMG_1.jpg"]:
        (tmp_path / name).write_bytes(b"fake")

    results = list(extractor.walk_to_depth(str(tmp_path), 0))
    _, _, files = results[0]
    assert files == ["IMG_1.jpg", "IMG_9.jpg", "IMG_10.jpg"]
