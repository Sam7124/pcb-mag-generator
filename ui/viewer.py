# ui/viewer.py
import os
import tempfile
import cadquery as cq
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt6 import QtWidgets


class VTKViewer(QtWidgets.QFrame):
    """
    Lightweight STL-based 3D preview using PyVistaQt.

    Notes:
        - We always export a temporary STL for preview (fast and portable).
        - For assemblies, parts are transformed (rotate+translate) and combined
          into a single compound prior to export.
        - The visual style uses a smooth shaded surface with a thin wireframe
          overlay for legible edges without triangle clutter.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter.interactor)
        self._reset_view()

    def _reset_view(self) -> None:
        """Initialize/clear the scene and reset the camera."""
        self.plotter.clear()
        self.plotter.add_axes()
        self.plotter.show_grid()
        self.plotter.reset_camera()

    def _export_to_stl(self, shape: cq.Workplane, path: str) -> None:
        """Export a CadQuery Workplane to an STL file at the given path."""
        cq.exporters.export(shape, path, exportType="STL")

    def _combine_assembly(self, items):
        """
        Combine an assembly into a single compound Workplane.

        Args:
            items: list of tuples
                (workplane, (dx, dy, dz), (rz, ry, rx))
                where rotations are in degrees.

        Returns:
            cq.Workplane: compound of all transformed parts.
        """
        moved_vals = []
        for shp, (dx, dy, dz), (rz, ry, rx) in items:
            wp = shp
            if rz:
                wp = wp.rotate((0, 0, 0), (0, 0, 1), rz)
            if ry:
                wp = wp.rotate((0, 0, 0), (0, 1, 0), ry)
            if rx:
                wp = wp.rotate((0, 0, 0), (1, 0, 0), rx)
            wp = wp.translate((dx, dy, dz))
            moved_vals.append(wp.val())
        comp = cq.Compound.makeCompound(moved_vals)
        return cq.Workplane(obj=comp)

    def show(self, obj) -> None:
        """
        Render a single Workplane or an assembly list.

        Args:
            obj: cq.Workplane or list as returned by make_assembly(...)
        """
        with tempfile.TemporaryDirectory() as td:
            tmp = os.path.join(td, "preview.stl")
            if isinstance(obj, list):
                comp = self._combine_assembly(obj)
                self._export_to_stl(comp, tmp)
            else:
                self._export_to_stl(obj, tmp)

            mesh = pv.read(tmp)
            self.plotter.clear()

            # Smooth shaded surface (no triangle edges)
            self.plotter.add_mesh(
                mesh,
                show_edges=False,
                smooth_shading=True,
                color="lightgray",
            )

            # Thin wireframe overlay for visual edges
            self.plotter.add_mesh(
                mesh,
                style="wireframe",
                color="black",
                line_width=1,
            )

            self.plotter.reset_camera()
