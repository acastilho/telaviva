__version__ = "0.1.0"

import json
import os
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from android import activity as android_activity
from android.permissions import Permission, check_permission, request_permissions
from jnius import autoclass


REQUEST_MEDIA_PROJECTION = 4107
PACKAGE = "com.telaviva.recorder"

PythonActivity = autoclass("org.kivy.android.PythonActivity")
Activity = autoclass("android.app.Activity")
Context = autoclass("android.content.Context")
DisplayMetrics = autoclass("android.util.DisplayMetrics")
ProjectionBridge = autoclass(f"{PACKAGE}.ProjectionBridge")
ServiceRecorder = autoclass(f"{PACKAGE}.ServiceRecorder")


class RecorderApp(App):
    def build(self):
        self.activity = PythonActivity.mActivity
        self.projection_manager = self.activity.getSystemService(
            Context.MEDIA_PROJECTION_SERVICE
        )
        self._activity_result_bound = False
        self._state_path = Path(str(self.activity.getFilesDir().getAbsolutePath())) / "recorder.state"
        self._stop_path = Path(str(self.activity.getFilesDir().getAbsolutePath())) / "recorder.stop"

        root = BoxLayout(
            orientation="vertical",
            spacing=dp(14),
            padding=dp(22),
        )

        self.status = Label(
            text="Pronto para gravar tela + microfone",
            halign="center",
            valign="middle",
        )
        self.status.bind(size=lambda widget, _: setattr(widget, "text_size", widget.size))

        self.start_button = Button(
            text="GRAVAR",
            size_hint_y=None,
            height=dp(64),
        )
        self.start_button.bind(on_release=self.start_recording)

        self.stop_button = Button(
            text="PARAR",
            size_hint_y=None,
            height=dp(64),
            disabled=True,
        )
        self.stop_button.bind(on_release=self.stop_recording)

        hint = Label(
            text=(
                "Para gravar a voz do ChatGPT: use o chat normal, toque em "
                "'Ler em voz alta' e deixe este app com o microfone."
            ),
            halign="center",
            valign="middle",
        )
        hint.bind(size=lambda widget, _: setattr(widget, "text_size", widget.size))

        root.add_widget(self.status)
        root.add_widget(self.start_button)
        root.add_widget(self.stop_button)
        root.add_widget(hint)

        Clock.schedule_interval(self._refresh_state, 0.75)
        return root

    def start_recording(self, *_):
        if not check_permission(Permission.RECORD_AUDIO):
            self.status.text = "Precisamos da permissão do microfone."
            request_permissions(
                [Permission.RECORD_AUDIO],
                self._after_microphone_permission,
            )
            return
        self._request_screen_capture()

    def _after_microphone_permission(self, _permissions, grants):
        if not grants or not all(grants):
            self.status.text = "Permissão do microfone negada."
            return
        self._request_screen_capture()

    def _request_screen_capture(self):
        self._clear_stop_flag()
        if not self._activity_result_bound:
            android_activity.bind(on_activity_result=self._on_activity_result)
            self._activity_result_bound = True

        self.status.text = "Autorize a captura da tela no Android."
        capture_intent = self.projection_manager.createScreenCaptureIntent()
        self.activity.startActivityForResult(capture_intent, REQUEST_MEDIA_PROJECTION)

    def _on_activity_result(self, request_code, result_code, data):
        if request_code != REQUEST_MEDIA_PROJECTION:
            return

        if result_code != Activity.RESULT_OK or data is None:
            self.status.text = "Captura de tela cancelada."
            return

        try:
            metrics = DisplayMetrics()
            self.activity.getWindowManager().getDefaultDisplay().getRealMetrics(metrics)

            # H.264 encoders are happier with even dimensions.
            width = int(metrics.widthPixels) // 2 * 2
            height = int(metrics.heightPixels) // 2 * 2
            density = int(metrics.densityDpi)

            payload = {
                "result_code": int(result_code),
                "intent": str(ProjectionBridge.intentToBase64(data)),
                "width": width,
                "height": height,
                "density": density,
                "fps": 30,
                "video_bitrate": 8_000_000,
                "audio_bitrate": 128_000,
                "audio_sample_rate": 44_100,
            }

            # The generated python-for-android service enters foreground mode
            # before executing services/recorder.py. That ordering is required
            # by Android 14+ before getMediaProjection() is called.
            ServiceRecorder.start(self.activity, json.dumps(payload))
            self.status.text = "Iniciando gravação..."
            self.start_button.disabled = True
            self.stop_button.disabled = False
        except Exception as exc:  # surfaced on-device for fast diagnosis
            self.status.text = f"Falha ao iniciar: {exc}"
            self.start_button.disabled = False
            self.stop_button.disabled = True

    def stop_recording(self, *_):
        try:
            self._stop_path.write_text("stop", encoding="utf-8")
            self.status.text = "Finalizando MP4..."
            self.stop_button.disabled = True
        except Exception as exc:
            self.status.text = f"Falha ao solicitar parada: {exc}"

    def _clear_stop_flag(self):
        try:
            self._stop_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _refresh_state(self, _dt):
        if not self._state_path.exists():
            return

        try:
            state = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return

        status = state.get("status")
        if status == "recording":
            self.status.text = "● GRAVANDO — agora pode abrir o ChatGPT"
            self.start_button.disabled = True
            self.stop_button.disabled = False
        elif status == "stopping":
            self.status.text = "Finalizando MP4..."
            self.stop_button.disabled = True
        elif status == "stopped":
            uri = state.get("uri", "Vídeo salvo em Filmes/TelaViva")
            self.status.text = f"Gravação concluída\n{uri}"
            self.start_button.disabled = False
            self.stop_button.disabled = True
        elif status == "error":
            self.status.text = f"Erro: {state.get('message', 'desconhecido')}"
            self.start_button.disabled = False
            self.stop_button.disabled = True

    def on_stop(self):
        if self._activity_result_bound:
            try:
                android_activity.unbind(on_activity_result=self._on_activity_result)
            except Exception:
                pass


if __name__ == "__main__":
    RecorderApp().run()
