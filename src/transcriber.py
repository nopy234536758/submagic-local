#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transcriber — extraction audio + transcription mot-à-mot avec WhisperX.
"""

import os
import tempfile
from typing import Callable, List, Dict, Optional

import torch
import whisperx
from moviepy import VideoFileClip


class Transcriber:
    """
    Encapsule le pipeline WhisperX :
      1. extraction audio (WAV temporaire)
      2. transcription
      3. alignement forcé (timestamps par mot)
    """

    def __init__(self, model_size: str = "small", language: Optional[str] = None):
        self.model_size = model_size
        self.language = language
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "float32"

    def transcribe(
        self,
        video_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> List[Dict]:
        """
        Retourne une liste de dicts :
          [{"word": str, "start": float, "end": float}, ...]
        """
        def _prog(v, msg):
            if progress_callback:
                progress_callback(v, msg)

        # ── 1. Extraction audio ──
        _prog(0.10, "Extraction audio…")
        tmp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_audio.close()

        try:
            clip = VideoFileClip(video_path)
            if clip.audio is None:
                raise ValueError("La vidéo ne contient pas de piste audio.")
            clip.audio.write_audiofile(tmp_audio.name, logger=None)
            clip.close()
        except Exception as e:
            os.unlink(tmp_audio.name)
            raise RuntimeError(f"Impossible d'extraire l'audio : {e}") from e

        # ── 2. Transcription Whisper ──
        _prog(0.25, f"Chargement du modèle Whisper ({self.model_size})…")
        try:
            model = whisperx.load_model(
                self.model_size,
                self.device,
                compute_type=self.compute_type,
                language=self.language
            )
            audio = whisperx.load_audio(tmp_audio.name)

            _prog(0.40, "Transcription en cours…")
            result = model.transcribe(audio, batch_size=16)

            # ── 3. Alignement forcé ──
            _prog(0.65, "Alignement forcé (timestamps par mot)…")
            model_a, metadata = whisperx.load_align_model(
                language_code=result["language"],
                device=self.device
            )
            aligned = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                self.device,
                return_char_alignments=False
            )
        finally:
            os.unlink(tmp_audio.name)

        # ── 4. Extraction des timestamps ──
        _prog(0.85, "Extraction des timestamps…")
        words = []
        for seg in aligned.get("segments", []):
            for w in seg.get("words", []):
                # Certains mots n'ont pas de timestamps après alignement (ponctuation, etc.)
                if "start" not in w or "end" not in w:
                    continue
                words.append({
                    "word": w["word"].strip(),
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                })

        if not words:
            raise RuntimeError(
                "Aucun mot avec timestamp détecté. "
                "Vérifiez que la piste audio contient de la parole."
            )

        _prog(0.95, f"{len(words)} mots alignés.")
        return words
