# -*- coding: utf-8 -*-
"""
Can I Start? — Kivy-App für Windabschätzung, Drohnenverwaltung und Standort-Hilfen.

Wichtige Grenzen:
- Die Hellmann-Rechnung ist nur eine grobe meteorologische Schätzung.
- Die Karte zeigt OpenStreetMap-Kacheln direkt in einem zweiten App-Reiter.
- Diese Version enthält keine Flugzonenprüfung und keine rechtliche Freigabe.
"""
import json
import math
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup

try:
    from kivy_garden.mapview import MapView, MapMarker
    MAPVIEW_IMPORT_ERROR = None
except Exception as exc:
    MapView = None
    MapMarker = None
    MAPVIEW_IMPORT_ERROR = str(exc)

try:
    from plyer import gps
    GPS_IMPORT_ERROR = None
except Exception as exc:
    gps = None
    GPS_IMPORT_ERROR = str(exc)

try:
    from android.permissions import request_permissions, Permission
except Exception:
    request_permissions = None
    Permission = None


APP_NAME = "Can I Start?"
DIPUL_URL = "https://maptool-dipul.dfs.de/"
OSM_MAP_URL = "https://www.openstreetmap.org/"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

THEMES = {
    "dark": {
        "bg": (0.035, 0.050, 0.075, 1),
        "card": (0.085, 0.105, 0.145, 0.96),
        "field": (0.045, 0.060, 0.090, 1),
        "text": (0.94, 0.96, 1.00, 1),
        "muted": (0.58, 0.64, 0.73, 1),
        "accent": (0.28, 0.68, 1.00, 1),
        "red": (0.95, 0.25, 0.28, 1),
        "green": (0.20, 0.82, 0.48, 1),
        "amber": (1.00, 0.68, 0.22, 1),
    },
    "light": {
        "bg": (0.91, 0.94, 0.98, 1),
        "card": (1.00, 1.00, 1.00, 0.98),
        "field": (0.94, 0.96, 0.99, 1),
        "text": (0.09, 0.13, 0.19, 1),
        "muted": (0.35, 0.41, 0.50, 1),
        "accent": (0.06, 0.38, 0.78, 1),
        "red": (0.78, 0.12, 0.16, 1),
        "green": (0.04, 0.52, 0.26, 1),
        "amber": (0.62, 0.37, 0.02, 1),
    },
}

DEFAULT_DRONES = {
    # Wind resistance is a manufacturer/model specification, not a legal limit.
    "DJI Neo 2": 10.7,
    "Benutzerdefiniert": None,
}

TERRAIN_OPTIONS = [
    "0.14 - Küste/Wasser/offen",
    "0.20 - Wiese/Felder (Schätzwert)",
    "0.30 - Wald/bebaut (Schätzwert)",
    "Manuell",
]


def parse_number(value, field_name):
    raw = str(value).strip().replace(",", ".")
    if not raw:
        raise ValueError(f"Bitte „{field_name}“ ausfüllen.")
    try:
        result = float(raw)
    except ValueError:
        raise ValueError(f"„{field_name}“ muss eine Zahl sein.")
    if not math.isfinite(result):
        raise ValueError(f"„{field_name}“ ist ungültig.")
    return result


class GlassCard(BoxLayout):
    def __init__(self, app, **kwargs):
        self.app = app
        super().__init__(**kwargs)
        self.padding = dp(14)
        self.spacing = dp(9)
        self.radius = dp(18)
        with self.canvas.before:
            self._bg = Color(*self.app.theme["card"])
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            self._border_color = Color(1, 1, 1, 0.10)
            self._border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, self.radius),
                                width=1.0)
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, self.radius)

    def refresh_theme(self):
        self._bg.rgba = self.app.theme["card"]
        self._border_color.rgba = (1, 1, 1, 0.10) if self.app.current_theme == "dark" else (0.15, 0.2, 0.3, 0.12)


class StyledInput(TextInput):
    def __init__(self, app, **kwargs):
        self.app = app
        super().__init__(**kwargs)
        self.multiline = False
        self.size_hint_y = None
        self.height = dp(42)
        self.padding = [dp(11), dp(10), dp(11), dp(8)]
        self.background_normal = ""
        self.background_active = ""
        self.background_color = self.app.theme["field"]
        self.foreground_color = self.app.theme["text"]
        self.hint_text_color = self.app.theme["muted"]
        self.cursor_color = self.app.theme["accent"]
        self.font_size = "15sp"

    def refresh_theme(self):
        self.background_color = self.app.theme["field"]
        self.foreground_color = self.app.theme["text"]
        self.hint_text_color = self.app.theme["muted"]
        self.cursor_color = self.app.theme["accent"]


