# ui/main_window.py

from PyQt6 import QtWidgets, QtCore
import cadquery as cq
from models.frame_model import make_frame
from models.bone_model import make_bone
from models.assembly import make_assembly
from exporter.exporter import export_shape
from ui.viewer import VTKViewer


def mklabel(text: str, tooltip: str) -> QtWidgets.QLabel:
    """Create a QLabel with tooltip."""
    lbl = QtWidgets.QLabel(text)
    lbl.setToolTip(tooltip)
    lbl.setStyleSheet("QLabel { font-weight: 600; }")
    return lbl


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PCB Magazine Generator")
        self.resize(1300, 900)

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # --- Left side: parameter form ---
        form = QtWidgets.QWidget()
        form_layout = QtWidgets.QFormLayout(form)
        form_layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        # View selection
        self.component_combo = QtWidgets.QComboBox()
        self.component_combo.addItems(["frame", "bone", "assembly"])
        self.component_combo.currentTextChanged.connect(self.on_component_changed)
        self.component_combo.setToolTip(
            "<b>View</b><br>"
            "<i>frame</i>: only one side frame<br>"
            "<i>bone</i>: single dovetail connector<br>"
            "<i>assembly</i>: 2× frames (top/bottom) + 4× bones"
        )
        form_layout.addRow(mklabel("View:", "Choose which part is displayed in the preview."), self.component_combo)

        # --- PCB parameters ---
        # a: PCB inner length (X-axis)
        self.a_spin = QtWidgets.QDoubleSpinBox()
        self.a_spin.setRange(10, 10000)
        self.a_spin.setValue(90.0)
        self.a_spin.setSuffix(" mm")
        self.a_spin.valueChanged.connect(self.update_preview)
        self.a_spin.setToolTip(
            "<b>PCB-width [a]</b><br>"
            "Inner dimension in X direction (PCB length).<br>"
            "Determines the inner frame opening between side guides."
        )

        # b: Bone total length (tip-to-tip)
        self.b_spin = QtWidgets.QDoubleSpinBox()
        self.b_spin.setRange(1, 1000)
        self.b_spin.setValue(120)
        self.b_spin.setSuffix(" mm")
        self.b_spin.valueChanged.connect(self.update_preview)
        self.b_spin.setToolTip(
            "<b>PCB-height [b]</b><br>"
            "Total bone length including dovetail tips.<br>"
            "In assembly mode, equals distance from bottom frame underside (Z=0) "
            "to top frame topside."
        )

        # c: Slot width (PCB thickness)
        self.c_spin = QtWidgets.QDoubleSpinBox()
        self.c_spin.setRange(0.1, 50)
        self.c_spin.setDecimals(3)
        self.c_spin.setValue(1.6)
        self.c_spin.setSuffix(" mm")
        self.c_spin.valueChanged.connect(self.update_preview)
        self.c_spin.setToolTip(
            "<b>PCB-thickness [c]</b><br>"
            "Width of each slot = PCB thickness.<br>"
            "Tip: Add a small tolerance (e.g., +0.1 mm) for easier fit."
        )

        # d: Distance between PCBs
        self.d_spin = QtWidgets.QDoubleSpinBox()
        self.d_spin.setRange(0.1, 100)
        self.d_spin.setValue(10.0)
        self.d_spin.setSuffix(" mm")
        self.d_spin.valueChanged.connect(self.update_preview)
        self.d_spin.setToolTip(
            "<b>PCB-PCB-distance [d]</b><br>"
            "Material width between two slots."
        )

        # n: Number of PCBs
        self.n_spin = QtWidgets.QSpinBox()
        self.n_spin.setRange(1, 200)
        self.n_spin.setValue(10)
        self.n_spin.valueChanged.connect(self.update_preview)
        self.n_spin.setToolTip(
            "<b>PCB-count [n]</b><br>"
            "Number of PCBs (and therefore number of slots)."
        )

        form_layout.addRow(mklabel("PCB-width [a]:", self.a_spin.toolTip()), self.a_spin)
        form_layout.addRow(mklabel("PCB-height [b]:", self.b_spin.toolTip()), self.b_spin)
        form_layout.addRow(mklabel("PCB-thickness [c]:", self.c_spin.toolTip()), self.c_spin)
        form_layout.addRow(mklabel("PCB-PCB-distance [d]:", self.d_spin.toolTip()), self.d_spin)
        form_layout.addRow(mklabel("PCB-count [n]:", self.n_spin.toolTip()), self.n_spin)

        # --- Overall size (bounding box) display ---
        self.size_value = QtWidgets.QLabel("— × — × — mm")
        self.size_value.setToolTip(
            "<b>Overall size of the current model</b><br>"
            "Axis-aligned bounding box computed from the generated geometry.<br>"
            "Format: <i>X × Y × Z</i> in millimeters."
        )
        form_layout.addRow(mklabel("Overall size (X×Y×Z):", self.size_value.toolTip()), self.size_value)

        # --- Export controls ---
        export_row = QtWidgets.QHBoxLayout()
        self.fmt_combo = QtWidgets.QComboBox()
        self.fmt_combo.addItems(["step", "stl"])
        btn_export = QtWidgets.QPushButton("Export")
        btn_export.clicked.connect(self.export_model)
        export_row.addWidget(self.fmt_combo, 0)
        export_row.addWidget(btn_export, 0)
        form_layout.addRow(export_row)

        # --- Right side: viewer ---
        viewer = VTKViewer()

        splitter.addWidget(form)
        splitter.addWidget(viewer)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.viewer = viewer

        # Default start view: assembly
        self.component_combo.setCurrentText("assembly")
        self.update_preview()

    def build_model(self):
        """Builds the selected model with current parameters."""
        comp = self.component_combo.currentText()
        if comp == "frame":
            return make_frame(self.a_spin.value(), self.c_spin.value(), self.d_spin.value(), self.n_spin.value())
        elif comp == "bone":
            return make_bone(b=self.b_spin.value())
        else:
            return make_assembly(
                self.a_spin.value(),
                self.c_spin.value(),
                self.d_spin.value(),
                self.n_spin.value(),
                self.b_spin.value()
            )

    def _compute_bounding_box(self, model):
        """
        Compute an axis-aligned bounding box (X, Y, Z in mm) for either:
        - a single CadQuery Workplane, or
        - an assembly list of (Workplane, (dx,dy,dz), (rz,ry,rx))
        """
        def apply_transform(wp, dx, dy, dz, rz, ry, rx):
            if rz: wp = wp.rotate((0, 0, 0), (0, 0, 1), rz)
            if ry: wp = wp.rotate((0, 0, 0), (0, 1, 0), ry)
            if rx: wp = wp.rotate((0, 0, 0), (1, 0, 0), rx)
            return wp.translate((dx, dy, dz))

        if isinstance(model, list):
            solids = []
            for shp, (dx, dy, dz), (rz, ry, rx) in model:
                moved = apply_transform(shp, dx, dy, dz, rz, ry, rx)
                solids.append(moved.val())
            comp = cq.Compound.makeCompound(solids)
            bb = comp.BoundingBox()
        else:
            bb = cq.Compound.makeCompound([model.val()]).BoundingBox()

        # Return lengths (positive extents)
        return bb.xlen, bb.ylen, bb.zlen

    def _update_size_label(self, model):
        """Update the size label with the model's bounding box in mm."""
        try:
            x, y, z = self._compute_bounding_box(model)
            # Round to 2 decimals for readability
            def fmt(v): return f"{v:.2f}"
            self.size_value.setText(f"{fmt(x)} × {fmt(y)} × {fmt(z)} mm")
        except Exception:
            self.size_value.setText("— × — × — mm")

    def update_preview(self):
        """Rebuilds and displays the model preview, then updates the size readout."""
        try:
            model = self.build_model()
            self.viewer.show(model)
            self._update_size_label(model)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Model build error", str(e))

    def export_model(self):
        """Exports the current model to STEP or STL."""
        try:
            model = self.build_model()
            fmt = self.fmt_combo.currentText()
            default_name = "model.step" if fmt == "step" else "model.stl"
            out, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Export model", default_name,
                "STEP (*.step *.stp);;STL (*.stl)"
            )
            if not out:
                return

            if isinstance(model, list):
                # Export assembly as compound
                moved_vals = []
                for shp, (dx, dy, dz), (rz, ry, rx) in model:
                    wp = shp
                    if rz: wp = wp.rotate((0, 0, 0), (0, 0, 1), rz)
                    if ry: wp = wp.rotate((0, 0, 0), (0, 1, 0), ry)
                    if rx: wp = wp.rotate((0, 0, 0), (1, 0, 0), rx)
                    wp = wp.translate((dx, dy, dz))
                    moved_vals.append(wp.val())
                comp = cq.Compound.makeCompound(moved_vals)
                wp_comp = cq.Workplane(obj=comp)
                path = export_shape(wp_comp, out, fmt)
            else:
                path = export_shape(model, out, fmt)

            QtWidgets.QMessageBox.information(self, "Export complete", f"Exported to:\n{path}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export error", str(e))

    def on_component_changed(self, name: str):
        """Handles enabling/disabling parameter fields when view changes."""
        is_frame = (name == "frame")
        is_bone = (name == "bone")
        is_assembly = (name == "assembly")

        for w in (self.a_spin, self.c_spin, self.d_spin, self.n_spin):
            w.setEnabled(is_frame or is_assembly)
        self.b_spin.setEnabled(is_bone or is_assembly)

        # Auto-update preview on view change
        self.update_preview()
