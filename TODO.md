# To-do @zeit.reichtum

## Als Nächstes (Reihenfolge)
- [ ] Karussell T03-K auf Instagram und Facebook veröffentlichen (`publish.py T03-K --publish --fb`)
- [ ] Soundstripe-Musik: 12 ruhige Stücke ohne Gesang (je 2-3 Minuten) in `medien/musik/` legen, dann `python3 scripts/musik.py scan`
- [ ] Reel T03-R1 erstellen (Pitch, Fokus A, Video V04), mit Musik rendern, Test: `publish.py T03-R1 --test --fb`, dann `--publish --fb`
- [ ] Reel T02-R2 erstellen (läuft Do 19.11. 20:00, Video V13 · Fokus D · Spiegel · Pitch)
- [x] `publish.py` kann Reels (Instagram REELS-Container, Facebook-Video); noch nie gegen die Meta-API getestet
- [x] Musik-Mischung in `render_reel.py` und Musik-Pool `scripts/musik.py` gebaut

## Kommentar-Automatisierung selbst bauen (statt Manychat)
- [ ] Heute als Übergang: Meta Business Suite „Comment to message“ (Desktop), Stichwort START, eine Nachricht mit dem Link
- [ ] Eigener Webhook (Supabase Edge Function): Instagram `comments` und Facebook `feed` abonnieren, bei „START“ private Antwort senden, Button-Klick (Postback) löst Nachricht 2 aus
- [ ] Rechte ergänzen (instagram_manage_comments, instagram_manage_messages, pages_messaging, pages_manage_metadata) und Webhook-Adresse in der Meta-App eintragen
- [ ] Prüfen: reicht Standard Access (kein App Review) für das eigene Konto? Test mit zweitem Konto
- [ ] Flow-Texte aus Agent 11 beim Veröffentlichen pro Post speichern (`publish.py`)

## Facebook: Kommentar-Automatisierung (Stichwort → Nachricht)
- [ ] Variante wählen: Meta Business Suite „Comment to message“ (kostenlos, einfach, 1 private Antwort pro Kommentar, 7 Tage) oder Manychat „Facebook Comments 2.0“ mit „Alle Posts“
- [ ] Nur ein Tool pro Stichwort, sonst bekommen Frauen die Nachricht doppelt
- [ ] Erst danach Facebook-Posts mit Stichwort veröffentlichen (`--fb`)

## Musik
- [ ] Variante wählen: Instagram-Audio-API (Trend/Ambient aus der Bibliothek, nur kommerzielle Titel, keine Vorschau) oder lizenzfreie Ambient-Musik per ffmpeg unter den Originalton (10–15 %, Ordner `medien/musik/`)
- [ ] Gewählte Variante in `render_reel.py` bzw. `publish.py` einbauen

## Offen
- [ ] `data/forbidden-names.txt` füllen (Ersteller- und Kursnamen), sonst kann QA sie nicht prüfen
- [ ] Wochen-Pools KW47/KW48 sind nicht angelegt; die Fotos kommen derzeit aus dem KW46-Pool und den eigenen Fotos
- [ ] Ersatz für T04-R2 (schon veröffentlicht): Datei `output/T04-R2.md` bleibt als Archiv

- [ ] Story-Veröffentlichung (`publish.py T03-S`) ist neu und noch nie gegen Meta getestet (Instagram STORIES, Facebook photo_stories). Erst `--test --fb`, dann `--publish --fb`.
- [ ] T03-S Slide 3: „Ich lese mit.“ von Pamina bestätigen lassen, sonst streichen.
- [ ] Story-Videos mit Ton (`render_story.py T03-S`, danach `publish.py T03-S --test --fb`): Instagram STORIES mit video_url und Facebook video_stories (start → rupload → finish) sind neu und noch nie gegen Meta getestet. Falls es Probleme gibt: `--bilder` veröffentlicht die Story ohne Ton.

## Automatische Veröffentlichung (Stand 2026-11-18, 16:40)
- [x] Code: `scripts/warteschlange.py` (add / add-tag / status / cancel / run), `.github/workflows/publish.yml` (alle 10 Min), `sql/publish_queue.sql`; auf GitHub main gepusht (Commit c460a59).
- [ ] Pamina: Tabelle in Supabase anlegen (SQL aus `sql/publish_queue.sql`).
- [ ] Pamina: 6 Secrets in GitHub eintragen (SUPABASE_URL, SUPABASE_SECRET_KEY, SUPABASE_BUCKET, IG_USER_ID, FB_PAGE_ID, META_SYSTEM_TOKEN).
- [ ] Pamina: Meta-Token ohne Ablaufdatum prüfen; GitHub-Mails für Actions einschalten.
- [ ] Pamina: Netzwerk in Claude freigeben (*.supabase.co, graph.facebook.com, rupload.facebook.com), neuer Chat.
- [ ] Danach Claude: `python3 scripts/warteschlange.py add-tag 2026-11-19` (T04-R1 06:45, T04-S 17:30, T02-R2 20:00), Test mit Workflow „Run workflow“.
- Hinweis: Lokales Git hat noch den älteren Stand; vor `git pull` die ungetrackten Dateien (publish.py, warteschlange.py …) sichern oder erst committen.

## Inhalte für Do 19.11. (fertig, noch nicht eingeplant)
- [x] T04-R1 (06:45, Reel Typ A, Nurture, Marc Aurel 5,16, V05, Musik M02), T02-R2 (20:00, Reel Typ B, Pitch/Spiegel, V13, Musik M03), T04-S (17:30, Story Pitch/Spiegel, F05, Story-Videos mit Musik M04). Alle QA bestanden, gerendert, Standbilder geprüft.
- [ ] Einplanen sobald Netzwerk/Secrets stehen: `python3 scripts/warteschlange.py add-tag 2026-11-19`.
- [ ] Noch offen von heute: T03-R1 (Reel) und T03-K (Karussell) veröffentlichen; Reel-Upload gegen Meta testen.
