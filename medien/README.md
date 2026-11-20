# Medien-Ordner (nur lokal)

Alles hier ausser dieser Datei ist per `.gitignore` vom öffentlichen Repo ausgeschlossen.

```
medien/
  2026-KW47/
    woche.json                              Zuteilung der Woche (media.py init)
    fotos/2026-KW47-F01_kueche-morgenlicht-salbei.jpg   Gemini-Fotos (9:16)
    videos/T01-R1.mp4                       (alt) Reel-Videos pro Woche
  videos/2026-12/2026-12-V01.mp4            Monats-Videos – hier ablegen, Name = ID (Skill videos-monat)
  eigene-videos/                            eigene Handy-Videos einfach hineinlegen
  videoliste.jsonl                          alle Videos mit Verwendung (max. 3×, 10 Tage Pause)
  eigene/                                   eigene Fotos von Pamina einfach hineinlegen
  bildliste.jsonl                           alle Fotos mit Beschreibung und Verwendung
```

- **Videos:** Monats-Videos genau wie die ID benennen (`2026-12-V01.mp4`). `python3 scripts/media.py monat-status` zeigt, was noch fehlt.
- **Eigene Videos:** in `eigene-videos/` legen. Sie werden auf 9:16 zugeschnitten, die Metadaten (GPS = Wohnort) entfernt. Keine Gesichter von Kindern.
- **Eigene Fotos:** in `eigene/` legen (JPEG oder HEIC). Claude sieht sie an, gibt ihnen einen sprechenden Namen
  (`eigen-001_garten-abendlicht.jpg`) und entfernt dabei die Metadaten (GPS = Wohnort). Keine Gesichter von Kindern.
- **Wiederverwendung:** In Stories darf jedes Foto beliebig oft vorkommen, im Feed (Karussell) höchstens einmal in 42 Tagen.

## Musik (Soundstripe)
- MP3/WAV in `medien/musik/` legen, dann `python3 scripts/musik.py scan` (benennt sie `M01_titel.mp3` und teilt sie in 10-Sekunden-Abschnitte).
- `python3 scripts/musik.py status` zeigt, ob die Stücke für den Monat reichen. `render_reel.py` mischt die Musik automatisch leise unter den Originalton (`--musik aus` = ohne).
- Nur Stücke mit gültiger Soundstripe-Lizenz. Proof of License im Soundstripe-Konto aufbewahren.
