#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VideoComposer — rendu sous-titres animés via PIL + FFmpeg direct.
Supporte : animations, ombre, fond mot, surlignage karaoké,
           N mots par affichage, fond vert/noir/vidéo, export audio.
"""

import os
import math
import subprocess
import tempfile
from typing import Callable, List, Dict, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from style_config import StyleConfig


# ─────────────────────────────────────────────────────
# UTILS COULEUR
# ─────────────────────────────────────────────────────
def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _rgb_to_hex(r, g, b) -> str:
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def _lerp_color(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex(r1 + (r2-r1)*t, g1 + (g2-g1)*t, b1 + (b2-b1)*t)

def _negative_color(video_path: str, t: float, y_ratio: float, vid_w: int, vid_h: int) -> str:
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return "#FFFFFF"
    bw, bh = 320, 100
    xc, yc = vid_w // 2, int(vid_h * y_ratio)
    x1, x2 = max(0, xc-bw//2), min(vid_w, xc+bw//2)
    y1, y2 = max(0, yc-bh//2), min(vid_h, yc+bh//2)
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return "#FFFFFF"
    avg = roi.mean(axis=(0, 1))
    nr, ng, nb = int(255-avg[2]), int(255-avg[1]), int(255-avg[0])
    luma = 0.299*nr + 0.587*ng + 0.114*nb
    if luma < 80:
        f = 90 / max(luma, 1)
        nr, ng, nb = min(255, int(nr*f)), min(255, int(ng*f)), min(255, int(nb*f))
    return _rgb_to_hex(nr, ng, nb)


# ─────────────────────────────────────────────────────
# CHARGEMENT POLICE
# ─────────────────────────────────────────────────────
_SYSTEM_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]

def _load_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    for p in _SYSTEM_FONTS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ─────────────────────────────────────────────────────
# GROUPE DE MOTS : découpage par N mots, sans ponctuation seule
# ─────────────────────────────────────────────────────
import unicodedata

def _is_punctuation_only(word: str) -> bool:
    """Retourne True si le mot ne contient que de la ponctuation/espaces."""
    stripped = word.strip()
    if not stripped:
        return True
    return all(unicodedata.category(c).startswith('P') or
               unicodedata.category(c).startswith('Z')
               for c in stripped)

def build_display_groups(words: List[Dict], n: int) -> List[Dict]:
    """
    Regroupe les mots en groupes de n mots pour l'affichage.
    - La ponctuation est collée au mot précédent (pas de groupe seul ponct.)
    - Chaque groupe a :
        group_start, group_end, group_words (liste de word dicts),
        group_idx, word_idx_in_group pour chaque mot.
    Retourne une liste de mots enrichis avec ces champs.
    """
    if n <= 1:
        # mode 1 mot : pas de regroupement, on ignore ponctuation seule
        result = []
        for w in words:
            wc = dict(w)
            wc["group_start"] = w["start"]
            wc["group_end"] = w["end"]
            wc["group_words"] = [w]
            wc["group_idx"] = len(result)
            wc["word_idx_in_group"] = 0
            result.append(wc)
        return result

    # Filtrer les mots qui sont UNIQUEMENT ponctuation — on les colle au précédent
    merged: List[Dict] = []
    for w in words:
        if _is_punctuation_only(w["word"]):
            if merged:
                # Coller au mot précédent : étendre son end et ajouter le texte
                prev = merged[-1]
                prev["word"] = prev["word"].rstrip() + w["word"]
                prev["end"] = w["end"]
            # sinon ignorer
        else:
            merged.append(dict(w))

    # Découper en groupes de n
    result = []
    i = 0
    group_idx = 0
    while i < len(merged):
        group = merged[i:i+n]
        g_start = group[0]["start"]
        g_end = group[-1]["end"]
        for j, gw in enumerate(group):
            wc = dict(gw)
            wc["group_start"] = g_start
            wc["group_end"] = g_end
            wc["group_words"] = group
            wc["group_idx"] = group_idx
            wc["word_idx_in_group"] = j
            result.append(wc)
        i += n
        group_idx += 1
    return result


# ─────────────────────────────────────────────────────
# RENDU D'UN GROUPE DE MOTS (karaoké / mot unique)
# ─────────────────────────────────────────────────────
def _render_group(
    group_words: List[Dict],
    current_word_idx: int,      # index du mot surligné dans le groupe (-1 = aucun)
    style: StyleConfig,
    base_color: str,
    canvas_w: int,
    canvas_h: int,
    anim_progress: float = 1.0,
) -> np.ndarray:
    """
    Rend tous les mots du groupe côte à côte sur le canvas.
    Le mot courant est surligné (karaoké). Les mots passés sont grisés.
    """
    s = style
    font = _load_font(s.font_path, s.font_size)
    SPACE_W = 14   # espace entre les mots en px

    # ── Mesurer chaque mot ──
    dummy = Image.new("RGBA", (1, 1))
    d = ImageDraw.Draw(dummy)

    word_sizes = []
    for wd in group_words:
        display = wd["word"].upper() if s.uppercase else wd["word"]
        bb = d.textbbox((0, 0), display, font=font)
        word_sizes.append((display, bb[2]-bb[0], bb[3]-bb[1], bb[0], bb[1]))

    total_w = sum(ws[1] for ws in word_sizes) + SPACE_W * max(0, len(word_sizes)-1)
    max_h = max(ws[2] for ws in word_sizes) if word_sizes else 0

    pad = s.outline_width + s.word_bg_padding + 8
    shadow_extra = (abs(s.shadow_offset_x) + s.shadow_blur + 4) if s.shadow else 0
    img_w = total_w + pad * 2 + shadow_extra
    img_h = max_h + pad * 2 + shadow_extra

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Curseur de dessin
    cursor_x = pad + shadow_extra // 2

    for wi, (display, ww, wh, offx, offy) in enumerate(word_sizes):
        ty = pad - offy + shadow_extra // 2
        tx = cursor_x - offx

        # Choisir la couleur
        if wi == current_word_idx and s.highlight:
            txt_color = _hex_to_rgb(s.highlight_color)
            out_color = _hex_to_rgb(s.highlight_outline)
        elif current_word_idx >= 0 and wi < current_word_idx and s.words_per_display > 1:
            # mots déjà passés en mode karaoké
            txt_color = _hex_to_rgb(s.highlight_done_color)
            out_color = _hex_to_rgb(s.outline_color)
        else:
            txt_color = _hex_to_rgb(base_color)
            out_color = _hex_to_rgb(s.outline_color)

        # ── Fond du mot ──
        if s.word_bg:
            bg_rgb = _hex_to_rgb(s.word_bg_color)
            bg_rect = [tx - s.word_bg_padding, ty - s.word_bg_padding,
                       tx + ww + s.word_bg_padding, ty + wh + s.word_bg_padding]
            draw.rounded_rectangle(bg_rect, radius=s.word_bg_radius,
                                   fill=(*bg_rgb, s.word_bg_opacity))

        # ── Ombre ──
        if s.shadow:
            sh_rgb = _hex_to_rgb(s.shadow_color)
            ow = s.outline_width
            ox, oy = s.shadow_offset_x, s.shadow_offset_y
            if ow > 0:
                for dx in range(-ow, ow+1):
                    for dy in range(-ow, ow+1):
                        draw.text((tx+ox+dx, ty+oy+dy), display, font=font,
                                  fill=(*sh_rgb, s.shadow_opacity))
            draw.text((tx+ox, ty+oy), display, font=font, fill=(*sh_rgb, s.shadow_opacity))

        # ── Contour ──
        ow = s.outline_width
        if ow > 0:
            for dx in range(-ow, ow+1):
                for dy in range(-ow, ow+1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((tx+dx, ty+dy), display, font=font, fill=(*out_color, 255))

        # ── Texte principal ──
        draw.text((tx, ty), display, font=font, fill=(*txt_color, 255))

        # Surbrillance scintillante pour le mot actif (karaoké > 1 mot)
        if wi == current_word_idx and s.highlight and s.words_per_display > 1:
            glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            gc = _hex_to_rgb(s.highlight_color)
            gd.text((tx, ty), display, font=font, fill=(*gc, 80))
            glow = glow.filter(ImageFilter.GaussianBlur(4))
            img = Image.alpha_composite(img, glow)
            draw = ImageDraw.Draw(img)

        cursor_x += ww + SPACE_W

    # ── Animation d'entrée ──
    img = _apply_animation_in(img, s.animation_in, anim_progress)

    # ── Placer dans le canvas ──
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    # Centrage horizontal
    if s.align == "center":
        x_px = int(canvas_w * s.x_position) - img_w // 2
    elif s.align == "left":
        x_px = int(canvas_w * s.x_position)
    else:  # right
        x_px = int(canvas_w * s.x_position) - img_w
    x_px = max(0, min(canvas_w - img_w, x_px))
    y_px = int(canvas_h * s.y_position) - img_h // 2
    y_px = max(0, min(canvas_h - img_h, y_px))
    canvas.paste(img, (x_px, y_px), img)

    return np.array(canvas)


def _apply_animation_in(img: Image.Image, anim: str, t: float) -> Image.Image:
    if t >= 1.0 or anim == "none":
        return img
    w, h = img.size

    if anim == "fade":
        alpha = img.split()[3]
        alpha = alpha.point(lambda p: int(p * t))
        img.putalpha(alpha)

    elif anim == "pop":
        scale = 0.5 + 0.5 * _ease_out_back(t)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        img = img.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.paste(img, ((w-nw)//2, (h-nh)//2), img)
        img = canvas

    elif anim == "slide_up":
        offset = int(h * (1 - _ease_out_cubic(t)))
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.paste(img, (0, offset), img)
        img = canvas

    elif anim == "slide_down":
        offset = int(h * (1 - _ease_out_cubic(t)))
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.paste(img, (0, -offset), img)
        img = canvas

    elif anim == "bounce":
        scale = _ease_out_bounce(t)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        img = img.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.paste(img, ((w-nw)//2, (h-nh)//2), img)
        img = canvas

    return img


def _ease_out_cubic(t): return 1 - (1 - t) ** 3
def _ease_out_back(t):
    c1, c3 = 1.70158, 1.70158 + 1
    return 1 + c3 * (t - 1)**3 + c1 * (t - 1)**2
def _ease_out_bounce(t):
    n1, d1 = 7.5625, 2.75
    if t < 1/d1: return n1*t*t
    elif t < 2/d1: t -= 1.5/d1; return n1*t*t + 0.75
    elif t < 2.5/d1: t -= 2.25/d1; return n1*t*t + 0.9375
    else: t -= 2.625/d1; return n1*t*t + 0.984375


# ─────────────────────────────────────────────────────
# COMPOSER PRINCIPAL
# ─────────────────────────────────────────────────────
class VideoComposer:
    def __init__(self, video_path: str, style: StyleConfig):
        self.video_path = video_path
        self.style = style

        cap = cv2.VideoCapture(video_path)
        self.vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps   = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

    def _output_size(self) -> Tuple[int, int]:
        res = self.style.export_resolution
        if res == "1080p":
            ratio = self.vid_w / self.vid_h
            return (1920, int(1920 / ratio)) if ratio >= 1 else (int(1080 * ratio), 1080)
        elif res == "4k":
            ratio = self.vid_w / self.vid_h
            return (3840, int(3840 / ratio)) if ratio >= 1 else (int(2160 * ratio), 2160)
        return (self.vid_w, self.vid_h)

    def _word_color(self, t: float) -> str:
        s = self.style
        if s.effect_mode == "negative":
            return _negative_color(self.video_path, t, s.y_position, self.vid_w, self.vid_h)
        elif s.effect_mode == "gradient":
            phase = (t % 3.0) / 3.0
            return _lerp_color(s.gradient_color1, s.gradient_color2, phase)
        return s.text_color

    def compose(
        self,
        word_timestamps: List[Dict],
        output_path: str,
        mode: str = "export",
        progress_callback: Optional[Callable] = None,
    ):
        def _prog(v, msg):
            if progress_callback:
                progress_callback(v, msg)

        out_w, out_h = self._output_size()
        s = self.style
        bg_mode = s.export_bg

        _prog(0.10, "Préparation des timestamps…")
        words = word_timestamps
        if mode == "preview":
            words = [w for w in words if w["start"] < 45]

        for w in words:
            if not w["word"].strip():
                w["word"] = "[……]"

        # Construire les groupes
        enriched = build_display_groups(words, s.words_per_display)

        # ── Pipe FFmpeg ──
        _prog(0.15, "Ouverture de la vidéo source…")

        if bg_mode == "video":
            ff_input_args = [
                "ffmpeg", "-y",
                "-f", "rawvideo", "-vcodec", "rawvideo",
                "-s", f"{out_w}x{out_h}",
                "-pix_fmt", "rgba",
                "-r", str(self.fps),
                "-i", "pipe:0",
                "-i", self.video_path,
                "-map", "0:v", "-map", "1:a?",
                "-c:v", "libx264", "-preset", "fast",
                "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest",
                output_path
            ]
        else:
            # Fond vert/noir — on GARDE l'audio
            ff_input_args = [
                "ffmpeg", "-y",
                "-f", "rawvideo", "-vcodec", "rawvideo",
                "-s", f"{out_w}x{out_h}",
                "-pix_fmt", "rgba",
                "-r", str(self.fps),
                "-i", "pipe:0",
                "-i", self.video_path,
                "-map", "0:v", "-map", "1:a?",
                "-c:v", "libx264", "-preset", "fast",
                "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest",
                output_path
            ]

        ff_proc = subprocess.Popen(ff_input_args, stdin=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL)

        cap = cv2.VideoCapture(self.video_path)
        frame_idx = 0
        total = self.total_frames or 1

        _prog(0.20, "Encodage en cours…")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                t = frame_idx / self.fps

                # Fond
                if bg_mode == "green":
                    base = Image.new("RGBA", (out_w, out_h), (0, 255, 0, 255))
                elif bg_mode == "black":
                    base = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 255))
                else:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_frame = Image.fromarray(frame_rgb).convert("RGBA")
                    if (out_w, out_h) != (self.vid_w, self.vid_h):
                        pil_frame = pil_frame.resize((out_w, out_h), Image.LANCZOS)
                    base = pil_frame

                # Trouver le groupe actif et le mot courant
                overlay = _get_overlay_for_time(t, enriched, s, self._word_color(t),
                                                 out_w, out_h)
                if overlay is not None:
                    base = Image.alpha_composite(base, Image.fromarray(overlay, "RGBA"))

                ff_proc.stdin.write(base.tobytes())
                frame_idx += 1

                if frame_idx % 30 == 0:
                    pct = 0.20 + 0.75 * (frame_idx / total)
                    _prog(pct, f"Encodage… frame {frame_idx}/{total}")

        finally:
            cap.release()
            ff_proc.stdin.close()
            ff_proc.wait()

        _prog(1.0, "Export terminé ✓")


def _get_overlay_for_time(
    t: float,
    enriched: List[Dict],
    s: StyleConfig,
    base_color: str,
    canvas_w: int,
    canvas_h: int,
) -> Optional[np.ndarray]:
    """
    Trouve le groupe actif au temps t et rend son overlay.
    """
    # Trouver le groupe courant : le groupe dont la fenêtre couvre t
    current_group = None
    current_word_in_group = -1

    # Le groupe est actif si group_start <= t <= group_end
    # On cherche en plus le mot courant dans le groupe
    for ew in enriched:
        if ew["group_start"] <= t <= ew["group_end"]:
            current_group = ew
            break

    if current_group is None:
        # Chercher le dernier groupe dont group_end < t (pour garder affiché)
        # On affiche rien entre deux groupes (ou on pourrait garder le précédent)
        return None

    group_words = current_group["group_words"]
    group_start = current_group["group_start"]
    group_end = current_group["group_end"]

    # Mot courant dans le groupe = celui dont start <= t
    current_word_in_group = -1
    if s.words_per_display > 1 and s.highlight:
        for i, gw in enumerate(group_words):
            if gw["start"] <= t:
                current_word_in_group = i

    # Animation : basée sur le début du groupe
    elapsed = t - group_start
    anim_dur = max(s.animation_duration, 0.01)
    anim_t = min(elapsed / anim_dur, 1.0)

    return _render_group(
        group_words, current_word_in_group, s, base_color,
        canvas_w, canvas_h, anim_t
    )


# ─────────────────────────────────────────────────────
# PRÉVISUALISATION FRAME (player intégré)
# ─────────────────────────────────────────────────────
def render_preview_frame(
    video_path: str,
    t: float,
    word_timestamps: List[Dict],
    style: StyleConfig,
    target_w: int = 800,
) -> Optional[np.ndarray]:
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None

    s = style
    bg_mode = s.export_bg

    vid_h, vid_w = frame.shape[:2]
    scale = target_w / vid_w
    disp_w = target_w
    disp_h = int(vid_h * scale)

    if bg_mode == "green":
        base = Image.new("RGBA", (disp_w, disp_h), (0, 255, 0, 255))
    elif bg_mode == "black":
        base = Image.new("RGBA", (disp_w, disp_h), (0, 0, 0, 255))
    else:
        frame_resized = cv2.resize(frame, (disp_w, disp_h))
        base = Image.fromarray(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)).convert("RGBA")

    enriched = build_display_groups(word_timestamps, s.words_per_display)
    overlay = _get_overlay_for_time(t, enriched, s, s.text_color, disp_w, disp_h)
    if overlay is not None:
        base = Image.alpha_composite(base, Image.fromarray(overlay, "RGBA"))

    return cv2.cvtColor(np.array(base.convert("RGB")), cv2.COLOR_RGB2BGR)
