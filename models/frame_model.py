# models/frame_model.py
import cadquery as cq

# ===== Public parameters (provided by UI/CLI) =====
# make_frame(a_len, c_slot, d_nose, n)

# ===== Construction constants =====
# Inner window extends by LEN_EXTRA over the nominal PCB width [a]
LEN_EXTRA = 5.0

# Base plate thickness
PLATE_T = 8.0

# Rail (dovetail/guide) depth cut into the inner window
NOSE_DEPTH = 3.0

# Frame wall thicknesses around the inner window
FRAME_WALL_X = 10.0 - NOSE_DEPTH  # leave space because nose eats into the inner window
FRAME_WALL_Y = 10.0

# Extra margin above and below the slot field
TOP_BOTTOM_MARGIN = 2.0

# (Kept for completeness; currently not used explicitly on noses)
NOSE_CH = 0.6

# Small rectangular connector openings near the outer edges
CONNECTOR_H = 5.0
CONNECTOR_W = 6.0
CONNECTOR_XOFF = 8.0

# Triangular cable chamfer wedge geometry around the connector cutouts
CHAMFER_X = 4.0
CHAMFER_Z = PLATE_T

# Outer vertical corner chamfer
OUTER_CORNER_CH = 2.0

# Tiny bevel along the connector opening top edges (visual clean-up)
CONNECTOR_TOP_CH = 0.5


def active_height(n: int, slot_w: float, nose_w: float) -> float:
    """Total inner Y extent spanned by the slot field.

    Includes n slots and (n+1) noses between/around them.

    Args:
        n: Number of PCBs (=> number of slots).
        slot_w: Slot width (PCB thickness).
        nose_w: Material width between two slots.

    Returns:
        Total inner height covered by slots and noses (mm).
    """
    return n * slot_w + (n + 1) * nose_w


def make_frame(a_len: float, c_slot: float, d_nose: float, n: int) -> cq.Workplane:
    """Build the frame with two vertical rails and n slots per side.

    Coordinate system:
        - XY plane is the plate plane.
        - Z is the plate thickness.
        - The shape is centered on (0, 0, 0) before downstream assembly transforms.

    Geometry summary:
        1) Create an outer plate and cut the inner window (opening).
        2) Add left/right vertical rails (noses) along X edges of the inner window.
        3) Cut n slots per rail (width = c_slot, spaced by d_nose).
        4) Cut connector rectangles near outer edges (top and bottom).
        5) Add triangular chamfer wedges at the connector openings.
        6) Add small cosmetic chamfers (outer corners and above connectors).

    Args:
        a_len: PCB inner width [a] in X (mm). The inner opening is a_len + LEN_EXTRA.
        c_slot: Slot width [c] in Y (mm) = PCB thickness.
        d_nose: Material width [d] between slots (mm).
        n: Number of PCBs [n] = number of slots.

    Returns:
        CadQuery Workplane containing the final frame solid.
    """
    # --- Inner/outer dimensions ---
    inner_x = a_len + LEN_EXTRA
    inner_y = active_height(n, c_slot, d_nose)
    outer_x = inner_x + 2 * FRAME_WALL_X
    outer_y = inner_y + 2 * (FRAME_WALL_Y + TOP_BOTTOM_MARGIN)

    # --- Base plate with inner window cutout ---
    frame = cq.Workplane("XY").box(outer_x, outer_y, PLATE_T)
    frame = frame.faces(">Z").workplane().rect(inner_x, inner_y).cutBlind(-PLATE_T)

    # --- Left/right rails (noses) along the inner window vertical edges ---
    left_rail = (
        cq.Workplane("XY")
        .center(-inner_x / 2 + NOSE_DEPTH / 2, 0)
        .box(NOSE_DEPTH, inner_y, PLATE_T)
    )
    right_rail = (
        cq.Workplane("XY")
        .center(inner_x / 2 - NOSE_DEPTH / 2, 0)
        .box(NOSE_DEPTH, inner_y, PLATE_T)
    )
    rails = left_rail.union(right_rail)

    # --- Slot cutouts inside the rails ---
    # First nose starts at -inner_y/2 and occupies d_nose; then slot of width c_slot, etc.
    y0 = -inner_y / 2 + d_nose
    for i in range(n):
        y_center = y0 + (i + 0.5) * c_slot + i * d_nose
        cut_left = (
            cq.Workplane("XY")
            .center(-inner_x / 2 + NOSE_DEPTH / 2, y_center)
            .box(NOSE_DEPTH, c_slot, PLATE_T + 0.2)
        )
        cut_right = (
            cq.Workplane("XY")
            .center(inner_x / 2 - NOSE_DEPTH / 2, y_center)
            .box(NOSE_DEPTH, c_slot, PLATE_T + 0.2)
        )
        rails = rails.cut(cut_left).cut(cut_right)

    # Merge rails back into the frame
    frame = frame.union(rails)

    # --- Connector rectangles near the outer edges (top and bottom) ---
    x_left = -outer_x / 2 + CONNECTOR_XOFF + CONNECTOR_W / 2
    x_right = outer_x / 2 - CONNECTOR_XOFF - CONNECTOR_W / 2
    y_top = outer_y / 2 - CONNECTOR_H / 2
    y_bot = -outer_y / 2 + CONNECTOR_H / 2
    centers = [(x_left, y_top), (x_right, y_top), (x_left, y_bot), (x_right, y_bot)]

    cutter = (
        cq.Workplane("XY")
        .pushPoints(centers)
        .rect(CONNECTOR_W, CONNECTOR_H)
        .extrude(PLATE_T + 1.0, both=True)
    )
    frame = frame.cut(cutter)

    # --- Triangular chamfer wedges (cable entry) at connector openings ---
    def make_wedge_at_edge(x_edge: float, y_center: float, x_dir: int) -> cq.Workplane:
        """Create a triangular wedge extruded along the connector height."""
        y_bottom = y_center - CONNECTOR_H / 2
        tri = (
            cq.Workplane("XZ")
            .workplane(offset=y_bottom)
            .center(x_edge, -PLATE_T / 2)
            .polyline([(0, 0), (x_dir * CHAMFER_X, 0), (0, CHAMFER_Z)])
            .close()
            .extrude(CONNECTOR_H)
        )
        return tri

    wedges = None
    for (x0, y0) in centers:
        wl = make_wedge_at_edge(x0 - CONNECTOR_W / 2, y0, -1)
        wr = make_wedge_at_edge(x0 + CONNECTOR_W / 2, y0, 1)
        wedges = wl if wedges is None else wedges.union(wl)
        wedges = wedges.union(wr)

    frame = frame.cut(wedges)

    # --- Cosmetic chamfers ---
    # Small chamfer on top Y edges around connector openings
    if CONNECTOR_TOP_CH > 0:
        for (x0, y0) in centers:
            frame = (
                frame.edges(cq.NearestToPointSelector((x0 - CONNECTOR_W / 2, y0, PLATE_T / 2)))
                .edges("|Y")
                .chamfer(CONNECTOR_TOP_CH)
            )
            frame = (
                frame.edges(cq.NearestToPointSelector((x0 + CONNECTOR_W / 2, y0, PLATE_T / 2)))
                .edges("|Y")
                .chamfer(CONNECTOR_TOP_CH)
            )

    # Outer vertical corner chamfers
    if OUTER_CORNER_CH > 0:
        frame = frame.faces(">X").edges("|Z").chamfer(OUTER_CORNER_CH)
        frame = frame.faces("<X").edges("|Z").chamfer(OUTER_CORNER_CH)

    return cq.Workplane(obj=frame.val())
