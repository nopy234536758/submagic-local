#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Submagic Local ✦ Turfu Edition — GUI Next Level.
"""

import os
import sys
import threading
import tempfile
import time
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk

from style_config import StyleConfig
from transcriber import Transcriber
from video_composer import VideoComposer, render_preview_frame
from srt_exporter import export_srt, export_word_by_word_srt

# ── Try to import pygame for audio preview ──
try:
    import pygame
    pygame.mixer.init()
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False

# ── Try moviepy for audio extraction ──
try:
    from moviepy import VideoFileClip
    HAS_MOVIEPY = True
except Exception:
    HAS_MOVIEPY = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Palette ──
ACCENT      = "#6C63FF"
ACCENT2     = "#FF6584"
BG_ROOT     = "#0D0D0F"
BG_PANEL    = "#13131A"
BG_CARD     = "#1E1E2E"
BG_CARD2    = "#252535"
TEXT_DIM    = "#6B7280"
TEXT_BRIGHT = "#F9FAFB"
GREEN_BTN   = "#059669"
GREEN_HOV   = "#047857"
BLUE_BTN    = "#1d4ed8"
BLUE_HOV    = "#1e40af"


# ═══════════════════════════════════════════════════════
# WIDGET : Color Picker Button
# ═══════════════════════════════════════════════════════
class ColorBtn(ctk.CTkButton):
    def __init__(self, parent, color: str, on_change, **kw):
        super().__init__(parent, width=36, height=28, text="", corner_radius=6,
                         fg_color=color, hover=False, **kw)
        self._color = color
        self._on_change = on_change
        self.configure(command=self._pick)

    def _pick(self):
        result = colorchooser.askcolor(color=self._color, title="Couleur")
        if result and result[1]:
            self._color = result[1]
            self.configure(fg_color=self._color)
            self._on_change(self._color)

    def set_color(self, c: str):
        self._color = c
        self.configure(fg_color=c)


# ═══════════════════════════════════════════════════════
# AUDIO PLAYER (pygame-based)
# ═══════════════════════════════════════════════════════
class AudioPlayer:
    """Extrait l'audio de la vidéo et le joue en sync avec la preview."""

    def __init__(self):
        self._audio_path = None
        self._offset = 0.0

    def load(self, video_path: str):
        """Extrait l'audio en WAV temporaire."""
        self._audio_path = None
        if not (HAS_PYGAME and HAS_MOVIEPY):
            return
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            clip = VideoFileClip(video_path)
            if clip.audio:
                clip.audio.write_audiofile(tmp.name, logger=None)
                self._audio_path = tmp.name
            clip.close()
        except Exception:
            pass

    def play(self, t: float):
        if not (HAS_PYGAME and self._audio_path):
            return
        try:
            pygame.mixer.music.load(self._audio_path)
            pygame.mixer.music.play(start=t)
        except Exception:
            pass

    def stop(self):
        if HAS_PYGAME:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def is_playing(self) -> bool:
        if HAS_PYGAME:
            try:
                return pygame.mixer.music.get_busy()
            except Exception:
                pass
        return False


