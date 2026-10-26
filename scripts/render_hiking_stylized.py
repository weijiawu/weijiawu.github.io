"""Original procedural Blender hiking short; no stock footage or external models.

PYTHONPATH=/path/to/bpy python scripts/render_hiking_stylized.py --preview
PYTHONPATH=/path/to/bpy python scripts/render_hiking_stylized.py
The feet use a planted stance and a two-segment inverse-kinematic leg solver.
"""
import argparse
import math
import random
from pathlib import Path

# demo:start imports
import bpy
# demo:end imports
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--preview', action='store_true')
parser.add_argument('--validate', action='store_true', help='Check parallax and loop continuity without rendering')
parser.add_argument('--frame', type=int, default=20)
parser.add_argument('--start', type=int, default=0)
parser.add_argument('--end', type=int, default=288)
parser.add_argument('--output', type=Path, default=Path('/private/tmp/weijia-snow-frames'))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
ROOT = Path(__file__).resolve().parents[1]
FPS, DURATION, SPEED, PERIOD = 24, 12, .65, 7.8
SLOPE = .065
random.seed(41)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
# demo:start engine
scene.render.engine = 'CYCLES'
# demo:end engine
scene.cycles.samples = 20
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.render.use_persistent_data = True
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'METAL'
    if any(d.use for d in prefs.devices):
        scene.cycles.device = 'GPU'
except Exception:
    pass
scene.render.resolution_x = 864
scene.render.resolution_y = 576
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.render.film_transparent = False


def material(name, color, roughness=.7):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    shader = m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    return m


clay = {
    'jacket': material('Ochre canvas', (.72, .34, .065)),
    'trim': material('Golden seams', (.92, .56, .16)),
    'pants': material('Deep blue fabric', (.075, .16, .19)),
    'boot': material('Chocolate hiking boots', (.16, .095, .062)),
    'sole': material('Rubber soles', (.047, .057, .054)),
    'skin': material('Warm clay skin', (.64, .36, .21)),
    'cap': material('Teal cap', (.045, .23, .25)),
    'pack': material('Terracotta canvas', (.57, .18, .105)),
    'strap': material('Dark woven straps', (.18, .105, .065)),
    'eye': material('Eyes', (.035, .031, .029)),
    'trail': material('Packed blue-white snow', (.66, .80, .88)),
    'snowfield': material('Untouched snowfield', (.83, .91, .96)),
    'pine': material('Pine green', (.075, .23, .19)),
    'pine_light': material('Pine tips', (.13, .33, .25)),
    'rock': material('Cool slate', (.34, .42, .40)),
    'peak': material('Blue slate mountain faces', (.24, .40, .54)),
    'snow': material('Fresh white powder', (.92, .97, 1.0)),
    'ice': material('Glacial blue shadow', (.51, .70, .84)),
    'print': material('Compressed boot prints', (.39, .58, .70)),
    'wood': material('Trail sign wood', (.29, .17, .09)),
    'letter': material('Sign lettering', (.94, .83, .59)),
}


def smooth(o):
    if o.type == 'MESH':
        for face in o.data.polygons:
            face.use_smooth = True
    return o


def ball(name, location, scale, mat, segments=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=12, location=location)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(mat)
    return smooth(o)


def box(name, location, scale, mat, bevel=.05):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    b = o.modifiers.new('Soft edges', 'BEVEL')
    b.width = bevel
    b.segments = 4
    o.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return o


def segment(name, a, b, radius, mat):
    o = ball(name, (0, 0, 0), (1, 1, 1), mat)
    place_segment(o, a, b, radius)
    return o


def place_segment(o, a, b, radius):
    a, b = Vector(a), Vector(b)
    o.location = (a + b) / 2
    o.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    o.scale = (radius, radius, (b - a).length / 2 + radius * .45)


def parent_keep(o, parent):
    bpy.context.view_layer.update()
    matrix = o.matrix_world.copy()
    o.parent = parent
    o.matrix_world = matrix
    return o


def empty(name, location=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    scene.collection.objects.link(o)
    o.location = location
    return o


def cone(name, location, radius, depth, mat, vertices=9):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius, radius2=0, depth=depth, location=location)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    bevel = o.modifiers.new('Soft ridges', 'BEVEL')
    bevel.width = .035
    bevel.segments = 2
    o.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return o


