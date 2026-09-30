"""Same-directory atomic replacement for user files."""

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_destination(path: Path) -> Iterator[Path]:
    """Yield a temporary path; replace the destination only after successful writing.

    The original suffix is retained for format validators. An exception leaves
    an existing destination untouched. Temporary files are always removed.
    """

    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.stem}-", suffix=path.suffix, dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        yield temporary
        with temporary.open("r+b") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
