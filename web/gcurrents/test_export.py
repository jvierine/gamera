from pathlib import Path
import importlib.util
import numpy as np


MODULE = Path(__file__).with_name("export_gcurrents.py")
spec = importlib.util.spec_from_file_location("export_gcurrents", MODULE)
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


def test_cell_centres():
    corners = np.arange(27, dtype=float).reshape(3, 3, 3)
    centres = export.cell_centres(corners)
    assert centres.shape == (2, 2, 2)
    assert centres[0, 0, 0] == np.mean(corners[:2, :2, :2])


def test_choose_steps_includes_end():
    rows = [(0, -60.0, 1.0), (1, 0.0, 2.0), (2, 61.0, 3.0), (3, 120.0, 4.0)]
    chosen = export.choose_steps(rows, 60.0)
    assert [row[0] for row in chosen] == [1, 2, 3]


def test_mjd_epoch():
    assert export.mjd_iso(0.0) == "1858-11-17T00:00:00Z"