# ═══════════════════════════════════════════════════════
# WIDGET : Player de prévisualisation intégré
# ═══════════════════════════════════════════════════════
class PreviewPlayer(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=12, **kw)
        self._video_path = None
        self._word_timestamps = []
        self._style = None
        self._playing = False
        self._t = 0.0
        self._duration = 0.0
        self._fps = 30.0
        self._thread = None
        self._audio = AudioPlayer()

        # Canvas
        self.canvas = tk.Canvas(self, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=(6, 0))
        self._img_ref = None

        # Controls bar
        ctrl = ctk.CTkFrame(self, fg_color=BG_CARD2, corner_radius=8)
        ctrl.pack(fill="x", padx=8, pady=6)

        self.btn_play = ctk.CTkButton(
            ctrl, text="▶", width=44, height=34,
            fg_color=ACCENT, hover_color="#5A52D5",
            font=("", 14), command=self._toggle_play
        )
        self.btn_play.pack(side="left", padx=(8, 6), pady=5)

        self.slider = ctk.CTkSlider(
            ctrl, from_=0, to=100, command=self._seek,
            button_color=ACCENT, button_hover_color="#5A52D5",
            progress_color=ACCENT
        )
        self.slider.pack(side="left", fill="x", expand=True, padx=4)

        self.lbl_time = ctk.CTkLabel(
            ctrl, text="0:00 / 0:00", width=95,
            font=("", 11), text_color=TEXT_DIM
        )
        self.lbl_time.pack(side="right", padx=(4, 10))

        self._show_placeholder()

    def _show_placeholder(self):
        self.canvas.delete("all")
        self.canvas.create_text(
            400, 200,
            text="🎬  Chargez une vidéo et transcrivez\npour voir la prévisualisation",
            fill="#444", font=("", 13), justify="center"
        )

    def load(self, video_path, word_timestamps, style):
        self._video_path = video_path
        self._word_timestamps = word_timestamps
        self._style = style
        cap = cv2.VideoCapture(video_path)
        self._fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        fc = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        self._duration = fc / self._fps
        cap.release()
        self._t = 0.0
        self.slider.configure(to=self._duration)
        self._render_frame(0.0)
        # Load audio async
        threading.Thread(target=self._audio.load, args=(video_path,), daemon=True).start()

    def _render_frame(self, t: float):
        if not self._video_path:
            return
        cw = self.canvas.winfo_width() or 760
        ch = self.canvas.winfo_height() or 430
        frame = render_preview_frame(
            self._video_path, t, self._word_timestamps, self._style, target_w=cw
        )
        if frame is None:
            return
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        img.thumbnail((cw, ch), Image.LANCZOS)
        self._img_ref = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(cw//2, ch//2, image=self._img_ref, anchor="center")
        mins = int(t) // 60; secs = int(t) % 60
        dmins = int(self._duration) // 60; dsecs = int(self._duration) % 60
        self.lbl_time.configure(text=f"{mins}:{secs:02d} / {dmins}:{dsecs:02d}")

    def _toggle_play(self):
        if self._playing:
            self._playing = False
            self._audio.stop()
            self.btn_play.configure(text="▶")
        else:
            self._playing = True
            self._audio.play(self._t)
            self.btn_play.configure(text="⏸")
            self._thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._thread.start()

    def _playback_loop(self):
        interval = 1.0 / self._fps
        while self._playing and self._t < self._duration:
            start = time.time()
            self._render_frame(self._t)
            self.slider.set(self._t)
            self._t += interval
            elapsed = time.time() - start
            time.sleep(max(0, interval - elapsed))
        self._playing = False
        self._audio.stop()
        self.btn_play.configure(text="▶")

    def _seek(self, val):
        self._t = float(val)
        if self._playing:
            self._audio.stop()
            self._audio.play(self._t)
        else:
            self._render_frame(self._t)

    def refresh_style(self, style):
        self._style = style
        if not self._playing:
            self._render_frame(self._t)


# ═══════════════════════════════════════════════════════
# WIDGET : Éditeur de sous-titres
# ═══════════════════════════════════════════════════════
class SubtitleEditor(ctk.CTkFrame):
    def __init__(self, parent, on_change, **kw):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=12, **kw)
        self._on_change = on_change
        self._words = []

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(header, text="✏️  Correction des sous-titres",
                     font=("", 13, "bold"), text_color=TEXT_BRIGHT).pack(side="left")
        ctk.CTkButton(
            header, text="Appliquer ✓", width=90, height=28,
            fg_color=ACCENT, hover_color="#5A52D5",
            font=("", 11, "bold"), command=self._apply
        ).pack(side="right")

        self.txt = ctk.CTkTextbox(self, font=("JetBrains Mono", 11), wrap="word",
                                  fg_color=BG_CARD2, text_color="#C9D1D9")
        self.txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.txt.insert("1.0", "Les sous-titres apparaîtront ici après transcription.")

    def load_words(self, words):
        self._words = [dict(w) for w in words]
        self.txt.delete("1.0", "end")
        for w in self._words:
            self.txt.insert("end", f"{w['start']:.2f}\t{w['end']:.2f}\t{w['word']}\n")

    def _apply(self):
        content = self.txt.get("1.0", "end").strip()
        new_words = []
        for line in content.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            try:
                new_words.append({
                    "start": float(parts[0]),
                    "end": float(parts[1]),
                    "word": parts[2].strip() or "[……]"
                })
            except ValueError:
                continue
        if new_words:
            self._words = new_words
            self._on_change(new_words)
            messagebox.showinfo("✅", f"{len(new_words)} mots mis à jour.")

    def get_words(self):
        return self._words


