"""Runs against the real weights. Skipped automatically if torch/ultralytics or the weights are missing."""
import os

import pytest
from PIL import Image

pytest.importorskip("ultralytics")
from agriscope.config import ROOT  # noqa: E402
from agriscope.detector import Detector  # noqa: E402
from agriscope.knowledge import describe_class, guidance_for  # noqa: E402

WEIGHTS = str(ROOT / "models" / "best.pt")
pytestmark = pytest.mark.skipif(not os.path.isfile(WEIGHTS), reason="models/best.pt not present")


@pytest.fixture(scope="module")
def det():
    d = Detector(WEIGHTS)
    d.ensure_loaded()
    return d


def test_weights_are_a_detection_model_with_15_classes(det):
    info = det.info()
    assert info["task"] == "detect" and info["num_classes"] == 15


def test_every_model_class_has_reference_notes(det):
    for name in det.class_names().values():
        assert describe_class(name)["group_key"] != "unknown", name
        assert guidance_for(name), name


def test_known_sample_detections(det):
    img = Image.open(ROOT / "static" / "samples" / "late_blight.jpg").convert("RGB")
    r = det.predict(img, 0.25)
    assert r["detections"] and r["findings"][0]["label"] == "Late blight"
    d = r["detections"][0]
    assert 0.25 <= d["confidence"] <= 1.0
    b = d["box"]
    assert 0 <= b["x1"] < b["x2"] <= r["image"]["width"] and 0 <= b["y1"] < b["y2"] <= r["image"]["height"]


def test_threshold_is_respected(det):
    img = Image.open(ROOT / "static" / "samples" / "eb.jpg").convert("RGB")
    low, high = det.predict(img, 0.1), det.predict(img, 0.75)
    assert len(low["detections"]) >= len(high["detections"])
    assert all(d["confidence"] >= 0.75 for d in high["detections"])


def test_missing_weights_report_cleanly(tmp_path):
    from agriscope.detector import ModelUnavailable

    d = Detector(str(tmp_path / "nope.pt"))
    with pytest.raises(ModelUnavailable) as e:
        d.ensure_loaded()
    assert str(tmp_path) not in str(e.value)


def test_corrupt_weights_report_cleanly(tmp_path):
    from agriscope.detector import ModelUnavailable

    bad = tmp_path / "bad.pt"
    bad.write_bytes(b"not a model")
    d = Detector(str(bad))
    with pytest.raises(ModelUnavailable) as e:
        d.ensure_loaded()
    assert str(tmp_path) not in str(e.value) and not d.ready
