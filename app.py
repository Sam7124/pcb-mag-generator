# app.py
import argparse
import sys
import cadquery as cq
from exporter.exporter import export_shape
from models.frame_model import make_frame
from models.bone_model import make_bone
from models.assembly import make_assembly


def run_gui():
    """
    Launch the PyQt-based GUI for interactive parameter editing and preview.
    """
    from PyQt6 import QtWidgets
    from ui.main_window import MainWindow
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


def main():
    """
    CLI and GUI entry point.

    - Without '--nogui', the GUI is launched.
    - In CLI mode, builds the specified component (frame, bone, or assembly)
      with provided parameters and exports it as STL or STEP.
    """
    p = argparse.ArgumentParser(description="PCB Magazine Generator")
    p.add_argument(
        '--nogui',
        action='store_true',
        help='Run in CLI mode (no GUI)'
    )
    p.add_argument(
        '--component',
        choices=['frame', 'bone', 'assembly'],
        default='assembly',
        help='Component to build'
    )
    p.add_argument(
        '-a', type=float, default=90.0,
        help='PCB-width [a] (inner X dimension, mm)'
    )
    p.add_argument(
        '-b', type=float, default=120.0,
        help='PCB-height [b] (bone tip-to-tip length, mm)'
    )
    p.add_argument(
        '-c', type=float, default=1.6,
        help='PCB-thickness [c] (slot width, mm)'
    )
    p.add_argument(
        '-d', type=float, default=10.0,
        help='PCB-PCB-distance [d] (material between slots, mm)'
    )
    p.add_argument(
        '-n', type=int, default=10,
        help='PCB-count [n] (number of slots)'
    )
    p.add_argument(
        '--fmt', choices=['stl', 'step'], default='stl',
        help='Output format'
    )
    p.add_argument(
        '--out', type=str, default='model.stl',
        help='Output file path'
    )
    args = p.parse_args()

    # If GUI mode: launch GUI and return
    if not args.nogui:
        return run_gui()

    # === Build model ===
    if args.component == 'frame':
        model = make_frame(args.a, args.c, args.d, args.n)
    elif args.component == 'bone':
        model = make_bone(b=args.b)
    else:
        model = make_assembly(args.a, args.c, args.d, args.n, args.b)

    # === Export ===
    if isinstance(model, list):
        # Assembly: combine into a single compound for export
        moved_vals = []
        for shp, (dx, dy, dz), (rz, ry, rx) in model:
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
        wp_comp = cq.Workplane(obj=comp)
        path = export_shape(wp_comp, args.out, args.fmt)
    else:
        path = export_shape(model, args.out, args.fmt)

    print(f"Exported to: {path}")


if __name__ == '__main__':
    main()
