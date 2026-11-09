# Medien-Ordner (nur lokal)

Alles hier ausser dieser Datei ist per `.gitignore` vom öffentlichen Repo ausgeschlossen.

```
medien/
  2026-KW47/
    woche.json                              Zuteilung der Woche (media.py init)
    fotos/2026-KW47-F01_kueche-morgenlicht-salbei.jpg   Gemini-Fotos (9:16)
    videos/T01-R1.mp4                       Reel-Videos – hier ablegen, Name = Slot
  eigene/                                   eigene Fotos von Pamina einfach hineinlegen
  bildliste.jsonl                           alle Fotos mit Beschreibung und Verwendung
```

- **Videos:** Datei genau wie der Slot benennen (`T01-R1.mp4`, `T05-R2.mov`). `python3 scripts/media.py status` zeigt, was noch fehlt.
- **Eigene Fotos:** in `eigene/` legen (JPEG oder HEIC). Claude sieht sie an, gibt ihnen einen sprechenden Namen
  (`eigen-001_garten-abendlicht.jpg`) und entfernt dabei die Metadaten (GPS = Wohnort). Keine Gesichter von Kindern.
- **Wiederverwendung:** In Stories darf jedes Foto beliebig oft vorkommen, im Feed (Karussell) höchstens einmal in 42 Tagen.
