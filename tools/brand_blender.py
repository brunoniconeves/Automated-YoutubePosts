"""The channel sting in 3D, rendered by Blender in the background (Eevee): a glossy rounded badge with a play mark
and the channel name in relief, popping in with an overshoot, a slow camera dolly with depth of field, a light
sweeping across the logo and out-of-focus lights drifting behind. Frames go to brand/_frames_<h|v>/; make_brand.py
turns them into the stings (bloom, fades, sound).
    blender -b -P tools/brand_blender.py -- --name "YOUR CHANNEL" --aspect h --out brand/_frames_h
"""
import argparse, math, os, random, sys
import bpy, bmesh

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--name", default="YOUR CHANNEL")
ap.add_argument("--aspect", choices=("h", "v"), default="h")
ap.add_argument("--out", required=True)
ap.add_argument("--font", default="C:/Windows/Fonts/bahnschrift.ttf")
ap.add_argument("--frames", type=int, default=240)
ap.add_argument("--samples", type=int, default=48)
ap.add_argument("--still", default="", help="comma-separated frames to render as stills (a look test) instead of the animation")
a = ap.parse_args(argv)
H = a.aspect == "h"
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        sc.render.engine = engine
        break
    except TypeError:
        pass
sc.eevee.taa_render_samples = a.samples
sc.render.resolution_x, sc.render.resolution_y = (1920, 1080) if H else (1080, 1920)
sc.render.fps = 30
sc.frame_start, sc.frame_end = 1, a.frames
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = os.path.join(os.path.abspath(a.out), "f_")
for look in ("AgX - Punchy", "Punchy"):
    try:
        sc.view_settings.look = look
        break
    except TypeError:
        pass


def node(nt, kind):
    return next(n for n in nt.nodes if n.type == kind)


