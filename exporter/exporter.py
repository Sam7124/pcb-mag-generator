# exporter/exporter.py
import cadquery as cq
from pathlib import Path


def export_shape(shape: cq.Workplane, out_path: str, fmt: str = "stl") -> str:
    """
    Export a CadQuery Workplane to either STL or STEP format.

    Args:
        shape: CadQuery Workplane object to export.
        out_path: Destination file path as string.
        fmt: Export format ('stl', 'step', or 'stp').

    Returns:
        Absolute path to the exported file.

    Raises:
        ValueError: If an unsupported export format is specified.
    """
    fmt = fmt.lower()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "stl":
        cq.exporters.export(shape, str(out), exportType="STL")
    elif fmt in ("step", "stp"):
        cq.exporters.export(shape, str(out), exportType="STEP")
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    return str(out.resolve())