def height(x):
    return SLOPE * x


# Perspective tracking camera: every world object translates at the same
# speed, and distance creates the slower motion of the mountain layers.
# demo:start snow
ground = box(
    'Snowfield', (0, 3, -.24),
    (200, 24, .4), clay['snowfield'], .1,
)
ground.rotation_euler[1] = -math.atan(SLOPE)
# demo:end snow
trail = box('Packed snow trail', (0, 0, -.035), (200, 1.4, .09), clay['trail'], .06)
trail.rotation_euler[1] = -math.atan(SLOPE)

moving = []


def add_moving(o, x, y, z=0):
    o.location = (x, y, z + height(x))
    moving.append((o, x, y, z))


def mountain(name, x, y, tall, width, seed):
    rng = random.Random(seed)
    count = 9
    vertices = []
    # A broken snow line and asymmetric summit make each ridge less geometric.
    radii = [rng.uniform(.82, 1.14) for _ in range(count)]
    for i in range(count):
        angle = math.tau * i / count
        vertices.append((math.cos(angle) * width * radii[i], math.sin(angle) * width * .55 * radii[i], -.12))
    for i in range(count):
        angle = math.tau * i / count
        z = tall * rng.uniform(.32, .55)
        fraction = 1 - z / tall
        vertices.append((math.cos(angle) * width * radii[i] * fraction + .11, math.sin(angle) * width * .55 * radii[i] * fraction, z))
    vertices.append((width * .17, -.10, tall))
    faces, mats = [], []
    for i in range(count):
        j = (i + 1) % count
        faces.extend([(i, j, count + j), (i, count + j, count + i), (count + i, count + j, 2 * count)])
        mats.extend([0, 1 if i % 3 else 0, 2 if i % 4 else 1])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    for mat in [clay['peak'], clay['ice'], clay['snow']]:
        obj.data.materials.append(mat)
    for polygon, index in zip(mesh.polygons, mats):
        polygon.material_index = index
    bevel = obj.modifiers.new('Soft ridge edges', 'BEVEL')
    bevel.width = .018
    bevel.segments = 2
    obj.modifiers.new('Mountain face normals', 'WEIGHTED_NORMAL')
    add_moving(obj, x, y, -.12)


# Both layers are part of the moving world. The perspective camera gives
# the far ridge less screen displacement than the nearer firs and snowbanks.
for i, (x, y, tall, width) in enumerate([
    (-2.7, 8.7, 3.2, 2.3), (1.25, 9.4, 3.8, 2.5),
    (-2.0, 5.8, 2.35, 1.8), (2.0, 6.4, 2.85, 2.0),
]):
    mountain('Distant snow massif' if y > 8 else 'Near snow ridge', x, y, tall, width, 82 + i)

# Snow-covered rocks and drifts repeat outside the camera boundaries.
for i in range(12):
    x = -PERIOD / 2 + random.random() * PERIOD
    y = random.choice([-1, 1]) * random.uniform(.9, 1.9)
    size = random.uniform(.07, .18)
    rock = empty('Snow-covered rock')
    base = ball('Exposed slate', (0, 0, size * .4), (size * 1.3, size, size * .65), clay['rock'], 12)
    base.parent = rock
    cap = ball('Powder on rock', (-.01, 0, size * .73), (size * 1.22, size * .97, size * .36), clay['snow'], 16)
    cap.parent = rock
    add_moving(rock, x, y)
for i in range(14):
    x = -PERIOD / 2 + random.random() * PERIOD
    y = random.choice([-1, 1]) * random.uniform(.9, 1.9)
    size = random.uniform(.15, .34)
    drift = ball('Soft snowdrift', (0, 0, 0), (size * 1.6, size, size * .42), clay['snow'], 20)
    add_moving(drift, x, y, -.02)
for i, x in enumerate([-3.6, -1.7, .7, 2.9]):
    tree = empty('Snow-laden fir')
    size = [.82, 1.25, 1.05, .85][i]
    trunk = box('Fir trunk', (0, 0, .28 * size), (.11, .11, .56 * size), clay['wood'], .02)
    trunk.parent = tree
    for level in range(3):
        center = (.57 + level * .25) * size
        radius = (.46 - level * .095) * size
        branch = cone('Evergreen rim', (0, 0, center), radius, .75 * size, clay['pine'])
        branch.parent = tree
        snow = cone('Heavy snow on fir', (0, 0, center + .0675 * size), radius * .86, .615 * size, clay['snow'])
        snow.parent = tree
    add_moving(tree, x, 2.25 + (i % 2) * .65)

