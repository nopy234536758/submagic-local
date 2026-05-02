#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StyleConfig — tous les paramètres visuels des sous-titres (niveau CapCut).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class StyleConfig:
    # ── Texte ──
    font_size: int = 60
    text_color: str = "#FFFFFF"
    font_path: Optional[str] = None
    bold: bool = True
    italic: bool = False
    uppercase: bool = False
    letter_spacing: int = 0

    # ── Contour ──
    outline_color: str = "#000000"
    outline_width: int = 2

    # ── Ombre ──
    shadow: bool = False
    shadow_color: str = "#000000"
    shadow_opacity: int = 180
    shadow_offset_x: int = 3
    shadow_offset_y: int = 3
    shadow_blur: int = 4

    # ── Fond du mot ──
    word_bg: bool = False
    word_bg_color: str = "#000000"
    word_bg_opacity: int = 160
    word_bg_padding: int = 10
    word_bg_radius: int = 8

    # ── Surlignage karaoké ──
    highlight: bool = True
    highlight_color: str = "#FFD700"
    highlight_outline: str = "#000000"
    highlight_done_color: str = "#AAAAAA"  # mots déjà passés (mode N>1)

    # ── Affichage N mots à la fois ──
    words_per_display: int = 1  # 1 = un mot, 2+ = karaoké

    # ── Position ──
    y_position: float = 0.82
    x_position: float = 0.5
    align: str = "center"

    # ── Animation entrée ──
    animation_in: str = "pop"
    animation_duration: float = 0.12

    # ── Effet couleur ──
    effect_mode: str = "fixed"
    gradient_color1: str = "#FF6B6B"
    gradient_color2: str = "#4ECDC4"

    # ── Export ──
    export_resolution: str = "source"
    export_bg: str = "video"   # "video" | "green" | "black"
