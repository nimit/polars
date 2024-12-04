import pytest

import polars as pl


@pytest.mark.slow
def test_concat_expressions_stack_overflow() -> None:
    n = 10000
    e = pl.concat([pl.lit(x) for x in range(n)])

    df = pl.select(e)
    assert df.shape == (n, 1)


@pytest.mark.slow
def test_concat_lf_stack_overflow() -> None:
    n = 1000
    bar = pl.DataFrame({"a": 0}).lazy()

    for i in range(n):
        bar = pl.concat([bar, pl.DataFrame({"a": i}).lazy()])
    assert bar.collect().shape == (1001, 1)


def test_concat_horizontally_strict() -> None:
    a = pl.DataFrame({"a": [0, 1, 2], "b": [1, 2, 3]})
    b = pl.DataFrame({"c": [11], "d": [42]}) # 1 vs N (may broadcast)
    c = pl.DataFrame({"c": [11, 12], "d": [42, 24]}) # 2 vs N

    with pytest.raises(pl.exceptions.ShapeError):
        pl.concat([a, b], how="horizontal", strict=True)

    with pytest.raises(pl.exceptions.ShapeError):
        pl.concat([a, c], how="horizontal", strict=True)

    with pytest.raises(pl.exceptions.ShapeError):
        pl.concat([a.lazy(), b.lazy()], how="horizontal", strict=True).collect()

    with pytest.raises(pl.exceptions.ShapeError):
        pl.concat([a.lazy(), c.lazy()], how="horizontal", strict=True).collect()

    out = pl.concat([a, b], how="horizontal", strict=False)
    assert out.to_dict(as_series=False) == {
        "a": [0, 1, 2],
        "b": [1, 2, 3],
        "c": [11, None, None],
        "d": [42, None, None],
    }

    out = pl.concat([b, c], how="horizontal", strict=False)
    assert out.to_dict(as_series=False) == {
        "a": [0, 1, 2],
        "b": [1, 2, 3],
        "c": [11, 12, None],
        "d": [42, 24, None],
    }


def test_concat_vertically_relaxed() -> None:
    a = pl.DataFrame(
        data={"a": [1, 2, 3], "b": [True, False, None]},
        schema={"a": pl.Int8, "b": pl.Boolean},
    )
    b = pl.DataFrame(
        data={"a": [43, 2, 3], "b": [32, 1, None]},
        schema={"a": pl.Int16, "b": pl.Int64},
    )
    out = pl.concat([a, b], how="vertical_relaxed")
    assert out.schema == {"a": pl.Int16, "b": pl.Int64}
    assert out.to_dict(as_series=False) == {
        "a": [1, 2, 3, 43, 2, 3],
        "b": [1, 0, None, 32, 1, None],
    }
    out = pl.concat([b, a], how="vertical_relaxed")
    assert out.schema == {"a": pl.Int16, "b": pl.Int64}
    assert out.to_dict(as_series=False) == {
        "a": [43, 2, 3, 1, 2, 3],
        "b": [32, 1, None, 1, 0, None],
    }

    c = pl.DataFrame({"a": [1, 2], "b": [2, 1]})
    d = pl.DataFrame({"a": [1.0, 0.2], "b": [None, 0.1]})

    out = pl.concat([c, d], how="vertical_relaxed")
    assert out.schema == {"a": pl.Float64, "b": pl.Float64}
    assert out.to_dict(as_series=False) == {
        "a": [1.0, 2.0, 1.0, 0.2],
        "b": [2.0, 1.0, None, 0.1],
    }
    out = pl.concat([d, c], how="vertical_relaxed")
    assert out.schema == {"a": pl.Float64, "b": pl.Float64}
    assert out.to_dict(as_series=False) == {
        "a": [1.0, 0.2, 1.0, 2.0],
        "b": [None, 0.1, 2.0, 1.0],
    }