# Alternating prints are revealed only behind the hiker; their spacing and
# movement match the planted boots rather than drifting over the snow.
for i in range(20):
    x = .2418 + (i - 10) * .39
    y = -.155 if i % 2 == 0 else .155
    imprint = ball('Boot impression', (0, 0, 0), (.13, .075, .006), clay['print'], 16)
    imprint.rotation_euler[1] = -math.atan(SLOPE)
    add_moving(imprint, x, y, .012)


def lettering(body, location, size, parent):
    curve = bpy.data.curves.new(body, 'FONT')
    curve.body = body
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    curve.size = size
    curve.extrude = .001
    o = bpy.data.objects.new(body, curve)
    scene.collection.objects.link(o)
    o.data.materials.append(clay['letter'])
    o.location = location
    o.rotation_euler = (math.pi / 2, 0, 0)
    o.parent = parent
    return o


sign = empty('Summit sign')
post = box('Signpost', (0, 0, .66), (.09, .09, 1.32), clay['wood'], .02)
post.parent = sign
for name, z, w in [('SUMMIT  >', 1.3, .95), ('404 m', 1.06, .65)]:
    panel = box('Carved trail marker', (0, 0, z), (w, .08, .21), clay['wood'], .035)
    panel.parent = sign
    lettering(name, (0, -.046, z), .125, sign)
snow_lip = box('Snow on sign', (0, 0, 1.415), (.96, .12, .05), clay['snow'], .025)
snow_lip.parent = sign
add_moving(sign, 2.7, .98)

# Repeat neighboring tiles outside the camera as well. A tree or a rock leaving
# one tile is replaced by its identical neighbor, without popping at the edge.
def clone_tree(source, parent=None):
    clone = source.copy()
    scene.collection.objects.link(clone)
    clone.parent = parent
    for child in source.children:
        clone_tree(child, clone)
    return clone


tiled_moving = []
for source, x, y, z in moving:
    offsets = [-2 * PERIOD, -PERIOD, 0, PERIOD, 2 * PERIOD] if y > 5 else [-PERIOD, 0, PERIOD]
    for offset in offsets:
        tiled_moving.append((clone_tree(source) if offset else source, x, y, z, offset))