def material(name, color, rough=0.25, coat=0.0, emit=0.0, emit_color=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = node(m.node_tree, "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    if "Coat Weight" in p.inputs:
        p.inputs["Coat Weight"].default_value = coat
    p.inputs["Emission Color"].default_value = (*(emit_color or color), 1)
    p.inputs["Emission Strength"].default_value = emit
    return m


def gradient_material(name, bottom, top, emit=0.05):
    m = material(name, bottom, rough=0.12, coat=1.0, emit=emit)
    nt = m.node_tree
    p = node(nt, "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*bottom, 1)
    ramp.color_ramp.elements[1].color = (*top, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Emission Color"])
    return m


def slab(name, points, depth, bevel, mat):
    """A flat shape from a polygon in the XZ plane, extruded toward the camera (-Y) and bevelled."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((x, 0, z)) for x, z in points]
    face = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    for v in [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]:
        v.co.y -= depth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width, mod.segments, mod.limit_method = bevel, 5, "ANGLE"
    ob.data.materials.append(mat)
    for poly in me.polygons:
        poly.use_smooth = True
    return ob


def rounded_rect(w, h, r, n=10):
    pts = []
    for cx, cz, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(n + 1):
            t = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(t), cz + r * math.sin(t)))
    return pts


def rounded_triangle(size, r, n=8):
    corners = [(size * 0.62, 0), (-size * 0.38, size * 0.55), (-size * 0.38, -size * 0.55)]
    pts = []
    for i, (x, z) in enumerate(corners):
        px, pz = corners[i - 1]; nx, nz = corners[(i + 1) % 3]
        a_in = math.atan2(pz - z, px - x); a_out = math.atan2(nz - z, nx - x)
        cx, cz = x + r * 1.6 * (math.cos(a_in) + math.cos(a_out)) / 2, z + r * 1.6 * (math.sin(a_in) + math.sin(a_out)) / 2
        start = math.atan2(z - cz, x - cx)
        for k in range(n + 1):
            t = start - math.radians(60) + math.radians(120) * k / n
            pts.append((cx + r * math.cos(t), cz + r * math.sin(t)))
    return pts


# The logo: badge + play mark under one parent, the name beside (16:9) or under (9:16).
purple, blue = (0.22, 0.04, 0.85), (0.02, 0.28, 0.95)
logo = bpy.data.objects.new("Logo", None)
bpy.context.collection.objects.link(logo)
badge = slab("Badge", rounded_rect(2.4, 2.4, 0.55), 0.36, 0.06, gradient_material("BadgeMat", purple, blue))
play = slab("Play", rounded_triangle(1.0, 0.08), 0.14, 0.03, material("White", (0.95, 0.95, 1.0), rough=0.15, coat=0.6, emit=0.6))
play.location = (0.08, -0.36, 0)
badge.parent = play.parent = logo

font = bpy.data.fonts.load(a.font) if os.path.exists(a.font) else None
words = a.name.upper().split()
half = (len(words) + 1) // 2
lines = [" ".join(words[:half]), " ".join(words[half:])] if len(words) > 1 else [a.name.upper()]
cu = bpy.data.curves.new("Name", "FONT")
cu.body = "\n".join(l for l in lines if l)
if font:
    cu.font = font
cu.size, cu.extrude, cu.bevel_depth, cu.bevel_resolution = 1.05, 0.06, 0.012, 3
cu.space_line = 0.9
cu.align_x = "LEFT" if H else "CENTER"
cu.align_y = "CENTER"
name = bpy.data.objects.new("Name", cu)
bpy.context.collection.objects.link(name)
name.rotation_euler = (math.radians(90), 0, 0)
name.data.materials.append(material("NameMat", (0.97, 0.97, 1.0), rough=0.25, coat=0.4, emit=0.9))
bpy.context.view_layer.update()
if H:
    logo.location = (-1.95, 0, 0)
    name.location = (-0.35, -0.1, 0.05)
else:
    logo.location = (0, 0, 1.45)
    name.location = (0, -0.1, -1.3)

# Pop-in with an overshoot and a quarter turn settling; the name slides in after.
for f, s in ((1, 0.001), (16, 1.14), (24, 0.95), (31, 1.02), (38, 1.0)):
    logo.scale = (s, s, s); logo.keyframe_insert("scale", frame=f)
for f, r in ((1, -40), (30, 6), (40, 0)):
    logo.rotation_euler = (0, 0, math.radians(r)); logo.keyframe_insert("rotation_euler", frame=f)
base = name.location.copy()
for f, dx, s in ((14, 0.0, 0.001), (22, 0.0, 0.001), (34, 0.0, 1.03), (42, 0.0, 1.0)):
    name.scale = (s, s, s); name.keyframe_insert("scale", frame=f)
name.location = base

# Background: a soft gradient wall far behind, and glowing lights drifting out of focus.
wall = bpy.data.objects.new("Wall", bpy.data.meshes.new("Wall"))
bpy.context.collection.objects.link(wall)
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=40); bm.to_mesh(wall.data)
wall.rotation_euler = (math.radians(90), 0, 0); wall.location = (0, 18, 0)
wm = bpy.data.materials.new("WallMat"); wm.use_nodes = True
nt = wm.node_tree
out = node(nt, "OUTPUT_MATERIAL")
for n in list(nt.nodes):
    if n != out: nt.nodes.remove(n)
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.01, 0.01, 0.04, 1); ramp.color_ramp.elements[1].color = (0.10, 0.03, 0.25, 1)
nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs["Surface"])
wall.data.materials.append(wm)
glow = bpy.data.objects.new("Glow", bpy.data.meshes.new("Glow"))
bpy.context.collection.objects.link(glow)
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=14); bm.to_mesh(glow.data)
glow.rotation_euler = (math.radians(90), 0, 0); glow.location = (0, 6, 0.3)
gm = bpy.data.materials.new("GlowMat"); gm.use_nodes = True; gt = gm.node_tree
go = node(gt, "OUTPUT_MATERIAL")
for n in list(gt.nodes):
    if n != go: gt.nodes.remove(n)
gem = gt.nodes.new("ShaderNodeEmission"); gtc = gt.nodes.new("ShaderNodeTexCoord"); grad = gt.nodes.new("ShaderNodeTexGradient")
grad.gradient_type = "SPHERICAL"; gmap = gt.nodes.new("ShaderNodeMapping"); gmap.inputs["Location"].default_value = (0, 0, 0)
gramp = gt.nodes.new("ShaderNodeValToRGB")
gramp.color_ramp.elements[0].color = (0, 0, 0, 1); gramp.color_ramp.elements[1].color = (0.35, 0.12, 1.0, 1)
gt.links.new(gtc.outputs["Object"], gmap.inputs["Vector"]); gt.links.new(gmap.outputs["Vector"], grad.inputs["Vector"])
gmap.inputs["Scale"].default_value = (0.085, 0.085, 0.085)
gramp.color_ramp.interpolation = "EASE"
mid = gramp.color_ramp.elements.new(0.55); mid.color = (0.12, 0.04, 0.35, 1)
gramp.color_ramp.elements[0].position = 0.2
gt.links.new(grad.outputs["Fac"], gramp.inputs["Fac"]); gt.links.new(gramp.outputs["Color"], gem.inputs["Color"])
gem.inputs["Strength"].default_value = 1.2
add = gt.nodes.new("ShaderNodeAddShader"); tp = gt.nodes.new("ShaderNodeBsdfTransparent")
gt.links.new(gem.outputs[0], add.inputs[0]); gt.links.new(tp.outputs[0], add.inputs[1]); gt.links.new(add.outputs[0], go.inputs["Surface"])
gm.blend_method = "BLEND" if hasattr(gm, "blend_method") else None
glow.data.materials.append(gm)
palette = [(0.45, 0.2, 1.0), (0.15, 0.55, 1.0), (0.9, 0.35, 1.0), (0.3, 0.9, 1.0)]
for i in range(45):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(0.12, 0.35), segments=16, ring_count=8,
                                         location=(random.uniform(-12, 12), random.uniform(5, 16), random.uniform(-8, 8)))
    b = bpy.context.object
    b.data.materials.append(material(f"Bokeh{i}", (0, 0, 0), emit=random.uniform(2, 6), emit_color=random.choice(palette)))
    z0 = b.location.z
    b.keyframe_insert("location", frame=1)
    b.location.z = z0 + random.uniform(0.4, 1.2); b.location.x += random.uniform(-0.4, 0.4)
    b.keyframe_insert("location", frame=a.frames)

# Lights: a big soft key, two coloured rims, and a thin light sweeping across the front.
def area(name, loc, size, energy, color=(1, 1, 1), sx=None):
    ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy; ld.color = color
    if sx:
        ld.shape, ld.size, ld.size_y = "RECTANGLE", sx, size
    else:
        ld.size = size
    ob = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(ob); ob.location = loc
    tr = ob.constraints.new("TRACK_TO"); tr.target = logo; tr.track_axis, tr.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
    return ob
area("Key", (-5, -7, 5), 6, 450)
area("RimL", (-6, 4, 2), 3, 1200, (0.6, 0.3, 1.0))
area("RimR", (6, 4, -1), 3, 1200, (0.2, 0.7, 1.0))
sweep = area("Sweep", (-9, -4, 0), 9, 1800, sx=0.35)
sweep.keyframe_insert("location", frame=44)
sweep.location.x = 9; sweep.keyframe_insert("location", frame=92)
world = bpy.data.worlds.new("World"); world.use_nodes = True
node(world.node_tree, "BACKGROUND").inputs["Color"].default_value = (0.005, 0.005, 0.02, 1)
sc.world = world

# Camera: a slow dolly in with a slight drift, focused on the logo, shallow depth of field.
cd = bpy.data.cameras.new("Cam"); cd.lens = 35; cd.sensor_fit = "HORIZONTAL"
cam = bpy.data.objects.new("Cam", cd); bpy.context.collection.objects.link(cam); sc.camera = cam
aim = bpy.data.objects.new("Aim", None); bpy.context.collection.objects.link(aim); aim.location = (0, 0, 0.1)
tr = cam.constraints.new("TRACK_TO"); tr.target = aim; tr.track_axis, tr.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
cd.dof.use_dof = True; cd.dof.focus_object = aim; cd.dof.aperture_fstop = 0.35
try:
    sc.eevee.bokeh_max_size = 400
except AttributeError:
    pass
d = 8.6 if H else 8.4
cam.location = (1.2, -d * 1.18, 0.6); cam.keyframe_insert("location", frame=1)
cam.location = (0.0, -d, 0.15); cam.keyframe_insert("location", frame=a.frames)
for fc in (getattr(cam.animation_data.action, "fcurves", None) or []):
    for k in fc.keyframe_points:
        k.interpolation = "SINE"; k.easing = "EASE_OUT"

if a.still:
    for f in [int(x) for x in a.still.split(",")]:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(os.path.abspath(a.out), f"still_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
print("frames:", a.out)
