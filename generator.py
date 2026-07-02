from __future__ import annotations

import hashlib
import io
import math
import urllib.request
from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ImageFeatures:
    colors: list[str]
    aspect: float
    brightness: float
    saturation: float
    edge_density: float
    vertical_symmetry: float
    color_variance: float
    warm_bias: float
    dominant_ratio: float
    diagonal_energy: float
    seed_value: int


def _stable_int(value: str, seed: int) -> int:
    data = f"{value}:{seed}".encode("utf-8")
    return int(hashlib.sha256(data).hexdigest()[:12], 16)


def _download_image(url: str, timeout: float = 20.0) -> Image.Image:
    req = urllib.request.Request(url, headers={"User-Agent": "404gen-color-primitives/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = response.read(8 * 1024 * 1024)
    return Image.open(io.BytesIO(payload)).convert("RGB")


def _hex(rgb: np.ndarray) -> str:
    r, g, b = [int(max(0, min(255, x))) for x in rgb]
    return f"0x{r:02x}{g:02x}{b:02x}"


def _fallback_features(stem: str, seed: int) -> ImageFeatures:
    base = _stable_int(stem, seed)
    colors = []
    for i in range(4):
        v = _stable_int(f"{stem}:{i}", seed)
        colors.append(f"0x{(v >> 16) & 255:02x}{(v >> 8) & 255:02x}{v & 255:02x}")
    return ImageFeatures(colors, 1.0 + ((base % 41) - 20) / 100, 0.55, 0.45, 0.35, 0.65, 0.28, 0.0, 0.25, 0.2, base)


def extract_features(stem: str, image_url: str, seed: int) -> ImageFeatures:
    try:
        image = _download_image(image_url)
    except Exception:
        return _fallback_features(stem, seed)

    width, height = image.size
    small = image.resize((64, 64), Image.Resampling.BILINEAR)
    arr = np.asarray(small, dtype=np.float32) / 255.0
    flat = arr.reshape(-1, 3)

    lum = flat @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    brightness = float(np.mean(lum))
    saturation = float(np.mean(np.max(flat, axis=1) - np.min(flat, axis=1)))
    color_variance = float(np.mean(np.std(flat, axis=0)))
    warm_bias = float(np.mean(flat[:, 0] - flat[:, 2]))

    quant = np.clip((flat * 5).astype(np.int32), 0, 4)
    bins = quant[:, 0] * 25 + quant[:, 1] * 5 + quant[:, 2]
    counts = np.bincount(bins, minlength=125)
    dominant_ratio = float(counts.max() / max(1, counts.sum()))
    top = counts.argsort()[-5:][::-1]
    colors = []
    for idx in top:
        mask = bins == idx
        if np.any(mask):
            colors.append(_hex(np.mean(flat[mask], axis=0) * 255.0))
    while len(colors) < 4:
        colors.append(_fallback_features(stem, seed).colors[len(colors)])

    gray = arr @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    diagonal_energy = float(np.mean(np.abs(gray[1:, 1:] - gray[:-1, :-1])))
    edge_density = float(min(1.0, (np.mean(gx) + np.mean(gy)) * 4.0))
    symmetry = 1.0 - float(np.mean(np.abs(gray - np.fliplr(gray))))
    return ImageFeatures(
        colors=colors[:4],
        aspect=float(width / max(1, height)),
        brightness=brightness,
        saturation=saturation,
        edge_density=edge_density,
        vertical_symmetry=max(0.0, min(1.0, symmetry)),
        color_variance=min(1.0, color_variance * 2.2),
        warm_bias=max(-1.0, min(1.0, warm_bias)),
        dominant_ratio=dominant_ratio,
        diagonal_energy=min(1.0, diagonal_energy * 4.0),
        seed_value=_stable_int(stem, seed),
    )


def build_module(stem: str, image_url: str, seed: int) -> str:
    f = extract_features(stem, image_url, seed)
    body_h = 0.34 + 0.12 * f.brightness
    body_w = min(0.46, max(0.22, 0.31 * f.aspect))
    body_d = max(0.18, min(0.40, 0.28 + 0.08 * f.edge_density))
    segments = 8 if f.edge_density < 0.35 else 12
    side_count = 2 + int(f.saturation * 4) + int(f.dominant_ratio < 0.18)
    mirrored = "true" if f.vertical_symmetry > 0.58 else "false"
    c0, c1, c2, c3 = f.colors
    horn = 0.06 + 0.04 * ((f.seed_value >> 3) % 5) / 4.0
    tilt = (((f.seed_value >> 9) % 21) - 10) / 300.0 + (f.diagonal_energy - 0.2) * 0.05
    accent_metalness = 0.01 + f.color_variance * 0.04
    nose_sides = 6 if f.warm_bias < 0 else 9
    return f"""export default function generate(THREE) {{
  const group = new THREE.Group();
  const baseMat = new THREE.MeshStandardMaterial({{ color: {c0}, roughness: 0.72, metalness: 0.03 }});
  const accentMat = new THREE.MeshStandardMaterial({{ color: {c1}, roughness: 0.64, metalness: 0.02 }});
  const darkMat = new THREE.MeshStandardMaterial({{ color: {c2}, roughness: 0.88, metalness: 0.0 }});
  const lightMat = new THREE.MeshStandardMaterial({{ color: {c3}, roughness: 0.58, metalness: {accent_metalness:.4f} }});
  const body = new THREE.Mesh(new THREE.BoxGeometry({body_w:.4f}, {body_h:.4f}, {body_d:.4f}, 1, 1, 1), baseMat);
  body.rotation.z = {tilt:.4f};
  group.add(body);
  const cap = new THREE.Mesh(new THREE.SphereGeometry({min(body_w, body_d) * 0.45:.4f}, {segments}, 6), accentMat);
  cap.scale.y = {0.65 + f.saturation * 0.45:.4f};
  cap.position.y = {body_h / 2 + 0.045:.4f};
  group.add(cap);
  const footGeo = new THREE.BoxGeometry({body_w / 3:.4f}, 0.055, {body_d / 2.4:.4f});
  for (let i = 0; i < {side_count}; i++) {{
    const t = {side_count} === 1 ? 0 : (i / ({side_count} - 1)) - 0.5;
    const foot = new THREE.Mesh(footGeo, darkMat);
    foot.position.set(t * {body_w * 0.75:.4f}, {-body_h / 2 - 0.035:.4f}, {body_d * 0.18:.4f});
    group.add(foot);
    if ({mirrored}) {{
      const back = new THREE.Mesh(footGeo, darkMat);
      back.position.set(t * {body_w * 0.75:.4f}, {-body_h / 2 - 0.035:.4f}, {-body_d * 0.18:.4f});
      group.add(back);
    }}
  }}
  const spikeGeo = new THREE.ConeGeometry({horn:.4f}, {horn * 1.9:.4f}, 5);
  for (let i = -1; i <= 1; i += 2) {{
    const spike = new THREE.Mesh(spikeGeo, lightMat);
    spike.position.set(i * {body_w * 0.28:.4f}, {body_h / 2 + horn:.4f}, {body_d * 0.10:.4f});
    spike.rotation.z = -i * 0.38;
    group.add(spike);
  }}
  const nose = new THREE.Mesh(new THREE.ConeGeometry({body_w * 0.18:.4f}, {body_d * 0.55:.4f}, {nose_sides}), accentMat);
  nose.rotation.x = Math.PI / 2;
  nose.position.z = {body_d / 2 + body_d * 0.20:.4f};
  group.add(nose);
  return group;
}}
"""
