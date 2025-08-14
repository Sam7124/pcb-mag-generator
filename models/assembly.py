# models/assembly.py

import cadquery as cq
from models.frame_model import make_frame, PLATE_T
from models.bone_model import make_bone, DEFAULTS as BONE_DEFAULTS

BONE_X_INSET = 11.0  # inset bones by 11 mm toward the center along X

def make_assembly(a: float, c: float, d: float, n: int, b: float):
    """Build the full assembly:
    - Frame 1 bottom: underside at Z = 0 (its center ends up at +PLATE_T/2).
    - Frame 2 top: mirrored in Z and translated so its top face lies at Z = b.
    - 4 upright bones at the four XY corners of Frame 1; each bone is inset by BONE_X_INSET along X.
      For the two lower corners (negative Y) shift the bones by +bone_thickness along Y so they fit inside.
    """
    # Base frames
    frame_raw = make_frame(a, c, d, n)  # centered around origin, thickness ±PLATE_T/2
    frame1 = frame_raw.translate((0, 0, PLATE_T/2))  # bottom frame: underside at Z=0
    frame2 = frame_raw.mirror(mirrorPlane="XY").translate((0, 0, b - PLATE_T/2))  # top frame: top at Z=b

    # Outer dimensions from frame1 bounding box
    f_bb = cq.Compound.makeCompound([frame1.val()]).BoundingBox()
    outer_x = f_bb.xlen
    outer_y = f_bb.ylen

    # Bones stand upright: rotate bone around X so its original Y-length becomes Z-length
    bone_raw = make_bone(b=b).rotate((0, 0, 0), (1, 0, 0), 90)
    zc = b / 2.0  # bone center at mid-height so it spans Z=0..b

    # Four XY corners of the bottom frame
    corners = [
        (+outer_x/2.0, +outer_y/2.0),
        (-outer_x/2.0, +outer_y/2.0),
        (-outer_x/2.0, -outer_y/2.0),
        (+outer_x/2.0, -outer_y/2.0),
    ]

    # Bone thickness (used to nudge the two bottom corners up along Y)
    bone_thickness = float(BONE_DEFAULTS.get("thickness", 5.0))

    placements = []
    placements.append((frame1, (0.0, 0.0, 0.0), (0, 0, 0)))
    placements.append((frame2, (0.0, 0.0, 0.0), (0, 0, 0)))

    for (x, y) in corners:
        x_in = x - BONE_X_INSET if x > 0 else x + BONE_X_INSET
        y_in = y + bone_thickness if y < 0 else y
        placements.append((bone_raw, (x_in, y_in, zc), (0, 0, 0)))

    return placements
