# models/bone_model.py
import cadquery as cq
from cadquery import selectors as s

# ===== Default parameters =====
# 'b' is the total tip-to-tip length, including both dovetails.
DEFAULTS = dict(
    b=80.0,         # total tip-to-tip length [mm]
    thickness=5.0,  # part thickness (Z) [mm]
    x_out=7.0,      # width at the dovetail tip
    x_mid=5.0,      # width at the inner shoulder
    x_in=3.0,       # narrow step between shoulder and tip
    l_dovetail=8.0, # dovetail length per side (shoulder -> tip)
    bone_w=10.0,    # overall body width in X (informational)
    edge_ch=0.5     # chamfer size on selected edges
)


def make_bone(**params) -> cq.Workplane:
    """
    Build the 'bone' connector. The overall length 'b' is measured tip-to-tip
    and already includes both dovetails.

    Profile:
        Symmetric around X=0 in the XY plane. The 2D outline follows points P1..P13,
        then is extruded along +Z by 'thickness'.

    Chamfers:
        Applied on the four short edge segments around the inner shoulder transitions:
        (P2–P3), (P6–P7), (P8–P9), (P12–P13) on both top and bottom faces.

    Returns:
        CadQuery Workplane containing the final solid.
    """
    p = {**DEFAULTS, **params}
    b = float(p["b"])
    THICKNESS = float(p["thickness"])

    X_OUT = float(p["x_out"])
    X_MID = float(p["x_mid"])
    X_IN = float(p["x_in"])
    L_DOVETAIL = float(p["l_dovetail"])
    EDGE_CH = float(p["edge_ch"])

    # 'b' is the total length -> half length:
    half_total = b / 2.0

    # Keep dovetail length within sensible bounds to avoid degenerate geometry.
    if L_DOVETAIL <= 0 or L_DOVETAIL >= half_total:
        L_DOVETAIL = max(0.1, min(half_total * 0.45, L_DOVETAIL))

    # Tip lies at ±half_total; inner shoulder lies L_DOVETAIL before the tip.
    Y_OUTER = half_total          # tip Y
    Y_INNER = half_total - L_DOVETAIL  # shoulder Y

    # 2D outline (XY), symmetric about X=0
    pts = [
        ( X_OUT,  Y_OUTER),  # P1
        (-X_OUT,  Y_OUTER),  # P2
        (-X_IN,   Y_INNER),  # P3
        (-X_MID,  Y_INNER),  # P4
        (-X_MID, -Y_INNER),  # P5
        (-X_IN,  -Y_INNER),  # P6
        (-X_OUT, -Y_OUTER),  # P7
        ( X_OUT, -Y_OUTER),  # P8
        ( X_IN,  -Y_INNER),  # P9
        ( X_MID, -Y_INNER),  # P10
        ( X_MID,  Y_INNER),  # P11
        ( X_IN,   Y_INNER),  # P12
        ( X_OUT,  Y_OUTER),  # P13
    ]

    wp = cq.Workplane("XY")
    solid = wp.polyline(pts).close().extrude(THICKNESS)

    # Target midpoints near the short shoulder edges for chamfer selection
    m23   = ((-X_OUT + -X_IN)/2.0,   ( Y_OUTER +  Y_INNER)/2.0)
    m67   = ((-X_IN  + -X_OUT)/2.0,  (-Y_INNER + -Y_OUTER)/2.0)
    m89   = (( X_OUT +  X_IN)/2.0,   (-Y_OUTER + -Y_INNER)/2.0)
    m1213 = (( X_IN  +  X_OUT)/2.0,  ( Y_INNER +  Y_OUTER)/2.0)

    if EDGE_CH > 0:
        # Top face chamfers
        for (mx, my) in (m23, m67, m89, m1213):
            solid = (
                solid.faces(">Z")
                     .edges(s.NearestToPointSelector((mx, my, THICKNESS/2)))
                     .chamfer(EDGE_CH)
            )
        # Bottom face chamfers
        for (mx, my) in (m23, m67, m89, m1213):
            solid = (
                solid.faces("<Z")
                     .edges(s.NearestToPointSelector((mx, my, -THICKNESS/2)))
                     .chamfer(EDGE_CH)
            )

    return cq.Workplane(obj=solid.val())
