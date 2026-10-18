# Can I Start? - aktualisierte Android-App

## Dateien
- `main.py`: Eine zentrale Python-Datei für die Windberechnung, Drohnenverwaltung und den Karten-Reiter.
- `buildozer.spec`: Android-Abhängigkeiten und Berechtigungen.
- `.github/workflows/build.yml`: GitHub Actions Build-Workflow.

## Änderungen
- Zwei klar beschriftete Reiter: **WIND & DROHNEN** und **KARTE**.
- Die interaktive OpenStreetMap-Karte ist direkt in der App eingebettet und lädt Kacheln bei App-Start. Sie startet auf einer neutralen Deutschland-Übersicht und behauptet nicht, dass der Nutzer in Berlin sei.
- Im Karten-Reiter kann der Standort per GPS ermittelt oder manuell eingegeben werden. Bei GPS-Fehlern wird kein Standort erfunden; eine verständliche Fehlermeldung wird angezeigt.
- Flugzonen-/dipul-Funktionen und die Gelände-Abfrage wurden aus der Oberfläche entfernt.
- Emojis und dekorative Symbolzeichen wurden aus den Bedienflächen entfernt. Kivy verwendet nicht automatisch für alle Plattformen eine vollständige farbige Emoji-Schrift; einfache Textbeschriftungen sind zuverlässiger.
- Eigene Drohnen werden lokal in `App.user_data_dir/drones.json` gespeichert.

## Build
1. Dateien ins Repository kopieren und committen.
2. GitHub Actions öffnen und den Workflow **Build Can I Start APK** starten.
3. Das Artefakt `Can-I-Start-APK` herunterladen und entpacken.
4. APK auf Android installieren.

## Hinweise
Die Karte benötigt eine Internetverbindung. Die Kartendarstellung stammt von OpenStreetMap und unterliegt deren Nutzungsrichtlinien/Attribution. GPS funktioniert nur, wenn Android Standortdienste und App-Berechtigungen erlauben; ein GPS-Fix kann im Gebäude lange dauern oder ausbleiben.

Die Windberechnung ist eine vereinfachte Schätzung. Sie ist keine Startfreigabe und berücksichtigt nicht alle Böen oder Turbulenzen.

### Android-Mindestversion

Der Build verwendet `android.minapi = 28` (Android 9.0). Die Mindest-API wird zusätzlich in GitHub Actions über `ANDROIDMINAPI` gesetzt, damit die Android-Buildwerkzeuge denselben Zielwert erhalten. Das ist ein vorsorglicher Workaround für den CPython-Buildfehler rund um `preadv()`/`pwritev()`. Android-Versionen unter 9.0 werden damit nicht mehr unterstützt.
