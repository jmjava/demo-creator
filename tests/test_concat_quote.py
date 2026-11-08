from pathlib import Path

import pytest

from democreator.compose import ComposeError, concat_list_text


def test_quote_in_concat_path_is_refused(tmp_path: Path):
    """A quote in a segment path used to close the concat entry early."""
    with pytest.raises(ComposeError, match="quote"):
        concat_list_text([tmp_path / "a'b.webm"])