class CanIStartApp(App):
    def build(self):
        self.title = APP_NAME
        self.current_theme = "dark"
        self.theme = THEMES[self.current_theme]
        self.user_data_path = Path(self.user_data_dir)
        self.user_data_path.mkdir(parents=True, exist_ok=True)
        self.drone_file = self.user_data_path / "drones.json"
        self.drones = self.load_drones()
        self.custom_drone_names = set(self.drones) - set(DEFAULT_DRONES)
        self.cards = []
        self.inputs = []
        self.labels = []
        self.last_location = None
        self.terrain_status = "Standort abrufen, um eine unverbindliche Geländeschätzung zu versuchen."
        self.location_status = "Noch kein Standort erfasst."
        self.gps_fix_received = False
        self.zone_status = (
            "NICHT AUTOMATISCH GEPRÜFT\n"
            "Die amtliche Karte muss separat geprüft werden."
        )

        Window.clearcolor = self.theme["bg"]
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        self.root_layout = root
        with root.canvas.before:
            self._root_color = Color(*self.theme["bg"])
            self._root_rect = RoundedRectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_root, size=self._update_root)

        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        title = Label(text="[b]CAN I START?[/b]", markup=True, font_size="22sp",
                      color=self.theme["text"], halign="left", valign="middle")
        title.bind(size=title.setter("text_size"))
        header.add_widget(title)
        # Plain text instead of emoji/special-symbol theme icons: more reliable across Android fonts.
        self.theme_button = self.make_button("HELL / DUNKEL", self.toggle_theme, width=dp(118), color=self.theme["accent"])
        header.add_widget(self.theme_button)
        root.add_widget(header)

        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.wind_tab_button = self.make_button("WIND & DROHNEN", lambda *_: self.show_tab("wind"), color=self.theme["accent"], height=42)
        self.map_tab_button = self.make_button("KARTE", lambda *_: self.show_tab("map"), color=self.theme["card"], height=42)
        self.tab_bar.add_widget(self.wind_tab_button)
        self.tab_bar.add_widget(self.map_tab_button)
        root.add_widget(self.tab_bar)

        self.page_container = BoxLayout(orientation="vertical")
        self.wind_page = BoxLayout(orientation="vertical")
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.content = GridLayout(cols=1, spacing=dp(12), size_hint_y=None, padding=[0, 0, 0, dp(12)])
        self.content.bind(minimum_height=self.content.setter("height"))
        scroll.add_widget(self.content)
        self.wind_page.add_widget(scroll)
        root.add_widget(self.page_container)

        self.build_drone_card()
        self.build_wind_card()
        self.build_result_card()
        self.build_map_page()
        self.show_tab("wind")

        if request_permissions and Permission:
            try:
                request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION,
                                     Permission.INTERNET])
            except Exception:
                pass
        return root

    def _update_root(self, *_):
        self._root_rect.pos = self.root_layout.pos
        self._root_rect.size = self.root_layout.size

    def load_drones(self):
        drones = dict(DEFAULT_DRONES)
        try:
            if self.drone_file.exists():
                data = json.loads(self.drone_file.read_text(encoding="utf-8"))
                for name, limit in data.items():
                    if isinstance(name, str) and name.strip() and limit is not None:
                        val = float(limit)
                        if math.isfinite(val) and val > 0:
                            drones[name.strip()] = val
        except Exception:
            # Keep the built-in defaults if the local file is damaged.
            pass
        return drones

    def save_drones(self):
        custom = {}
        for name in self.custom_drone_names:
            value = self.drones.get(name)
            if value is not None:
                custom[name] = float(value)
        tmp = self.drone_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(custom, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.drone_file)

    def make_label(self, text, size=12, color=None, bold=False, height=None, align="left"):
        label = Label(text=text, font_size=f"{size}sp", color=color or self.theme["text"],
                      bold=bold, halign=align, valign="middle", size_hint_y=None,
                      height=dp(height or (26 if size <= 12 else 32)))
        label.bind(size=label.setter("text_size"))
        self.labels.append(label)
        return label

    def make_input(self, **kwargs):
        inp = StyledInput(self, **kwargs)
        self.inputs.append(inp)
        return inp

    def make_button(self, text, callback, width=None, color=None, height=42):
        btn = Button(text=text, size_hint_y=None, height=dp(height),
                     size_hint_x=None if width else 1, width=width or 0,
                     background_normal="", background_down="",
                     background_color=color or self.theme["accent"],
                     color=(1, 1, 1, 1), bold=True, font_size="12sp")
        btn.bind(on_release=callback)
        return btn

    def make_card(self, title, height):
        card = GlassCard(self, orientation="vertical", size_hint_y=None, height=dp(height))
        card.add_widget(self.make_label(title.upper(), size=11, color=self.theme["muted"], bold=True, height=22))
        self.cards.append(card)
        self.content.add_widget(card)
        return card

    def build_drone_card(self):
        card = self.make_card("Drohnen-Modell", 218)
        self.drone_spinner = Spinner(
            text="DJI Neo 2", values=sorted(self.drones.keys()), size_hint_y=None, height=dp(42),
            background_normal="", background_color=self.theme["field"], color=self.theme["text"],
        )
        self.drone_spinner.bind(text=self.on_drone_change)
        card.add_widget(self.drone_spinner)
        card.add_widget(self.make_label("Hersteller-/eigene Windgrenze (m/s)", height=22))
        self.max_wind_input = self.make_input(hint_text="z. B. 10,7")
        self.max_wind_input.text = "10.7"
        card.add_widget(self.max_wind_input)
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        row.add_widget(self.make_button("+ DROHNE HINZUFÜGEN", self.open_add_drone, color=self.theme["accent"]))
        self.delete_drone_button = self.make_button("AUSWAHL LÖSCHEN", self.delete_selected_drone,
                                                    color=self.theme["red"])
        row.add_widget(self.delete_drone_button)
        card.add_widget(row)
        card.add_widget(self.make_label("Eigene Drohnen bleiben lokal auf diesem Gerät gespeichert.", size=10,
                                        color=self.theme["muted"], height=18))

    def build_wind_card(self):
        card = self.make_card("Wind & Höhe", 315)
        card.add_widget(self.make_label("Gemessener Wind (m/s)", height=22))
        self.wind_input = self.make_input(hint_text="z. B. 4,1", input_filter="float")
        card.add_widget(self.wind_input)
        row = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        self.measure_height = self.make_input(hint_text="Messhöhe über Grund (m)", input_filter="float")
        self.target_height = self.make_input(hint_text="Zielhöhe über Grund (m)", input_filter="float")
        row.add_widget(self.measure_height)
        row.add_widget(self.target_height)
        card.add_widget(row)
        card.add_widget(self.make_label("Gelände / Hellmann-Exponent Alpha", height=22))
        self.alpha_spinner = Spinner(
            text=TERRAIN_OPTIONS[1], values=TERRAIN_OPTIONS, size_hint_y=None, height=dp(42),
            background_normal="", background_color=self.theme["field"], color=self.theme["text"]
        )
        self.alpha_spinner.bind(text=self.on_alpha_change)
        card.add_widget(self.alpha_spinner)
        self.alpha_manual = self.make_input(hint_text="Manueller Alpha-Wert (z. B. 0,20)", input_filter="float")
        self.alpha_manual.opacity = 0
        self.alpha_manual.disabled = True
        self.alpha_manual.height = dp(0)
        card.add_widget(self.alpha_manual)
        card.add_widget(self.make_label("Höhen sind über dem Boden (AGL), nicht über Meeresspiegel.", size=10,
                                        color=self.theme["muted"], height=18))
        card.add_widget(self.make_button("WIND BERECHNEN", self.calculate, color=self.theme["red"], height=46))

    def build_map_page(self):
        self.map_page = BoxLayout(orientation="vertical", spacing=dp(8), padding=[0, dp(4), 0, 0])
        self.map_page.add_widget(self.make_label(
            "OpenStreetMap-Karte. Verschieben und zoomen wie auf einer normalen Karte. "
            "Ohne GPS-Fix wird kein vermeintlicher eigener Standort angezeigt.",
            size=11, color=self.theme["muted"], height=48
        ))

        controls = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        self.gps_button = self.make_button("MEIN STANDORT", self.get_gps, color=self.theme["accent"])
        controls.add_widget(self.gps_button)
        controls.add_widget(self.make_button("KOORDINATEN EINGEBEN", self.manual_location, color=self.theme["accent"]))
        self.map_page.add_widget(controls)

        self.location_label = self.make_label(
            "Standort noch nicht bestimmt. Die Karte zeigt zunächst eine neutrale Übersicht über Deutschland.",
            size=10, color=self.theme["muted"], height=42
        )
        self.map_page.add_widget(self.location_label)

        if MapView is not None:
            # Map tiles load automatically; neutral center avoids inventing Berlin as the user's location.
            self.map_view = MapView(zoom=5, lat=51.1657, lon=10.4515)
            self.map_marker = None
            self.map_page.add_widget(self.map_view)
        else:
            self.map_view = None
            self.map_marker = None
            fallback = GlassCard(self, orientation="vertical", size_hint_y=1)
            fallback.add_widget(self.make_label(
                "Die Kartenkomponente konnte nicht geladen werden.\\n"
                f"Technischer Hinweis: {MAPVIEW_IMPORT_ERROR or 'unbekannter Fehler'}\\n\\n"
                "Prüfe, dass die MapView-Abhängigkeit in buildozer.spec enthalten ist und baue die APK neu.",
                size=11, color=self.theme["red"], height=130
            ))
            fallback.add_widget(self.make_button(
                "KARTE IM BROWSER ÖFFNEN", lambda *_: webbrowser.open(OSM_MAP_URL),
                color=self.theme["accent"]
            ))
            self.map_page.add_widget(fallback)

    def show_tab(self, tab_name):
        self.page_container.clear_widgets()
        if tab_name == "map":
            self.page_container.add_widget(self.map_page)
            self.wind_tab_button.background_color = self.theme["card"]
            self.map_tab_button.background_color = self.theme["accent"]
        else:
            self.page_container.add_widget(self.wind_page)
            self.wind_tab_button.background_color = self.theme["accent"]
            self.map_tab_button.background_color = self.theme["card"]
        self.active_tab = tab_name

    def build_result_card(self):
        card = self.make_card("Ergebnis", 142)
        self.result_label = self.make_label(
            "Messwerte eingeben und „Wind berechnen“ tippen.\\n"
            "Das Ergebnis ist eine Schätzung, keine Startfreigabe.",
            size=13, color=self.theme["text"], height=88, align="center"
        )
        card.add_widget(self.result_label)

    def on_drone_change(self, _spinner, name):
        value = self.drones.get(name)
        self.max_wind_input.text = "" if value is None else f"{float(value):g}"
        self.delete_drone_button.disabled = name not in self.custom_drone_names
        self.delete_drone_button.opacity = 1 if name in self.custom_drone_names else 0.45

    def on_alpha_change(self, _spinner, value):
        manual = value == "Manuell"
        self.alpha_manual.disabled = not manual
        self.alpha_manual.opacity = 1 if manual else 0
        self.alpha_manual.height = dp(42) if manual else dp(0)

    def open_add_drone(self, *_):
        layout = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(9))
        name_input = self.make_input(hint_text="Name, z. B. Mein Quadrocopter")
        wind_input = self.make_input(hint_text="Max. Wind laut Hersteller in m/s", input_filter="float")
        layout.add_widget(self.make_label("Drohnenname", height=22))
        layout.add_widget(name_input)
        layout.add_widget(self.make_label("Windgrenze in m/s", height=22))
        layout.add_widget(wind_input)
        error = self.make_label("", color=self.theme["red"], size=10, height=30)
        layout.add_widget(error)
        buttons = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        popup = Popup(title="Eigene Drohne hinzufügen", content=layout, size_hint=(0.9, 0.48))
        def save(*_):
            name = name_input.text.strip()
            try:
                limit = parse_number(wind_input.text, "Windgrenze")
                if limit <= 0 or limit > 100:
                    raise ValueError("Die Windgrenze muss größer als 0 und plausibel sein.")
                if not name:
                    raise ValueError("Bitte einen Namen eingeben.")
                if name in DEFAULT_DRONES:
                    raise ValueError("Dieser Name ist für ein eingebautes Modell reserviert.")
                self.drones[name] = limit
                self.custom_drone_names.add(name)
                self.save_drones()
                self.drone_spinner.values = sorted(self.drones.keys())
                self.drone_spinner.text = name
                self.max_wind_input.text = f"{limit:g}"
                popup.dismiss()
            except Exception as exc:
                error.text = str(exc)
        buttons.add_widget(self.make_button("SPEICHERN", save, color=self.theme["green"]))
        buttons.add_widget(self.make_button("ABBRECHEN", popup.dismiss, color=self.theme["red"]))
        layout.add_widget(buttons)
        popup.open()

    def delete_selected_drone(self, *_):
        name = self.drone_spinner.text
        if name not in self.custom_drone_names:
            return
        layout = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        layout.add_widget(self.make_label(f"„{name}“ wirklich löschen? Diese Aktion betrifft nur die lokale App-Datenbank.", height=55))
        buttons = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        popup = Popup(title="Drohne löschen?", content=layout, size_hint=(0.88, 0.32))
        def confirm(*_):
            self.drones.pop(name, None)
            self.custom_drone_names.discard(name)
            self.save_drones()
            self.drone_spinner.values = sorted(self.drones.keys())
            self.drone_spinner.text = "DJI Neo 2"
            popup.dismiss()
        buttons.add_widget(self.make_button("LÖSCHEN", confirm, color=self.theme["red"]))
        buttons.add_widget(self.make_button("ABBRECHEN", popup.dismiss, color=self.theme["accent"]))
        layout.add_widget(buttons)
        popup.open()

    def calculate(self, *_):
        try:
            v1 = parse_number(self.wind_input.text, "gemessener Wind")
            h1 = parse_number(self.measure_height.text, "Messhöhe")
            h2 = parse_number(self.target_height.text, "Zielhöhe")
            max_wind = parse_number(self.max_wind_input.text, "Windgrenze der Drohne")
            if v1 < 0:
                raise ValueError("Windgeschwindigkeit darf nicht negativ sein.")
            if h1 <= 0 or h2 <= 0:
                raise ValueError("Messhöhe und Zielhöhe müssen größer als 0 m sein.")
            if max_wind <= 0:
                raise ValueError("Die Windgrenze muss größer als 0 sein.")
            if self.alpha_spinner.text == "Manuell":
                alpha = parse_number(self.alpha_manual.text, "Hellmann-Exponent α")
            else:
                alpha = float(self.alpha_spinner.text.split("-")[0].strip())
            if not 0 <= alpha <= 1:
                raise ValueError("Alpha muss zwischen 0 und 1 liegen.")
            v2 = v1 * ((h2 / h1) ** alpha)
            kmh = v2 * 3.6
            margin = max_wind - v2
            if v2 > max_wind:
                color = self.theme["red"]
                status = "WINDGRENZE ÜBERSCHRITTEN - NICHT STARTEN"
            elif margin <= max_wind * 0.20:
                color = self.theme["amber"]
                status = "GERINGER PUFFER - VORSICHT"
            else:
                color = self.theme["green"]
                status = "UNTER DEM EINGEGEBENEN WINDLIMIT"
            self.result_label.color = color
            self.result_label.text = (
                f"{status}\n"
                f"Geschätzter Wind in {h2:g} m: {v2:.2f} m/s  /  {kmh:.1f} km/h\n"
                f"Eingegebene Modellgrenze: {max_wind:.2f} m/s\n"
                "Keine Startfreigabe: Böen, Turbulenzen, Akkustand und Regeln extra prüfen."
            )
        except Exception as exc:
            self.result_label.color = self.theme["red"]
            self.result_label.text = f"EINGABE PRÜFEN\n{exc}"

    def get_gps(self, *_):
        if gps is None:
            detail = GPS_IMPORT_ERROR or "Plyer-GPS konnte nicht geladen werden."
            self.location_label.text = "GPS-Komponente nicht geladen."
            self.show_message("GPS nicht verfügbar",
                              "Die GPS-Komponente ist in dieser App-Umgebung nicht verfügbar. "
                              "Technischer Hinweis: " + detail +
                              "\\n\\nPrüfe auf Android die Standortberechtigung. Alternativ Koordinaten manuell eingeben.")
            return
        self.gps_fix_received = False
        self.location_label.text = "GPS wird angefragt. Standortberechtigung erlauben und einige Sekunden warten."
        self.gps_button.text = "GPS WIRD GESUCHT ..."
        try:
            gps.configure(on_location=self.on_gps_location, on_status=self.on_gps_status)
            gps.start(minTime=1000, minDistance=1)
            Clock.schedule_once(lambda _dt: self._gps_timeout(), 25)
        except Exception as exc:
            self.gps_button.text = "MEIN STANDORT"
            self.location_label.text = f"GPS konnte nicht gestartet werden: {exc}"

    def _gps_timeout(self):
        self.stop_gps()
        if self.gps_fix_received:
            return
        self.gps_button.text = "MEIN STANDORT"
        self.location_label.text = (
            "Innerhalb von 25 Sekunden kam kein GPS-Fix. Standortdienste/Berechtigung prüfen "
            "oder Koordinaten manuell eingeben. Es wird kein Ersatzstandort erfunden."
        )

    def stop_gps(self):
        try:
            if gps:
                gps.stop()
        except Exception:
            pass

    def on_gps_status(self, stype, status):
        Clock.schedule_once(lambda _dt: setattr(self.location_label, "text",
            f"GPS-Status: {stype}: {status}"), 0)

    def on_gps_location(self, **kwargs):
        try:
            lat = float(kwargs.get("lat"))
            lon = float(kwargs.get("lon"))
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return
            self.gps_fix_received = True
            Clock.schedule_once(lambda _dt: self.set_location(lat, lon, "GPS"), 0)
            self.stop_gps()
        except Exception:
            pass

    def manual_location(self, *_):
        layout = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        lat_input = self.make_input(hint_text="Breitengrad, z. B. 54.35", input_filter="float")
        lon_input = self.make_input(hint_text="Längengrad, z. B. 10.12", input_filter="float")
        err = self.make_label("", color=self.theme["red"], size=10, height=28)
        layout.add_widget(self.make_label("Breitengrad", height=22))
        layout.add_widget(lat_input)
        layout.add_widget(self.make_label("Längengrad", height=22))
        layout.add_widget(lon_input)
        layout.add_widget(err)
        buttons = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        popup = Popup(title="Standort manuell eingeben", content=layout, size_hint=(0.9, 0.52))
        def save(*_):
            try:
                lat = parse_number(lat_input.text, "Breitengrad")
                lon = parse_number(lon_input.text, "Längengrad")
                if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                    raise ValueError("Koordinaten liegen außerhalb des gültigen Bereichs.")
                self.set_location(lat, lon, "manuell")
                popup.dismiss()
            except Exception as exc:
                err.text = str(exc)
        buttons.add_widget(self.make_button("ÜBERNEHMEN", save, color=self.theme["green"]))
        buttons.add_widget(self.make_button("ABBRECHEN", popup.dismiss, color=self.theme["red"]))
        layout.add_widget(buttons)
        popup.open()

    def set_location(self, lat, lon, source):
        self.last_location = (lat, lon)
        self.gps_button.text = "MEIN STANDORT"
        self.location_label.text = f"Standort ({source}): {lat:.6f}, {lon:.6f}"
        if self.map_view is not None:
            self.map_view.center_on(lat, lon)
            self.map_view.zoom = max(self.map_view.zoom, 15)
            try:
                if self.map_marker is not None:
                    self.map_view.remove_marker(self.map_marker)
                self.map_marker = MapMarker(lat=lat, lon=lon)
                self.map_view.add_marker(self.map_marker)
            except Exception as exc:
                self.location_label.text += f"\\nKarte konnte Markierung nicht setzen: {exc}"
        self.show_tab("map")

    def show_message(self, title, message):
        layout = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        layout.add_widget(self.make_label(message, size=12, height=110))
        popup = Popup(title=title, content=layout, size_hint=(0.9, 0.42))
        layout.add_widget(self.make_button("OK", popup.dismiss, color=self.theme["accent"]))
        popup.open()

    def toggle_theme(self, *_):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.theme = THEMES[self.current_theme]
        Window.clearcolor = self.theme["bg"]
        self._root_color.rgba = self.theme["bg"]
        for card in self.cards:
            card.refresh_theme()
        for inp in self.inputs:
            inp.refresh_theme()
        for label in self.labels:
            # Preserve meaningful status colors on the result and warning labels.
            if label is not getattr(self, "result_label", None):
                label.color = self.theme["muted"] if label.text.isupper() else self.theme["text"]
        self.result_label.color = self.theme["text"]
        self.theme_button.background_color = self.theme["accent"]
        self.show_tab(getattr(self, "active_tab", "wind"))


if __name__ == "__main__":
    CanIStartApp().run()
