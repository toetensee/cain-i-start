# Can I Start? — Android-App

## Enthaltene Dateien
- `main.py`: Kivy-App, Windabschätzung, Drohnen hinzufügen/löschen, lokale Speicherung, GPS und Geländeschätzung.
- `buildozer.spec`: Buildozer-Konfiguration für Android.
- `.github/workflows/build.yml`: GitHub Actions Workflow zum Erstellen einer Debug-APK.

## Funktionen
- Hellmann-Potenzgesetz: `v2 = v1 * (h2 / h1) ** alpha`.
- Eingaben akzeptieren Komma oder Punkt.
- Eigene Drohnen mit Windgrenze anlegen, lokal speichern und wieder löschen.
- GPS über Android-Standortberechtigung; manuelle Koordinaten als Fallback.
- Kartenansicht über OpenStreetMap im Browser.
- Öffnet die offizielle deutsche dipul-Geozonenkarte zur manuellen Prüfung.
- Versucht anhand nahegelegener OpenStreetMap-Tags eine grobe Gelände-Empfehlung (α). Das ist kein Messwert und kann falsch/unvollständig sein.

## Wichtige Grenzen
Die App prüft Flugverbotszonen **nicht automatisch** und erteilt keine rechtliche Startfreigabe. Die dipul-Karte wird geöffnet, damit die Person vor Ort die Geozonen und Bedingungen selbst kontrolliert. Es wurde keine frei nutzbare, dokumentierte Live-Schnittstelle für eine verlässliche automatische Freigabe eingebaut. Die Windberechnung ist nur eine grobe Schätzung; Böen, Turbulenzen, Hindernisse und die Regeln sind separat zu berücksichtigen.

## Build über GitHub
1. Lege `main.py`, `buildozer.spec` und `.github/workflows/build.yml` im Repository ab.
2. Commit/pushe die Dateien auf `main` oder `master`.
3. Öffne im Repository den Reiter **Actions** und wähle den Workflow „Build Can I Start APK“.
4. Nach erfolgreichem Lauf den Artifact `Can-I-Start-APK` herunterladen und entpacken.
5. Die enthaltene APK auf Android installieren. Android kann vor der Installation aus einer unbekannten Quelle warnen.

## Lokaler Windows-Test
Kivy muss in deiner Python-Umgebung installiert sein:
`python -m pip install kivy plyer`
Dann aus dem Projektordner:
`python main.py`
GPS ist bei einem gewöhnlichen Windows-PC normalerweise nicht verfügbar; dort Koordinaten manuell eingeben.

## Datenschutz / Daten
Eigene Drohnen werden in `App.user_data_dir/drones.json` auf dem jeweiligen Gerät gespeichert. Koordinaten werden nicht in einer Cloud gespeichert. Bei der Geländeschätzung werden Koordinaten an den öffentlichen OpenStreetMap Overpass-Dienst übertragen; zum Anzeigen der Karte werden Koordinaten an OpenStreetMap übergeben. Das ist erforderlich, damit diese Online-Dienste passende Kartendaten zurückgeben können.
