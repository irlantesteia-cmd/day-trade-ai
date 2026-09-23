import os
import shutil
import tempfile

import pytest

from src.models.logistic import LogisticRegressionModel
from src.models.registry import ModelMetadata, ModelRegistry


@pytest.fixture
def tmp_registry():
    d = tempfile.mkdtemp(prefix="test_registry_")
    reg = ModelRegistry(root_dir=d)
    yield reg
    shutil.rmtree(d, ignore_errors=True)


def _make_metadata(model_id="logistic", version="v1"):
    return ModelMetadata(
        model_id=model_id,
        model_version=version,
        dataset_version="ds_v1",
        feature_version="fs_v1",
        feature_keys=["f1", "f2"],
        training_period=("2026-01-01", "2026-06-30"),
        parameters={"lr": 0.3, "epochs": 100},
        metrics={"acc_oos": 0.55, "edge_pp": 1.2},
    )


def test_save_and_load_roundtrip(tmp_registry):
    model = LogisticRegressionModel(learning_rate=0.3, epochs=50)
    model.fit([[0.1, 0.2], [0.3, 0.4]], [0, 1])

    entry = tmp_registry.save(model, _make_metadata())
    assert os.path.isdir(entry)
    assert os.path.exists(os.path.join(entry, "model.pkl"))
    assert os.path.exists(os.path.join(entry, "metadata.json"))

    loaded, meta = tmp_registry.load("logistic", "v1")
    assert meta.model_id == "logistic"
    assert meta.model_version == "v1"
    assert meta.dataset_version == "ds_v1"
    assert meta.feature_keys == ["f1", "f2"]
    assert meta.training_period == ("2026-01-01", "2026-06-30")
    assert loaded.is_fitted is True


def test_exists(tmp_registry):
    assert tmp_registry.exists("logistic", "v1") is False
    model = LogisticRegressionModel()
    model.fit([[0.1], [0.2]], [0, 1])
    tmp_registry.save(model, _make_metadata())
    assert tmp_registry.exists("logistic", "v1") is True


def test_list_models(tmp_registry):
    model = LogisticRegressionModel()
    model.fit([[0.1], [0.2]], [0, 1])

    tmp_registry.save(model, _make_metadata("m1", "v1"))
    tmp_registry.save(model, _make_metadata("m1", "v2"))
    tmp_registry.save(model, _make_metadata("m2", "v1"))

    entries = tmp_registry.list_models()
    assert ("m1", "v1") in entries
    assert ("m1", "v2") in entries
    assert ("m2", "v1") in entries
    assert len(entries) == 3


def test_get_metadata(tmp_registry):
    model = LogisticRegressionModel()
    model.fit([[0.1], [0.2]], [0, 1])
    tmp_registry.save(model, _make_metadata())

    meta = tmp_registry.get_metadata("logistic", "v1")
    assert meta.parameters["lr"] == 0.3
    assert meta.metrics["acc_oos"] == 0.55


def test_load_missing_raises(tmp_registry):
    with pytest.raises(FileNotFoundError):
        tmp_registry.load("nao_existe", "v0")


def test_delete(tmp_registry):
    model = LogisticRegressionModel()
    model.fit([[0.1], [0.2]], [0, 1])
    tmp_registry.save(model, _make_metadata())

    assert tmp_registry.exists("logistic", "v1") is True
    tmp_registry.delete("logistic", "v1")
    assert tmp_registry.exists("logistic", "v1") is False


def test_metadata_tuple_serialization(tmp_registry):
    """tuples viram lists em JSON — devem voltar como tuples."""
    model = LogisticRegressionModel()
    model.fit([[0.1], [0.2]], [0, 1])

    md = _make_metadata()
    md.validation_period = ("2026-07-01", "2026-07-31")
    tmp_registry.save(model, md)

    loaded_meta = tmp_registry.get_metadata("logistic", "v1")
    assert isinstance(loaded_meta.training_period, tuple)
    assert isinstance(loaded_meta.validation_period, tuple)
    assert loaded_meta.validation_period == ("2026-07-01", "2026-07-31")