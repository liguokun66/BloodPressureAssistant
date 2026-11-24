# -*- coding: utf-8 -*-
"""
语音识别模块
- Android：调用系统 SpeechRecognizer（中文 zh-CN）
- 桌面：使用 speech_recognition（Google Web API，需联网）
- 识别失败时抛出异常，由 UI 提示用户改用键盘输入
"""

import threading
import traceback

from kivy.logger import Logger


def _run_on_ui(fn):
    """在 Android 主（UI）线程执行 fn；拿不到 activity 时直接执行。"""
    try:
        from jnius import autoclass, PythonJavaClass, java_method
        activity = autoclass('org.kivy.android.PythonActivity').mActivity

        class _Task(PythonJavaClass):
            __javainterfaces__ = ['java/lang/Runnable']

            def __init__(self, f):
                super().__init__()
                self._f = f

            @java_method('()V')
            def run(self):
                try:
                    self._f()
                except Exception:
                    Logger.info('voice: ui task failed\n%s'
                                % traceback.format_exc())

        if activity is not None:
            activity.runOnUiThread(_Task(fn))
        else:
            fn()
    except Exception:
        fn()


class VoiceRecognizer:
    """语音识别封装，支持 Android / 桌面"""

    def __init__(self, on_result=None, on_partial=None, on_error=None, on_ready=None):
        # on_result(text) / on_partial(text) / on_error(msg) / on_ready()
        self._on_result = on_result
        self._on_partial = on_partial
        self._on_error = on_error
        self._on_ready = on_ready
        self._recognizer = None
        self._android_listener = None
        self._sr_recognizer = None
        self._listening = False

    # ---------------- 可用性检测 ----------------
    def backend(self):
        """返回当前可用的后端：'android' / 'desktop' / None"""
        try:
            import jnius  # noqa
            return 'android'
        except Exception:
            pass
        try:
            import speech_recognition as sr  # noqa
            return 'desktop'
        except Exception:
            pass
        return None

    def is_available(self):
        b = self.backend()
        if b == 'android':
            return self._android_available()
        return b is not None

    @staticmethod
    def _has_mic_permission():
        try:
            from android.permissions import check_permission, Permission
            return bool(check_permission(Permission.RECORD_AUDIO))
        except Exception:
            return True

    def _android_available(self):
        """系统是否存在可用的语音识别服务（Android 11+ 需要在 manifest 声明 queries）"""
        try:
            from jnius import autoclass
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            if activity is None:
                return False
            SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
            return bool(SpeechRecognizer.isRecognitionAvailable(activity))
        except Exception:
            # 拿不准时放行，交给启动阶段的异常处理给出具体提示
            return True

    # ---------------- 开始 / 停止 ----------------
    def start(self):
        if self._listening:
            return
        b = self.backend()
        if b == 'android':
            self._start_android()
        elif b == 'desktop':
            self._start_desktop()
        else:
            self._fire_error('当前设备不支持语音识别，请使用键盘输入。')

    def stop(self):
        self._listening = False
        try:
            rec = self._recognizer
            if rec is not None and self.backend() == 'android':
                _run_on_ui(lambda: rec.stopListening())
        except Exception:
            pass
        try:
            if self._sr_recognizer is not None and self.backend() == 'desktop':
                pass
        except Exception:
            pass

    def _fire_result(self, text):
        if self._on_result:
            self._on_result(text)

    def _fire_partial(self, text):
        if self._on_partial:
            self._on_partial(text)

    def _fire_error(self, msg):
        if self._on_error:
            self._on_error(msg)

    def _fire_ready(self):
        if self._on_ready:
            self._on_ready()

    # ---------------- Android 实现 ----------------
    def _start_android(self):
        """切到 Android 主（UI）线程再创建/启动 SpeechRecognizer。

        Kivy 的 Python 主循环跑在 SDL 自己的线程上，而 SpeechRecognizer
        要求在主 Looper 上创建，否则会抛
        “SpeechRecognizer should be used only with the main thread”。
        """
        _run_on_ui(self._start_android_ui)

    def _start_android_ui(self):
        try:
            from jnius import autoclass, PythonJavaClass, java_method
        except Exception as e:
            self._fire_error('无法加载语音组件：%s（%s）'
                             % (type(e).__name__, e))
            return

        Intent = autoclass('android.content.Intent')
        RecognizerIntent = autoclass('android.speech.RecognizerIntent')
        SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')

        try:
            activity = PythonActivity.mActivity
        except Exception:
            activity = None
        if activity is None:
            self._fire_error('无法获取应用界面，请重启应用后再试。')
            return
        if not self._has_mic_permission():
            self._fire_error('没有麦克风权限：请在系统设置里允许使用麦克风后重试。')
            return
        try:
            if not SpeechRecognizer.isRecognitionAvailable(activity):
                self._fire_error('当前设备没有可用的语音识别服务。\n\n'
                                 '常见原因：\n'
                                 '· 厂商系统删除了 Google 语音识别\n'
                                 '· 未安装支持中文的输入法/识别服务\n\n'
                                 '可先用键盘输入，或在系统里启用语音识别服务。')
                return
        except Exception as e:
            Logger.info('voice: isRecognitionAvailable 失败 %s（%s）'
                        % (type(e).__name__, e))

        outer = self

        def _post(fn, *args):
            """RecognitionListener 回调在 Android UI 线程，派发回 Kivy 主循环，
            避免跨线程改控件。"""
            try:
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: fn(*args), 0)
            except Exception:
                pass

        class _Listener(PythonJavaClass):
            __javainterfaces__ = ['android/speech/RecognitionListener']

            def __init__(self):
                super().__init__()
                self.partial_text = ''

            @java_method('(Landroid/os/Bundle;)V')
            def onReadyForSpeech(self, params):
                _post(outer._fire_ready)

            @java_method('()V')
            def onBeginningOfSpeech(self):
                pass

            @java_method('(F)V')
            def onRmsChanged(self, rmsdB):
                pass

            @java_method('([B)V')
            def onBufferReceived(self, buffer):
                pass

            @java_method('()V')
            def onEndOfSpeech(self):
                pass

            @java_method('(I)V')
            def onError(self, error):
                msg_map = {
                    1: '音频错误',
                    2: '客户端错误',
                    3: '没有麦克风权限',
                    4: '网络错误',
                    5: '网络超时',
                    6: '没有识别到语音',
                    7: '识别服务忙',
                    8: '服务器错误',
                    9: '没有听到语音，请重试',
                }
                outer._listening = False
                _post(outer._fire_error,
                      '%s（错误码 %d）' % (
                          msg_map.get(error, '识别失败'), error))

            @java_method('(Landroid/os/Bundle;)V')
            def onResults(self, results):
                try:
                    arr = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if arr is not None and arr.size() > 0:
                        text = arr.get(0)
                        outer._listening = False
                        _post(outer._fire_result, text if text else '')
                    else:
                        outer._listening = False
                        _post(outer._fire_error, '没有识别到内容，请重试。')
                except Exception as e:
                    outer._listening = False
                    _post(outer._fire_error, '识别结果解析失败：%s' % e)
                outer._listening = False

            @java_method('(Landroid/os/Bundle;)V')
            def onPartialResults(self, partial):
                try:
                    arr = partial.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if arr is not None and arr.size() > 0:
                        self.partial_text = arr.get(0) or ''
                        _post(outer._fire_partial, self.partial_text)
                except Exception:
                    pass

            @java_method('(ILandroid/os/Bundle;)V')
            def onEvent(self, eventType, params):
                pass

        try:
            try:
                self._recognizer = SpeechRecognizer.createSpeechRecognizer(
                    activity)
            except Exception:
                # 个别机型必须用 ApplicationContext 创建
                self._recognizer = SpeechRecognizer.createSpeechRecognizer(
                    activity.getApplicationContext())
            self._android_listener = _Listener()
            self._recognizer.setRecognitionListener(self._android_listener)

            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, 'zh-CN')
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, 'zh-CN')
            intent.putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, False)
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5)
            try:
                intent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE,
                                activity.getPackageName())
            except Exception:
                pass

            self._listening = True
            self._recognizer.startListening(intent)
        except Exception as e:
            self._listening = False
            self._recognizer = None
            self._fire_error('Java 异常：%s\n详情：%s' % (type(e).__name__, e))

    # ---------------- 桌面实现 ----------------
    def _start_desktop(self):
        try:
            import speech_recognition as sr
        except Exception as e:
            self._fire_error('未安装 speech_recognition，请使用键盘输入。')
            return

        self._sr_recognizer = sr.Recognizer()
        self._listening = True

        def worker():
            try:
                with sr.Microphone() as source:
                    self._fire_ready()
                    self._sr_recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = self._sr_recognizer.listen(source, timeout=8, phrase_time_limit=10)
                text = self._sr_recognizer.recognize_google(audio, language='zh-CN')
                self._listening = False
                self._fire_result(text)
            except sr.WaitTimeoutError:
                self._listening = False
                self._fire_error('没有听到语音，请重试。')
            except sr.UnknownValueError:
                self._listening = False
                self._fire_error('无法识别语音内容，请重新说一遍。')
            except sr.RequestError as e:
                self._listening = False
                self._fire_error('网络识别服务不可用：%s' % e)
            except Exception as e:
                self._listening = False
                self._fire_error('语音识别异常：%s' % e)

        threading.Thread(target=worker, daemon=True).start()


# ---------------- 便捷函数 ----------------
def recognize_simple(on_result, on_error=None):
    """简单的一次性识别"""
    r = VoiceRecognizer(on_result=on_result, on_error=on_error)
    r.start()
    return r


if __name__ == '__main__':
    # 桌面自测
    def show(text):
        print('识别结果:', text)

    def err(msg):
        print('错误:', msg)

    print('开始语音识别（请说话）...')
    rec = VoiceRecognizer(on_result=show, on_error=err)
    print('后端:', rec.backend())
    rec.start()
    import time
    time.sleep(12)
