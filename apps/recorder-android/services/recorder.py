import json
import os
import time
from datetime import datetime
from pathlib import Path

from jnius import autoclass


PACKAGE = "com.telaviva.recorder"

PythonService = autoclass("org.kivy.android.PythonService")
Context = autoclass("android.content.Context")
MediaProjectionManager = autoclass("android.media.projection.MediaProjectionManager")
MediaRecorder = autoclass("android.media.MediaRecorder")
AudioSource = autoclass("android.media.MediaRecorder$AudioSource")
VideoSource = autoclass("android.media.MediaRecorder$VideoSource")
OutputFormat = autoclass("android.media.MediaRecorder$OutputFormat")
VideoEncoder = autoclass("android.media.MediaRecorder$VideoEncoder")
AudioEncoder = autoclass("android.media.MediaRecorder$AudioEncoder")
DisplayManager = autoclass("android.hardware.display.DisplayManager")
ContentValues = autoclass("android.content.ContentValues")
MediaStore = autoclass("android.provider.MediaStore")
Environment = autoclass("android.os.Environment")
BuildVersion = autoclass("android.os.Build$VERSION")
Integer = autoclass("java.lang.Integer")
Handler = autoclass("android.os.Handler")
Looper = autoclass("android.os.Looper")
ProjectionBridge = autoclass(f"{PACKAGE}.ProjectionBridge")
ProjectionCallback = autoclass(f"{PACKAGE}.ProjectionBridge$ProjectionCallback")


context = PythonService.mService
files_dir = Path(str(context.getFilesDir().getAbsolutePath()))
state_path = files_dir / "recorder.state"
stop_path = files_dir / "recorder.stop"


def write_state(status, **extra):
    payload = {"status": status, **extra}
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, state_path)


def create_media_store_target():
    resolver = context.getContentResolver()
    values = ContentValues()
    filename = f"TelaViva-{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp4"

    values.put("display_name", filename)
    values.put("mime_type", "video/mp4")

    if int(BuildVersion.SDK_INT) >= 29:
        values.put(
            "relative_path",
            f"{Environment.DIRECTORY_MOVIES}/TelaViva",
        )
        values.put("is_pending", Integer.valueOf(1))
        collection = MediaStore.Video.Media.getContentUri(
            MediaStore.VOLUME_EXTERNAL_PRIMARY
        )
    else:
        collection = MediaStore.Video.Media.EXTERNAL_CONTENT_URI

    uri = resolver.insert(collection, values)
    if uri is None:
        raise RuntimeError("Android não criou o arquivo de vídeo no MediaStore")

    pfd = resolver.openFileDescriptor(uri, "w")
    if pfd is None:
        resolver.delete(uri, None, None)
        raise RuntimeError("Android não abriu o arquivo de saída")

    return resolver, uri, pfd


def publish_media_store_target(resolver, uri):
    if int(BuildVersion.SDK_INT) >= 29:
        values = ContentValues()
        values.put("is_pending", Integer.valueOf(0))
        resolver.update(uri, values, None, None)


def delete_media_store_target(resolver, uri):
    try:
        resolver.delete(uri, None, None)
    except Exception:
        pass


def build_recorder(payload, file_descriptor):
    recorder = MediaRecorder()
    recorder.setAudioSource(AudioSource.MIC)
    recorder.setVideoSource(VideoSource.SURFACE)
    recorder.setOutputFormat(OutputFormat.MPEG_4)

    recorder.setVideoEncoder(VideoEncoder.H264)
    recorder.setVideoSize(int(payload["width"]), int(payload["height"]))
    recorder.setVideoFrameRate(int(payload.get("fps", 30)))
    recorder.setVideoEncodingBitRate(int(payload.get("video_bitrate", 8_000_000)))

    recorder.setAudioEncoder(AudioEncoder.AAC)
    recorder.setAudioChannels(1)
    recorder.setAudioSamplingRate(int(payload.get("audio_sample_rate", 44_100)))
    recorder.setAudioEncodingBitRate(int(payload.get("audio_bitrate", 128_000)))

    recorder.setOutputFile(file_descriptor)
    recorder.prepare()
    return recorder


def cleanup(recorder, virtual_display, projection, callback, pfd):
    if virtual_display is not None:
        try:
            virtual_display.release()
        except Exception:
            pass

    if recorder is not None:
        try:
            recorder.reset()
        except Exception:
            pass
        try:
            recorder.release()
        except Exception:
            pass

    if projection is not None:
        if callback is not None:
            try:
                projection.unregisterCallback(callback)
            except Exception:
                pass
        try:
            projection.stop()
        except Exception:
            pass

    if pfd is not None:
        try:
            pfd.close()
        except Exception:
            pass


def main():
    raw_argument = os.environ.get("PYTHON_SERVICE_ARGUMENT", "")
    payload = json.loads(raw_argument)

    stop_path.unlink(missing_ok=True)
    write_state("starting")

    resolver = None
    uri = None
    pfd = None
    recorder = None
    projection = None
    virtual_display = None
    callback = None
    recorder_started = False
    finalized = False

    try:
        result_data = ProjectionBridge.intentFromBase64(payload["intent"])
        projection_manager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE)
        projection = projection_manager.getMediaProjection(
            int(payload["result_code"]),
            result_data,
        )
        if projection is None:
            raise RuntimeError("Android não retornou uma sessão MediaProjection")

        # Android 14+ requires a callback before createVirtualDisplay().
        callback = ProjectionCallback()
        handler = Handler(Looper.getMainLooper())
        projection.registerCallback(callback, handler)

        resolver, uri, pfd = create_media_store_target()
        recorder = build_recorder(payload, pfd.getFileDescriptor())

        virtual_display = projection.createVirtualDisplay(
            "TelaVivaRecorder",
            int(payload["width"]),
            int(payload["height"]),
            int(payload["density"]),
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            recorder.getSurface(),
            None,
            handler,
        )
        if virtual_display is None:
            raise RuntimeError("Android não criou a tela virtual")

        recorder.start()
        recorder_started = True
        write_state("recording", uri=str(uri))

        while True:
            if stop_path.exists() or callback.isStopped():
                break
            time.sleep(0.20)

        write_state("stopping", uri=str(uri))

        # stop() finalizes the MP4 container. It can throw if recording was
        # shorter than the codec startup interval, so handle that explicitly.
        recorder.stop()
        recorder_started = False
        publish_media_store_target(resolver, uri)
        finalized = True
        write_state("stopped", uri=str(uri))

    except Exception as exc:
        if recorder_started and recorder is not None:
            try:
                recorder.stop()
            except Exception:
                pass
        if resolver is not None and uri is not None and not finalized:
            delete_media_store_target(resolver, uri)
        write_state("error", message=str(exc))
    finally:
        cleanup(recorder, virtual_display, projection, callback, pfd)
        stop_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
