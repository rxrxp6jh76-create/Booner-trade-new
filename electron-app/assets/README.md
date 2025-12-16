# Booner Trade Desktop App Assets

## Benötigte Dateien für DMG Build:

1. **dmg-background.png** (660x400 px)
   - Hintergrund für das DMG Installer-Fenster
   - Aktuell: SVG Version vorhanden, PNG muss erstellt werden
   - Siehe: ../CREATE-ASSETS.md für Anleitung

2. **logo.icns** (Multi-Resolution Icon)
   - App-Icon für macOS
   - Aktuell: SVG Version vorhanden, ICNS muss erstellt werden
   - Siehe: ../CREATE-ASSETS.md für Anleitung

## Vorhandene Dateien:

- `dmg-background.svg` - Vektor-Version des DMG Hintergrunds
- `logo.svg` - Vektor-Version des App-Icons

## Build-Prozess:

Das `build.sh` Script versucht automatisch:
1. `dmg-background.png` aus SVG zu erstellen (falls ImageMagick installiert)
2. Falls nicht möglich, wird electron-builder Standard verwendet
3. `logo.icns` muss manuell erstellt und hier abgelegt werden

## Manuelle Erstellung empfohlen:

Für beste Qualität, erstelle die Assets manuell mit den Tools in CREATE-ASSETS.md
und platziere sie in diesem Verzeichnis vor dem Build.
