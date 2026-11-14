import io

from agriscope import create_app
from agriscope.config import Config
from agriscope.detector import InferenceError

from conftest import FakeDetector, make_image_bytes


def test_detect_success_shape(post_file, fake):
    r = post_file(make_image_bytes())
    j = r.get_json()
    assert r.status_code == 200 and j["ok"] is True
    assert j["image"] == {"width": 128, "height": 96}
    assert j["detections"][0]["label"] == "Late blight"
    assert j["findings"][0]["guidance"]["actions"]
    assert fake.calls == [((128, 96), 0.25)]


def test_accepts_png_webp_and_rgba(post_file):
    for fmt, mode in [("PNG", "RGB"), ("WEBP", "RGB"), ("PNG", "RGBA")]:
        assert post_file(make_image_bytes(fmt, mode=mode)).status_code == 200


def test_confidence_parameter(post_file, fake):
    assert post_file(make_image_bytes(), confidence="0.6").status_code == 200
    assert fake.calls[-1][1] == 0.6
    for bad in ["abc", "0.01", "1.5", "nan"]:
        r = post_file(make_image_bytes(), confidence=bad)
        assert r.status_code == 400 and r.get_json()["error"]["code"] == "invalid_confidence"


def test_missing_and_empty_file(client, post_file):
    assert client.post("/api/detect", data={}).get_json()["error"]["code"] == "no_file"
    r = post_file(b"")
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "empty_file"


def test_rejects_non_images_by_content_not_name(post_file):
    for payload in [b"%PDF-1.4 fake", b"just text", b"GIF89a" + b"0" * 50]:
        r = post_file(payload, name="leaf.jpg")
        assert r.status_code == 415 and r.get_json()["error"]["code"] == "unsupported_type"
    assert post_file(make_image_bytes("GIF")).status_code == 415
    assert post_file(make_image_bytes("BMP")).status_code == 415


def test_corrupt_and_tiny_images(post_file):
    good = make_image_bytes(size=(400, 400))
    r = post_file(good[: len(good) // 2])
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "corrupt_image"
    r = post_file(make_image_bytes(size=(10, 10)))
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "image_too_small"


def test_pixel_limit():
    app = create_app(Config(preload_model=False, max_pixels=10_000), detector=FakeDetector())
    r = app.test_client().post("/api/detect", data={"file": (io.BytesIO(make_image_bytes(size=(200, 200))), "a.jpg")}, content_type="multipart/form-data")
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "image_too_large"


def test_oversize_upload_is_413_json(client):
    big = b"\xff\xd8\xff" + b"0" * (2 * 1024 * 1024)
    r = client.post("/api/detect", data={"file": (io.BytesIO(big), "a.jpg")}, content_type="multipart/form-data")
    assert r.status_code == 413 and r.get_json()["error"]["code"] == "file_too_large"


def test_model_unavailable_is_503_without_paths():
    app = create_app(Config(preload_model=False), detector=FakeDetector(ready=False))
    r = app.test_client().post("/api/detect", data={"file": (io.BytesIO(make_image_bytes()), "a.jpg")}, content_type="multipart/form-data")
    j = r.get_json()
    assert r.status_code == 503 and j["error"]["code"] == "model_unavailable"
    assert "/" not in j["error"]["message"].replace("ultralytics / torch", "")


def test_inference_failure_is_500_without_internals():
    app = create_app(Config(preload_model=False), detector=FakeDetector(raises=InferenceError("The model couldn't analyze this image. Try a different photo.")))
    r = app.test_client().post("/api/detect", data={"file": (io.BytesIO(make_image_bytes()), "a.jpg")}, content_type="multipart/form-data")
    assert r.status_code == 500 and "Traceback" not in r.get_data(as_text=True)


def test_unexpected_exception_is_sanitised():
    class Boom(FakeDetector):
        def predict(self, image, confidence):
            raise RuntimeError("secret /home/user/key.pem")

    app = create_app(Config(preload_model=False), detector=Boom())
    app.testing = False
    r = app.test_client().post("/api/detect", data={"file": (io.BytesIO(make_image_bytes()), "a.jpg")}, content_type="multipart/form-data")
    assert r.status_code == 500
    assert "secret" not in r.get_data(as_text=True) and r.get_json()["error"]["code"] == "internal_error"


def test_method_and_unknown_api_routes_are_json(client):
    assert client.get("/api/detect").get_json()["error"]["code"] == "method_not_allowed"
    assert client.get("/api/nope").status_code == 404 and client.get("/api/nope").get_json()["ok"] is False


def test_health(client):
    j = client.get("/api/health").get_json()
    assert j["status"] == "ok" and j["model"]["num_classes"] == 15
    assert client.get("/api/health").headers["Cache-Control"] == "no-store"
