import cadquery as cq, trimesh
W, D, H, t = 400.0, 200.0, 500.0, 1.5
door = cq.Workplane('XZ').rect(W - 4, H - 4).extrude(t)
door = door.union(cq.Workplane('XZ').rect(W - 4, H - 4).rect(W - 4 - 2 * t, H - 4 - 2 * t).extrude(20))
door = door.translate((0, -D / 2 - 1, 0))
lock = cq.Workplane('XZ').center(W / 2 - 40, 0).rect(22, 90).extrude(-14).edges('|Y').fillet(4).translate((0, -D / 2 - 1 - t, 0))
for n, p in (('door_c', door), ('lock_c', lock)):
    cq.exporters.export(p, f'{n}.stl', tolerance=0.08, angularTolerance=0.12)
    trimesh.load(f'{n}.stl').export(f'{n}.glb')
print('ok')
