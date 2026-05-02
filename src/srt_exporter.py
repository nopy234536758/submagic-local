#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
srt_exporter — génère un fichier .srt depuis les word timestamps.
Regroupe les mots par segments de N mots maximum.
"""

from typing import List, Dict


def _format_time(sec: float) -> str:
    """Convertit des secondes en format SRT : HH:MM:SS,mmm"""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def export_srt(
    word_timestamps: List[Dict],
    output_path: str,
    words_per_block: int = 5
) -> str:
    """
    Génère et écrit un fichier SRT.
    Retourne le chemin du fichier créé.

    Paramètres
    ----------
    word_timestamps : liste de {"word": str, "start": float, "end": float}
    output_path     : chemin du fichier .srt à créer
    words_per_block : nombre de mots par sous-titre
    """
    if not word_timestamps:
        raise ValueError("Aucun mot à exporter.")

    blocks = []
    for i in range(0, len(word_timestamps), words_per_block):
        chunk = word_timestamps[i:i + words_per_block]
        start = chunk[0]["start"]
        end = chunk[-1]["end"]
        text = " ".join(w["word"] for w in chunk)
        blocks.append((start, end, text))

    lines = []
    for idx, (start, end, text) in enumerate(blocks, start=1):
        lines.append(str(idx))
        lines.append(f"{_format_time(start)} --> {_format_time(end)}")
        lines.append(text)
        lines.append("")

    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path


def export_word_by_word_srt(
    word_timestamps: List[Dict],
    output_path: str
) -> str:
    """
    Génère un SRT avec un sous-titre par mot (idéal pour le karaoké).
    """
    if not word_timestamps:
        raise ValueError("Aucun mot à exporter.")

    lines = []
    for idx, w in enumerate(word_timestamps, start=1):
        lines.append(str(idx))
        lines.append(f"{_format_time(w['start'])} --> {_format_time(w['end'])}")
        lines.append(w["word"])
        lines.append("")

    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path