# ═══════════════════════════════════════════════════════
# APP PRINCIPALE
# ═══════════════════════════════════════════════════════
class SubmagicApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("✦ Submagic Local — Turfu Edition")
        self.geometry("1440x920")
        self.minsize(1100, 750)
        self.configure(fg_color=BG_ROOT)

        self.video_path = None
        self.word_timestamps = []
        self.style = StyleConfig()
        self.model_size = ctk.StringVar(value="small")

        self._build_ui()

    # ───────────────────────────────────────────────────
    # BUILD UI
    # ───────────────────────────────────────────────────
    def _build_ui(self):
        # Title bar
        title_bar = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=52)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        ctk.CTkLabel(
            title_bar,
            text="✦  SUBMAGIC  LOCAL",
            font=("", 17, "bold"),
            text_color=ACCENT
        ).pack(side="left", padx=20)

        ctk.CTkLabel(
            title_bar,
            text="Turfu Edition",
            font=("", 11),
            text_color=TEXT_DIM
        ).pack(side="left")

        if not HAS_PYGAME:
            ctk.CTkLabel(
                title_bar,
                text="⚠ Son preview : pip install pygame",
                font=("", 10), text_color="#F59E0B"
            ).pack(side="right", padx=16)

        # Main content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(0, weight=0, minsize=290)
        content.grid_columnconfigure(1, weight=1)
        content.grid_columnconfigure(2, weight=0, minsize=350)
        content.grid_rowconfigure(0, weight=1)

        # Left
        left = ctk.CTkScrollableFrame(content, width=290, fg_color=BG_PANEL,
                                       corner_radius=0, scrollbar_button_color=BG_CARD2)
        left.grid(row=0, column=0, sticky="nsew")
        self._build_left(left)

        # Center
        center = ctk.CTkFrame(content, fg_color="#0A0A10", corner_radius=0)
        center.grid(row=0, column=1, sticky="nsew")
        center.grid_rowconfigure(0, weight=3)
        center.grid_rowconfigure(1, weight=2)
        center.grid_columnconfigure(0, weight=1)

        self.player = PreviewPlayer(center)
        self.player.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 6))

        self.editor = SubtitleEditor(center, on_change=self._on_subtitles_edited)
        self.editor.grid(row=1, column=0, sticky="nsew", padx=12, pady=(6, 12))

        # Right
        right = ctk.CTkScrollableFrame(content, width=350, fg_color=BG_PANEL,
                                        corner_radius=0, scrollbar_button_color=BG_CARD2)
        right.grid(row=0, column=2, sticky="nsew")
        self._build_style_panel(right)

    # ── PANNEAU GAUCHE ──────────────────────────────────
    def _build_left(self, p):
        self._sec(p, "① Source vidéo")

        self.btn_load = ctk.CTkButton(
            p, text="📂  Charger une vidéo",
            command=self._load_video, height=40,
            fg_color=BG_CARD2, hover_color=BG_CARD,
            border_width=1, border_color=ACCENT,
            font=("", 12, "bold"), text_color=ACCENT
        )
        self.btn_load.pack(fill="x", padx=12, pady=(4, 2))
        self.lbl_video = ctk.CTkLabel(p, text="Aucune vidéo sélectionnée",
                                       text_color=TEXT_DIM, wraplength=250,
                                       font=("", 10))
        self.lbl_video.pack(padx=12, pady=(0, 8))

        self._sec(p, "② Modèle Whisper")
        mf = ctk.CTkFrame(p, fg_color=BG_CARD, corner_radius=8)
        mf.pack(fill="x", padx=12, pady=(4, 8))
        for i, sz in enumerate(["tiny", "small", "medium", "large"]):
            ctk.CTkRadioButton(
                mf, text=sz, variable=self.model_size, value=sz,
                font=("", 11), fg_color=ACCENT, hover_color="#5A52D5"
            ).grid(row=i//2, column=i%2, padx=10, pady=5, sticky="w")

        self.btn_transcribe = ctk.CTkButton(
            p, text="🎙  Transcrire",
            command=self._transcribe, state="disabled",
            height=44, font=("", 13, "bold"),
            fg_color=BLUE_BTN, hover_color=BLUE_HOV
        )
        self.btn_transcribe.pack(fill="x", padx=12, pady=(0, 4))

        self.progress = ctk.CTkProgressBar(p, progress_color=ACCENT,
                                            fg_color=BG_CARD2)
        self.progress.pack(fill="x", padx=12, pady=(4, 2))
        self.progress.set(0)
        self.lbl_prog = ctk.CTkLabel(p, text="", text_color=TEXT_DIM,
                                      font=("", 10), wraplength=250)
        self.lbl_prog.pack(padx=12, pady=(0, 8))

        self._sec(p, "③ Export")

        rf = ctk.CTkFrame(p, fg_color=BG_CARD, corner_radius=8)
        rf.pack(fill="x", padx=12, pady=(4, 4))
        rf.columnconfigure(1, weight=1)

        ctk.CTkLabel(rf, text="Résolution", font=("", 11)).grid(
            row=0, column=0, padx=10, pady=7, sticky="w")
        self.var_res = ctk.StringVar(value="source")
        ctk.CTkOptionMenu(
            rf, values=["source", "1080p", "4k"],
            variable=self.var_res,
            command=lambda v: setattr(self.style, "export_resolution", v),
            width=110, fg_color=BG_CARD2, button_color=ACCENT,
            button_hover_color="#5A52D5"
        ).grid(row=0, column=1, padx=8, pady=7)

        ctk.CTkLabel(rf, text="Fond vidéo", font=("", 11)).grid(
            row=1, column=0, padx=10, pady=7, sticky="w")
        self.var_bg = ctk.StringVar(value="video")
        self._bg_menu = ctk.CTkOptionMenu(
            rf, values=["video", "green screen", "black screen"],
            variable=self.var_bg,
            command=self._on_bg_change,
            width=130, fg_color=BG_CARD2, button_color=ACCENT,
            button_hover_color="#5A52D5"
        )
        self._bg_menu.grid(row=1, column=1, padx=8, pady=7)

        self.btn_export_mp4 = ctk.CTkButton(
            p, text="💾  Exporter MP4",
            command=self._export_mp4, state="disabled",
            height=42, font=("", 12, "bold"),
            fg_color=GREEN_BTN, hover_color=GREEN_HOV
        )
        self.btn_export_mp4.pack(fill="x", padx=12, pady=(10, 4))

        self.btn_export_srt = ctk.CTkButton(
            p, text="📄  Exporter SRT",
            command=self._export_srt, state="disabled",
            height=34, font=("", 11),
            fg_color=BG_CARD, hover_color=BG_CARD2,
            border_width=1, border_color="#374151"
        )
        self.btn_export_srt.pack(fill="x", padx=12, pady=(0, 4))

        self.btn_preview_quick = ctk.CTkButton(
            p, text="👁  Preview rapide (fichier)",
            command=self._preview_file, state="disabled",
            height=34, font=("", 11),
            fg_color=BG_CARD, hover_color=BG_CARD2,
            border_width=1, border_color="#374151"
        )
        self.btn_preview_quick.pack(fill="x", padx=12, pady=(0, 16))

    def _on_bg_change(self, v):
        mapping = {"video": "video", "green screen": "green", "black screen": "black"}
        val = mapping.get(v, "video")
        self.style.export_bg = val
        if self.word_timestamps:
            threading.Thread(target=self._refresh_preview, daemon=True).start()

    # ── PANNEAU STYLE (droite) ──────────────────────────
    def _build_style_panel(self, p):
        # ── Affichage mots ──
        self._sec(p, "🔢  Affichage")
        wf = self._card(p)
        ctk.CTkLabel(wf, text="Mots par bloc", font=("", 11)).grid(
            row=0, column=0, padx=10, pady=6, sticky="w")
        self._wpd_var = ctk.IntVar(value=1)
        self._wpd_label = ctk.CTkLabel(wf, text="1", font=("", 11, "bold"),
                                        text_color=ACCENT, width=24)
        self._wpd_label.grid(row=0, column=2, padx=4)
        wpd_sld = ctk.CTkSlider(
            wf, from_=1, to=8, number_of_steps=7,
            command=self._on_wpd_change,
            button_color=ACCENT, button_hover_color="#5A52D5",
            progress_color=ACCENT
        )
        wpd_sld.set(1)
        wpd_sld.grid(row=0, column=1, padx=8, pady=6, sticky="ew")
        wf.columnconfigure(1, weight=1)

        # ── Texte ──
        self._sec(p, "🎨  Texte")
        tf = self._card(p)
        self._row_slider(tf, "Taille", 20, 150, 60, 0,
                         lambda v: self._upd("font_size", int(v)))
        self._row_color(tf, "Couleur", "#FFFFFF", 1,
                        lambda c: self._upd("text_color", c))
        self._row_toggle(tf, "Gras", True, 2, lambda v: self._upd("bold", v))
        self._row_toggle(tf, "Italique", False, 3, lambda v: self._upd("italic", v))
        self._row_toggle(tf, "MAJUSCULES", False, 4, lambda v: self._upd("uppercase", v))

        self._sec(p, "✏️  Contour")
        of = self._card(p)
        self._row_slider(of, "Épaisseur", 0, 12, 2, 0,
                         lambda v: self._upd("outline_width", int(v)))
        self._row_color(of, "Couleur contour", "#000000", 1,
                        lambda c: self._upd("outline_color", c))

        self._sec(p, "🌑  Ombre")
        shf = self._card(p)
        self._row_toggle(shf, "Activer", False, 0, lambda v: self._upd("shadow", v))
        self._row_color(shf, "Couleur ombre", "#000000", 1,
                        lambda c: self._upd("shadow_color", c))
        self._row_slider(shf, "Opacité", 0, 255, 180, 2,
                         lambda v: self._upd("shadow_opacity", int(v)))
        self._row_slider(shf, "Décalage X", -20, 20, 3, 3,
                         lambda v: self._upd("shadow_offset_x", int(v)))
        self._row_slider(shf, "Décalage Y", -20, 20, 3, 4,
                         lambda v: self._upd("shadow_offset_y", int(v)))
        self._row_slider(shf, "Flou", 0, 15, 4, 5,
                         lambda v: self._upd("shadow_blur", int(v)))

        self._sec(p, "🔲  Fond du mot")
        bf = self._card(p)
        self._row_toggle(bf, "Activer", False, 0, lambda v: self._upd("word_bg", v))
        self._row_color(bf, "Couleur fond", "#000000", 1,
                        lambda c: self._upd("word_bg_color", c))
        self._row_slider(bf, "Opacité", 0, 255, 160, 2,
                         lambda v: self._upd("word_bg_opacity", int(v)))
        self._row_slider(bf, "Padding", 0, 30, 10, 3,
                         lambda v: self._upd("word_bg_padding", int(v)))
        self._row_slider(bf, "Arrondi", 0, 30, 8, 4,
                         lambda v: self._upd("word_bg_radius", int(v)))

        self._sec(p, "✨  Karaoké / Surlignage")
        hlf = self._card(p)
        self._row_toggle(hlf, "Activer", True, 0,
                         lambda v: self._upd("highlight", v))
        self._row_color(hlf, "Couleur actif", "#FFD700", 1,
                        lambda c: self._upd("highlight_color", c))
        self._row_color(hlf, "Contour actif", "#000000", 2,
                        lambda c: self._upd("highlight_outline", c))
        self._row_color(hlf, "Mots passés", "#AAAAAA", 3,
                        lambda c: self._upd("highlight_done_color", c))

        self._sec(p, "📍  Position")
        pf = self._card(p)
        self._row_slider(pf, "Position Y", 0.05, 0.98, 0.82, 0,
                         lambda v: self._upd("y_position", round(float(v), 2)))
        self._row_slider(pf, "Position X", 0.0, 1.0, 0.5, 1,
                         lambda v: self._upd("x_position", round(float(v), 2)))
        ctk.CTkLabel(pf, text="Alignement", font=("", 11)).grid(
            row=2, column=0, padx=10, pady=5, sticky="w")
        self.var_align = ctk.StringVar(value="center")
        ctk.CTkOptionMenu(
            pf, values=["left", "center", "right"], variable=self.var_align,
            command=lambda v: self._upd("align", v),
            width=100, fg_color=BG_CARD2, button_color=ACCENT
        ).grid(row=2, column=1, padx=8, pady=5)

        self._sec(p, "🎬  Animation")
        af = self._card(p)
        ctk.CTkLabel(af, text="Effet entrée", font=("", 11)).grid(
            row=0, column=0, padx=10, pady=5, sticky="w")
        self.var_anim = ctk.StringVar(value="pop")
        ctk.CTkOptionMenu(
            af, values=["none", "pop", "fade", "slide_up", "slide_down", "bounce"],
            variable=self.var_anim,
            command=lambda v: self._upd("animation_in", v),
            width=120, fg_color=BG_CARD2, button_color=ACCENT
        ).grid(row=0, column=1, padx=8, pady=5)
        self._row_slider(af, "Durée", 0.05, 0.5, 0.12, 1,
                         lambda v: self._upd("animation_duration", round(float(v), 3)))

        self._sec(p, "🌈  Effet couleur")
        ef = self._card(p)
        ctk.CTkLabel(ef, text="Mode", font=("", 11)).grid(
            row=0, column=0, padx=10, pady=5, sticky="w")
        self.var_effect = ctk.StringVar(value="fixed")
        ctk.CTkOptionMenu(
            ef, values=["fixed", "negative", "gradient"],
            variable=self.var_effect,
            command=lambda v: self._upd("effect_mode", v),
            width=120, fg_color=BG_CARD2, button_color=ACCENT
        ).grid(row=0, column=1, padx=8, pady=5)
        self._row_color(ef, "Gradient 1", "#FF6B6B", 1,
                        lambda c: self._upd("gradient_color1", c))
        self._row_color(ef, "Gradient 2", "#4ECDC4", 2,
                        lambda c: self._upd("gradient_color2", c))

        self._sec(p, "🔤  Police")
        ff = self._card(p)
        ff.columnconfigure(1, weight=1)
        ctk.CTkButton(
            ff, text="📂  Importer .ttf / .otf",
            command=self._import_font, height=32,
            font=("", 11), fg_color=BG_CARD2, hover_color=BG_CARD,
            border_width=1, border_color="#374151"
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=8, sticky="ew")
        self.lbl_font = ctk.CTkLabel(ff, text="Police système par défaut",
                                      text_color=TEXT_DIM, font=("", 10))
        self.lbl_font.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 6))

    # ── HELPERS UI ──────────────────────────────────────
    def _sec(self, parent, title):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=12, pady=(14, 2))
        ctk.CTkLabel(f, text=title, font=("", 12, "bold"),
                     text_color=TEXT_BRIGHT).pack(side="left")
        ctk.CTkFrame(f, fg_color="#2A2A3A", height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0))

    def _card(self, parent):
        f = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        f.pack(fill="x", padx=12, pady=(2, 4))
        f.columnconfigure(1, weight=1)
        return f

    def _row_slider(self, parent, label, mn, mx, default, row, cmd):
        ctk.CTkLabel(parent, text=label, font=("", 11),
                     text_color=TEXT_BRIGHT).grid(
            row=row, column=0, padx=10, pady=5, sticky="w")
        sld = ctk.CTkSlider(parent, from_=mn, to=mx, command=cmd,
                             button_color=ACCENT, button_hover_color="#5A52D5",
                             progress_color=ACCENT)
        sld.set(default)
        sld.grid(row=row, column=1, padx=8, pady=5, sticky="ew")

    def _row_color(self, parent, label, default, row, cmd):
        ctk.CTkLabel(parent, text=label, font=("", 11),
                     text_color=TEXT_BRIGHT).grid(
            row=row, column=0, padx=10, pady=5, sticky="w")
        ColorBtn(parent, default, cmd).grid(
            row=row, column=1, padx=8, pady=5, sticky="w")

    def _row_toggle(self, parent, label, default, row, cmd):
        ctk.CTkLabel(parent, text=label, font=("", 11),
                     text_color=TEXT_BRIGHT).grid(
            row=row, column=0, padx=10, pady=5, sticky="w")
        var = ctk.BooleanVar(value=default)
        sw = ctk.CTkSwitch(parent, text="", variable=var,
                            command=lambda: cmd(var.get()),
                            progress_color=ACCENT,
                            button_color="#FFFFFF")
        sw.grid(row=row, column=1, padx=8, pady=5, sticky="w")

    # ── WPD CHANGE ──────────────────────────────────────
    def _on_wpd_change(self, val):
        n = max(1, int(round(float(val))))
        self._wpd_label.configure(text=str(n))
        self._upd("words_per_display", n)

    # ───────────────────────────────────────────────────
    # STYLE UPDATE
    # ───────────────────────────────────────────────────
    def _upd(self, attr, val):
        setattr(self.style, attr, val)
        if self.word_timestamps:
            threading.Thread(target=self._refresh_preview, daemon=True).start()

    def _refresh_preview(self):
        self.player.refresh_style(self.style)

    # ───────────────────────────────────────────────────
    # ACTIONS
    # ───────────────────────────────────────────────────
    def _load_video(self):
        path = filedialog.askopenfilename(
            title="Sélectionner une vidéo",
            filetypes=[("Vidéo", "*.mp4 *.avi *.mov *.mkv *.webm")]
        )
        if path:
            self.video_path = path
            self.lbl_video.configure(
                text=f"✅  {os.path.basename(path)}", text_color="#10B981")
            self.btn_transcribe.configure(state="normal")
            self._set_prog(0, "Vidéo chargée.")

    def _import_font(self):
        path = filedialog.askopenfilename(
            title="Police", filetypes=[("Fonts", "*.ttf *.otf")])
        if path:
            self.style.font_path = path
            self.lbl_font.configure(text=os.path.basename(path),
                                    text_color=TEXT_BRIGHT)

    def _on_subtitles_edited(self, new_words):
        self.word_timestamps = new_words
        self.player.load(self.video_path, self.word_timestamps, self.style)

    def _transcribe(self):
        if not self.video_path:
            return
        self.btn_transcribe.configure(state="disabled", text="⏳  En cours…")
        self._set_prog(0.05, "Démarrage…")
        threading.Thread(target=self._run_transcription, daemon=True).start()

    def _run_transcription(self):
        try:
            t = Transcriber(model_size=self.model_size.get())
            words = t.transcribe(self.video_path, progress_callback=self._set_prog)
            for w in words:
                if not w["word"].strip():
                    w["word"] = "[……]"
            self.word_timestamps = words
            self.editor.load_words(words)
            self.player.load(self.video_path, words, self.style)
            self.btn_transcribe.configure(state="normal", text="🎙  Transcrire")
            self.btn_export_mp4.configure(state="normal")
            self.btn_export_srt.configure(state="normal")
            self.btn_preview_quick.configure(state="normal")
            self._set_prog(1.0, f"✅  {len(words)} mots transcrits.")
            messagebox.showinfo("✅  Transcription", f"{len(words)} mots détectés !")
        except Exception as e:
            messagebox.showerror("Erreur transcription", str(e))
            self.btn_transcribe.configure(state="normal", text="🎙  Transcrire")
            self._set_prog(0, f"Erreur : {str(e)[:60]}")

    def _preview_file(self):
        if not self.video_path or not self.word_timestamps:
            return
        out = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
        self.btn_preview_quick.configure(state="disabled", text="⏳ Génération…")
        self._set_prog(0.05, "Preview fichier en cours…")
        threading.Thread(target=self._run_export, args=(out, "preview"),
                         daemon=True).start()

    def _export_mp4(self):
        if not self.video_path or not self.word_timestamps:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if not path:
            return
        self.btn_export_mp4.configure(state="disabled", text="⏳ Export…")
        threading.Thread(target=self._run_export, args=(path, "export"),
                         daemon=True).start()

    def _run_export(self, out_path, mode):
        try:
            composer = VideoComposer(self.video_path, self.style)
            composer.compose(
                self.word_timestamps, out_path,
                mode=mode, progress_callback=self._set_prog
            )
            self._set_prog(1.0, f"✅  Export → {os.path.basename(out_path)}")
            if mode == "preview":
                if sys.platform == "darwin":
                    os.system(f"open '{out_path}'")
                elif sys.platform == "win32":
                    os.startfile(out_path)
                else:
                    os.system(f"xdg-open '{out_path}'")
                self.btn_preview_quick.configure(
                    state="normal", text="👁  Preview rapide (fichier)")
            else:
                self.btn_export_mp4.configure(
                    state="normal", text="💾  Exporter MP4")
                messagebox.showinfo("✅  Export terminé", f"Fichier : {out_path}")
        except Exception as e:
            messagebox.showerror("Erreur export", str(e))
            self.btn_export_mp4.configure(state="normal", text="💾  Exporter MP4")
            self.btn_preview_quick.configure(
                state="normal", text="👁  Preview rapide (fichier)")
            self._set_prog(0, f"Erreur : {str(e)[:60]}")

    def _export_srt(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".srt", filetypes=[("SRT", "*.srt")])
        if not path:
            return
        try:
            export_word_by_word_srt(self.word_timestamps, path)
            messagebox.showinfo("✅", f"SRT exporté : {path}")
        except Exception as e:
            messagebox.showerror("Erreur SRT", str(e))

    def _set_prog(self, v, msg=""):
        self.progress.set(v)
        if msg:
            self.lbl_prog.configure(text=msg)


if __name__ == "__main__":
    app = SubmagicApp()
    app.mainloop()
