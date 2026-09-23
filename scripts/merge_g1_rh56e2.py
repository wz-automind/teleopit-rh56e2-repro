#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

LEFT_MOUNT_POS = "0.0415 0 0"
LEFT_MOUNT_QUAT = "0.7071067812 0 0 0.7071067812"
RIGHT_MOUNT_POS = "0.0415 0 0"
RIGHT_MOUNT_QUAT = "0 0.7071067812 -0.7071067812 0"
WRIST_BODY = {"left": "left_wrist_yaw_link", "right": "right_wrist_yaw_link"}

def find_body(root, name):
    for body in root.iter("body"):
        if body.get("name") == name:
            return body
    wristish = [b.get("name") for b in root.iter("body") if "wrist" in (b.get("name") or "").lower()]
    raise RuntimeError(f"Body {name!r} not found. Wrist-like bodies: {wristish}")

def ensure_child(root, tag):
    elem = root.find(tag)
    if elem is None:
        elem = ET.SubElement(root, tag)
    return elem

def compiler_mesh_dir(xml_root, xml_path):
    compiler = xml_root.find("compiler")
    meshdir = compiler.get("meshdir", "") if compiler is not None else ""
    return (xml_path.parent / meshdir).resolve()

def copy_hand(g1_root, g1_xml, hand_xml, side):
    htree = ET.parse(hand_xml)
    hroot = htree.getroot()
    hand_world = hroot.find("worldbody")
    if hand_world is None:
        raise RuntimeError(f"No worldbody in {hand_xml}")
    source_root = hand_world.find("./body[@name='hand_root']")
    if source_root is None:
        bodies = hand_world.findall("body")
        if len(bodies) != 1:
            raise RuntimeError(f"Expected one hand root body, found {len(bodies)}")
        source_root = bodies[0]

    mounted = copy.deepcopy(source_root)
    mounted.set("name", f"rh56e2_{side}_mount")
    if side == "left":
        mounted.set("pos", LEFT_MOUNT_POS)
        mounted.set("quat", LEFT_MOUNT_QUAT)
    else:
        mounted.set("pos", RIGHT_MOUNT_POS)
        mounted.set("quat", RIGHT_MOUNT_QUAT)

    # The generated hand MJCF contains visual/collision geom pairs.  A
    # simulated G1 does not need hand self-collision for policy stability,
    # and those pairs overlap at startup.  Keep the hand visible but make
    # every RH56E2 geom non-colliding.
    for geom in mounted.iter("geom"):
        geom.set("contype", "0")
        geom.set("conaffinity", "0")

    # Add modest damping/armature to the newly embedded joints.  The source
    # URDF has almost no joint damping, which makes the position actuators
    # numerically stiff when attached to the moving wrists.
    for joint in mounted.iter("joint"):
        joint.set("damping", joint.get("damping", "0.05"))
        joint.set("armature", joint.get("armature", "0.001"))

    g1_asset = ensure_child(g1_root, "asset")
    hand_asset = hroot.find("asset")
    hand_meshdir = compiler_mesh_dir(hroot, hand_xml)
    g1_meshdir = compiler_mesh_dir(g1_root, g1_xml)
    out_subdir = g1_meshdir / "rh56e2" / side
    out_subdir.mkdir(parents=True, exist_ok=True)

    mesh_name_map = {}
    if hand_asset is not None:
        for mesh in hand_asset.findall("mesh"):
            old_name, file_attr = mesh.get("name"), mesh.get("file")
            if not old_name or not file_attr:
                continue
            source_file = (hand_meshdir / file_attr).resolve()
            if not source_file.exists():
                raise FileNotFoundError(source_file)
            new_name = f"rh56e2_{side}_{old_name}"
            mesh_name_map[old_name] = new_name
            dest = out_subdir / Path(file_attr).name
            shutil.copy2(source_file, dest)
            nm = copy.deepcopy(mesh)
            nm.set("name", new_name)
            nm.set("file", f"rh56e2/{side}/{dest.name}")
            g1_asset.append(nm)

    for geom in mounted.iter("geom"):
        ref = geom.get("mesh")
        if ref in mesh_name_map:
            geom.set("mesh", mesh_name_map[ref])

    find_body(g1_root, WRIST_BODY[side]).append(mounted)

    g1_act = ensure_child(g1_root, "actuator")
    hact = hroot.find("actuator")
    if hact is not None:
        for item in list(hact):
            g1_act.append(copy.deepcopy(item))

    heq = hroot.find("equality")
    if heq is not None and len(heq):
        geq = ensure_child(g1_root, "equality")
        for item in list(heq):
            geq.append(copy.deepcopy(item))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--g1", required=True)
    ap.add_argument("--left", required=True)
    ap.add_argument("--right", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    g1 = Path(a.g1).resolve()
    left = Path(a.left).resolve()
    right = Path(a.right).resolve()
    out = Path(a.output).resolve()

    tree = ET.parse(g1)
    root = tree.getroot()
    # The stock G1 rubber-hand collision capsules occupy the same space as
    # the attached RH56E2 bases.  Disable only those two replacement geoms.
    for geom_name in ("left_hand_collision", "right_hand_collision"):
        for geom in root.iter("geom"):
            if geom.get("name") == geom_name:
                geom.set("contype", "0")
                geom.set("conaffinity", "0")
                break
    original_nu = len(root.find("actuator") or [])
    copy_hand(root, g1, left, "left")
    copy_hand(root, g1, right, "right")
    tree.write(out, encoding="unicode", xml_declaration=True)

    import mujoco
    m = mujoco.MjModel.from_xml_path(str(out))
    expected = [
        "L_pinky_proximal_joint","L_ring_proximal_joint","L_middle_proximal_joint",
        "L_index_proximal_joint","L_thumb_proximal_pitch_joint","L_thumb_proximal_yaw_joint",
        "R_pinky_proximal_joint","R_ring_proximal_joint","R_middle_proximal_joint",
        "R_index_proximal_joint","R_thumb_proximal_pitch_joint","R_thumb_proximal_yaw_joint",
    ]
    actuated = []
    for aid in range(m.nu):
        jid = int(m.actuator_trnid[aid][0])
        actuated.append(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, jid) if jid >= 0 else None)
    missing = [x for x in expected if x not in actuated]
    print("base actuator count:", original_nu)
    print("combined nq/nv/nu:", m.nq, m.nv, m.nu)
    if original_nu < 29 or m.nu < 41 or missing:
        raise RuntimeError(f"Validation failed: original_nu={original_nu}, nu={m.nu}, missing={missing}")
    print("PASS:", out)

if __name__ == "__main__":
    main()
