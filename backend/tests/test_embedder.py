import math

from app.ingest.embedder import FakeEmbedder
from app.models.chunk import EMBEDDING_DIM


def test_fake_vectors_have_the_right_shape_and_length_one():
    [vector] = FakeEmbedder().embed(["Mouse M-042"])
    assert len(vector) == EMBEDDING_DIM
    assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0)


def test_fake_vectors_are_deterministic_and_distinct():
    a1, b, a2 = FakeEmbedder().embed(["alpha", "beta", "alpha"])
    assert a1 == a2
    assert a1 != b