# A rounded, intentionally stylized hiker; no scanned or stock human model.
body = empty('Hiker torso')
torso = ball('Canvas jacket', (.025, 0, 1.38), (.215, .27, .34), clay['jacket'])
parent_keep(torso, body)
hipmesh = ball('Trouser hips', (0, 0, 1.03), (.18, .245, .17), clay['pants'])
parent_keep(hipmesh, body)
for y in [-.15, .15]:
    curve = bpy.data.curves.new('Curved shoulder webbing', 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = .022
    curve.bevel_resolution = 3
    spline = curve.splines.new('BEZIER')
    points = [(-.14, y, 1.65), (.08, y, 1.65), (.19, y, 1.52), (.216, y, 1.36), (.17, y, 1.20)]
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = point.handle_right_type = 'AUTO'
    strap = bpy.data.objects.new('Shoulder webbing', curve)
    scene.collection.objects.link(strap)
    strap.data.materials.append(clay['strap'])
    parent_keep(strap, body)
zipper = box('Jacket zipper', (.231, 0, 1.39), (.012, .016, .40), clay['trim'], .004)
parent_keep(zipper, body)
head = empty('Head')
head.parent = body
for o in [ball('Neck', (.035, 0, 1.72), (.085, .085, .12), clay['skin']),
          ball('Head sculpt', (.055, 0, 1.91), (.205, .185, .235), clay['skin']),
          ball('Nose', (.249, 0, 1.91), (.063, .055, .053), clay['skin']),
          ball('Cap crown', (.035, 0, 2.085), (.217, .198, .115), clay['cap']),
          ball('Knitted beanie cuff', (.035, 0, 2.04), (.222, .204, .060), clay['cap']),
          ball('Beanie pompom', (.015, 0, 2.21), (.065, .065, .065), clay['cap']),
          ball('Winter neck warmer', (.035, 0, 1.735), (.12, .12, .055), clay['cap'])]:
    parent_keep(o, head)
for y in [-1, 1]:
    parent_keep(ball('Ear', (.015, y * .183, 1.91), (.06, .045, .075), clay['skin']), head)
    parent_keep(ball('Eye', (.226, y * .083, 1.95), (.013, .016, .021), clay['eye']), head)
pack = empty('Backpack bounce')
pack.parent = body
for o in [box('Rounded rucksack', (-.25, 0, 1.43), (.24, .43, .53), clay['pack'], .11),
          box('Rucksack pocket', (-.39, 0, 1.33), (.10, .34, .24), clay['pack'], .05),
          box('Rucksack flap', (-.27, 0, 1.69), (.30, .44, .08), clay['pack'], .04),
          box('Sleeping mat', (-.25, 0, 1.10), (.20, .53, .15), clay['cap'], .07)]:
    parent_keep(o, pack)
for y in [-.12, .12]:
    parent_keep(box('Backpack straps', (-.448, y, 1.44), (.018, .027, .33), clay['strap'], .006), pack)

limbs = []
for side in [-1, 1]:
    upper = segment('Trouser thigh', (0, 0, 0), (0, 0, 1), .108, clay['pants'])
    lower = segment('Trouser shin', (0, 0, 0), (0, 0, 1), .085, clay['pants'])
    knee = ball('Soft knee', (0, 0, 0), (.104, .104, .104), clay['pants'])
    shoe = empty('Boot')
    for o in [box('Leather boot', (.075, 0, .105), (.32, .20, .18), clay['boot'], .065),
              box('Rubber tread', (.075, 0, .035), (.35, .215, .06), clay['sole'], .025),
              box('Boot lace', (.12, 0, .198), (.09, .10, .012), clay['trim'], .009)]:
        o.parent = shoe
    arm = segment('Jacket sleeve upper', (0, 0, 0), (0, 0, 1), .10, clay['jacket'])
    forearm = segment('Jacket sleeve lower', (0, 0, 0), (0, 0, 1), .078, clay['jacket'])
    elbow = ball('Sleeve elbow', (0, 0, 0), (.086, .086, .086), clay['jacket'])
    hand = ball('Winter mitten', (0, 0, 0), (.075, .065, .09), clay['cap'])
    limbs.append((side, upper, lower, knee, shoe, arm, forearm, elbow, hand))


def solve_joint(a, b, length_a, length_b, bend):
    a, b = Vector(a), Vector(b)
    delta = b - a
    distance = min(delta.length, length_a + length_b - .001)
    direction = delta.normalized()
    along = (length_a ** 2 - length_b ** 2 + distance ** 2) / (2 * distance)
    perpendicular = Vector(bend) - direction * Vector(bend).dot(direction)
    perpendicular.normalize()
    return a + direction * along + perpendicular * math.sqrt(max(0, length_a ** 2 - along ** 2))


def smoothstep(value):
    return value * value * (3 - 2 * value)


def walk_cycle(t):
    phase = (t / 1.2) % 1
    bob = .018 * math.cos(phase * math.tau * 2)
    sway = .024 * math.sin(phase * math.tau)
    body.location = (.025 * math.sin(phase * math.tau * 2), sway, bob)
    body.rotation_euler = (0, .055, .035 * math.sin(phase * math.tau))
    head.rotation_euler[2] = .055 * math.sin(phase * math.tau)
    pack.location.z = -.012 * math.cos(phase * math.tau * 2 - .6)
    for side, upper, lower, kneemesh, shoe, arm, forearm, elbowmesh, hand in limbs:
        p = (phase + (0 if side == -1 else .5)) % 1
        stance = .62
        front = SPEED * 1.2 * stance / 2
        if p < stance:
            foot_x = front - SPEED * 1.2 * p
            lift = 0
        else:
            swing = (p - stance) / (1 - stance)
            foot_x = -front + 2 * front * smoothstep(swing)
            lift = .135 * math.sin(math.pi * swing)
        foot_y = side * .155
        shoe.location = (foot_x, foot_y, height(foot_x) + lift)
        shoe.rotation_euler[1] = -math.atan(SLOPE)
        hip = Vector((body.location.x + .045, foot_y + sway, 1.045 + bob))
        ankle = Vector((foot_x, foot_y, height(foot_x) + lift + .16))
        # demo:start gait
        knee = solve_joint(
            hip, ankle, .49, .46, (1, 0, 0),
        )
        place_segment(upper, hip, knee, .108)
        place_segment(lower, knee, ankle, .085)
        kneemesh.location = knee
        # demo:end gait
        shoulder = Vector((.11 + body.location.x, side * .275 + sway, 1.57 + bob))
        swing = -.21 * math.cos(p * math.tau)
        wrist = Vector((.15 + swing, side * .32 + sway, 1.04 + bob + .025 * math.sin(p * math.tau)))
        elbow = solve_joint(shoulder, wrist, .31, .29, (-1, 0, 0))
        place_segment(arm, shoulder, elbow, .10)
        place_segment(forearm, elbow, wrist, .078)
        elbowmesh.location = elbow
        hand.location = wrist + Vector((.012, 0, -.035))


def render_frame(frame):
    t = frame / FPS
    walk_cycle(t)
    for o, x, y, z, offset in tiled_moving:
        # demo:start parallax
        position = (
            (x - SPEED * t + PERIOD / 2)
            % PERIOD - PERIOD / 2 + offset
        )
        o.location = (
            position, y, z + height(position)
        )
        # demo:end parallax
        if o.name.startswith('Boot impression'):
            o.hide_render = position > -.20
    scene.frame_set(frame)
    bpy.context.view_layer.update()


world = bpy.data.worlds.new('Clear winter sky')
world.use_nodes = True
scene.world = world
world.node_tree.nodes.get('Background').inputs['Color'].default_value = (.56, .74, .89, 1)
world.node_tree.nodes.get('Background').inputs['Strength'].default_value = .65
bpy.ops.object.light_add(type='AREA', location=(-3, -4, 7))
key = bpy.context.object
key.data.energy = 750
key.data.shape = 'DISK'
key.data.size = 5
key.data.color = (1, .91, .80)
key.rotation_euler = (Vector((0, 0, 1)) - key.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.light_add(type='AREA', location=(2, 4, 5))
rim = bpy.context.object
rim.data.energy = 600
rim.data.size = 4
rim.data.color = (.68, .85, 1)
rim.rotation_euler = (Vector((0, 0, 1)) - rim.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add(location=(4.7, -8.5, 3.9))
camera = bpy.context.object
scene.camera = camera
# demo:start camera
camera.data.type = 'PERSP'
camera.data.lens = 70
# demo:end camera
camera.rotation_euler = (Vector((.2, .5, 1.15)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.dof.use_dof = True
camera.data.dof.focus_distance = (Vector((0, 0, 1.1)) - camera.location).length
camera.data.dof.aperture_fstop = 16

if args.validate:
    from bpy_extras.object_utils import world_to_camera_view
    tracked = []
    for prefix in ['Snow-covered rock', 'Snow-laden fir', 'Distant snow massif']:
        tracked.append(next(o for o, x, y, z in moving if o.name.startswith(prefix) and x > .5))
    render_frame(0)
    start = [world_to_camera_view(scene, camera, o.matrix_world.translation).x for o in tracked]
    loop_start = [(o.location.copy(), o.hide_render) for o, *_ in tiled_moving]
    render_frame(12)
    displacement = [abs(world_to_camera_view(scene, camera, o.matrix_world.translation).x - x) * scene.render.resolution_x for o, x in zip(tracked, start)]
    assert displacement[0] > displacement[1] > displacement[2] > 0, displacement
    print('Half-second screen displacement, near / middle / far:', displacement, flush=True)
    render_frame(FPS * DURATION)
    for (o, *_), (position, hidden) in zip(tiled_moving, loop_start):
        assert (o.location - position).length < .00001 and o.hide_render == hidden, o.name
    print('PASS: perspective parallax and every scenery object repeat exactly after 12 seconds.', flush=True)
elif args.preview:
    render_frame(args.frame)
    scene.render.filepath = str(args.output / 'preview.png')
    bpy.ops.render.render(write_still=True)
else:
    for frame in range(args.start, args.end):
        destination = args.output / f'{frame:04d}.png'
        if destination.exists():
            continue
        # demo:start render
        render_frame(frame)
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True)
        # demo:end render
        if frame % FPS == 0:
            print(f'PROGRESS {frame}/{FPS * DURATION}', flush=True)
