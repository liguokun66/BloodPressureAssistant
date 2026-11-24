# -*- coding: utf-8 -*-
"""
离线语音识别模块（Vosk）
- Android：通过 pyjnius 调用 vosk-android（AAR，Maven Central）在本地离线识别
- 无需网络、无需系统 SpeechRecognizer；模型随 APK 打包（assets/vosk-model）
- 首次使用时把 assets 里的模型解压到 user_data_dir/vosk-model（之后复用）

对外接口与 voice.VoiceRecognizer 保持一致：
    VoskOfflineRecognizer(on_result, on_partial, on_error, on_ready)
    .start() / .stop() / .cancel() / .busy()
"""

import os
import json
import threading

from kivy.logger import Logger
from kivy.clock import Clock

import kbdbg

# assets 里的模型目录（与 buildozer.spec 的 android.add_assets 对应）
ASSET_MODEL_DIR = 'vosk-model'
SAMPLE_RATE = 16000.0


def _run_on_ui(fn):
    """在 Android 主（UI）线程执行 fn；拿不到 activity 时在当前线程执行。"""
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
                    Logger.info('vosk: ui task failed\n%s'
                                % __import__('traceback').format_exc())

        if activity is not None:
            activity.runOnUiThread(_Task(fn))
        else:
            fn()
    except Exception:
        fn()


class VoskOfflineRecognizer:
    """Vosk 离线识别封装（仅 Android）。"""

    def __init__(self, on_result=None, on_partial=None, on_error=None,
                 on_ready=None):
        self._on_result = on_result
        self._on_partial = on_partial
        self._on_error = on_error
        self._on_ready = on_ready
        self._model = None          # org.vosk.Model
        self._recognizer = None     # org.vosk.Recognizer
        self._service = None        # org.vosk.android.SpeechService
        self._listener = None       # RecognitionListener 实现
        self._preparing = False
        self._started = False
        self._failed = False

    # ---------------- 状态查询 ----------------
    @staticmethod
    def supported():
        try:
            import jnius  # noqa
            return True
        except Exception:
            return False

    def busy(self):
        return self._preparing or self._started

    @staticmethod
    def model_dir():
        try:
            from kivy.app import App
            app = App.get_running_app()
            base = getattr(app, 'user_data_dir', None) or os.path.dirname(
                os.path.abspath(__file__))
        except Exception:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, 'vosk-model')

    @staticmethod
    def _model_files_ok(d):
        for probe in ('am/final.mdl', 'conf/model.conf', 'conf/mfcc.conf'):
            if not os.path.exists(os.path.join(d, probe)):
                return False
        return True

    # ---------------- 事件派发（回 Kivy 主循环） ----------------
    def _post(self, fn, *args):
        try:
            Clock.schedule_once(lambda dt: fn(*args), 0)
        except Exception:
            try:
                fn(*args)
            except Exception:
                pass

    def _fire_result(self, text):
        if self._on_result:
            self._post(self._on_result, text)

    def _fire_partial(self, text):
        if self._on_partial and text:
            self._post(self._on_partial, text)

    def _fire_error(self, msg):
        if self._on_error:
            self._post(self._on_error, msg)

    def _fire_ready(self):
        if self._on_ready:
            self._post(self._on_ready)

    # ---------------- 模型准备 ----------------
    def _ensure_model(self):
        """确保 user_data_dir/vosk-model 存在且完整；返回 Model 或抛异常。"""
        d = self.model_dir()
        if not self._model_files_ok(d):
            self._copy_assets(d)
        Model = _autoclass_safe('org.vosk.Model')
        return Model(d)

    @staticmethod
    def _autoclass_safe(name):
        from jnius import autoclass
        return autoclass(name)

    def _copy_assets(self, dst_dir):
        """把 assets/vosk-model 整棵目录树复制到 dst_dir。"""
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        ctx = PythonActivity.mActivity
        if ctx is None:
            raise RuntimeError('无法获取应用上下文')
        am = ctx.getAssets()

        def copy_dir(asset_path, out_dir):
            names = am.list(asset_path)
            names = list(names) if names is not None else []
            if not names:
                # 叶子：文件
                os.makedirs(os.path.dirname(out_dir), exist_ok=True)
                ins = am.open(asset_path)
                try:
                    with open(out_dir, 'wb') as f:
                        buf = bytearray(65536)
                        while True:
                            n = ins.read(buf)
                            if n is None or n <= 0:
                                break
                            f.write(bytes(buf[:n]))
                finally:
                    try:
                        ins.close()
                    except Exception:
                        pass
                return
            os.makedirs(out_dir, exist_ok=True)
            for name in names:
                copy_dir('%s/%s' % (asset_path, name),
                         os.path.join(out_dir, name))

        copy_dir(ASSET_MODEL_DIR, dst_dir)

    # ---------------- 生命周期 ----------------
    def start(self):
        if self.busy():
            return
        if not self.supported():
            self._fire_error('设备不支持离线语音引擎。')
            return
        self._preparing = True
        kbdbg.KB['eng'] = 'vosk'
        threading.Thread(target=self._prepare_worker, daemon=True).start()

    def _prepare_worker(self):
        try:
            model = self._ensure_model()
        except Exception as e:
            Logger.info('vosk: 模型准备失败 %s（%s）'
                        % (type(e).__name__, e))
            self._failed = True
            self._preparing = False
            self._fire_error('OFFLINE_MODEL_FAIL:%s（%s）'
                             % (type(e).__name__, e))
            return
        # 创建 Recognizer / SpeechService 需要在主 Looper 线程
        self._post(self._start_ui, model)

    def _start_ui(self, model):
        try:
            Recognizer = self._autoclass_safe('org.vosk.Recognizer')
            SpeechService = self._autoclass_safe(
                'org.vosk.android.SpeechService')
            self._recognizer = Recognizer(model, SAMPLE_RATE)
            self._service = SpeechService(self._recognizer, SAMPLE_RATE)
            self._listener = _VoskListener(self)
            ok = bool(self._service.startListening(self._listener))
            if not ok:
                raise RuntimeError('startListening 返回 false')
            self._preparing = False
            self._started = True
            self._fire_ready()
        except Exception as e:
            Logger.info('vosk: 启动失败 %s（%s）' % (type(e).__name__, e))
            self._failed = True
            self._preparing = False
            self._cleanup_java()
            self._fire_error('OFFLINE_START_FAIL:%s（%s）'
                             % (type(e).__name__, e))

    def stop(self):
        """松手结束：取最终识别结果（onFinalResult 回调）。"""
        service, self._service = self._service, None
        self._started = False
        if service is None:
            return
        _run_on_ui(lambda: service.stop())

    def cancel(self):
        service, self._service = self._service, None
        self._started = False
        if service is not None:
            _run_on_ui(service.cancel)

    def shutdown(self):
        service, self._service = self._service, None
        rec, self._recognizer = self._recognizer, None
        self._started = False
        if rec is not None:
            _run_on_ui(rec.close)
        if service is not None:
            _run_on_ui(service.shutdown)

    def _cleanup_java(self):
        rec, self._recognizer = self._recognizer, None
        svc, self._service = self._service, None
        if rec is not None:
            try:
                rec.close()
            except Exception:
                pass
        if svc is not None:
            try:
                svc.shutdown()
            except Exception:
                pass

    # ---------------- 结果解析 ----------------
    @staticmethod
    def _extract_text(hypothesis, key):
        try:
            obj = json.loads(hypothesis)
        except Exception:
            return ''
        if isinstance(obj, dict):
            val = obj.get(key, '')
            return val if isinstance(val, str) else ''
        return ''

    # ---------------- 回调入口（由 _VoskListener 调用） ----------------
    def on_partial(self, hypothesis):
        text = self._extract_text(hypothesis, 'partial')
        if text:
            self._fire_partial(text)

    def on_result(self, hypothesis):
        text = self._extract_text(hypothesis, 'text')
        if text:
            self._fire_result(text)

    def on_final(self, hypothesis):
        self._started = False
        text = self._extract_text(hypothesis, 'text')
        if text:
            self._fire_result(text)
        else:
            self._fire_error('没有听到清晰语音，请按住按钮重说。')
        self.shutdown()

    def on_error(self, exc):
        self._started = False
        msg = ''
        try:
            msg = exc.getMessage() if hasattr(exc, 'getMessage') else str(exc)
        except Exception:
            msg = str(exc)
        self._fire_error('离线识别出错：%s' % (msg or type(exc).__name__))
        self.shutdown()

    def on_timeout(self):
        self._started = False
        self._fire_error('说话超时，请重试。')


# ---------------- RecognitionListener 的 Python 实现 ----------------
try:
    from jnius import PythonJavaClass, java_method
except Exception:  # 桌面环境没有 pyjnius，仅占位
    PythonJavaClass = object

    def java_method(*a, **kw):
        def deco(fn):
            return fn
        return deco


class _VoskListener(PythonJavaClass):
    """org.vosk.android.RecognitionListener 的 PythonJavaClass 实现。"""
    __javainterfaces__ = ('org/vosk/android/RecognitionListener',)

    def __init__(self, owner):
        super().__init__()
        self._owner = owner

    @java_method('(Ljava/lang/String;)V')
    def onPartialResult(self, hypothesis):
        try:
            self._owner.on_partial(hypothesis)
        except Exception as e:
            Logger.info('vosk: partial 回调异常 %s' % e)

    @java_method('(Ljava/lang/String;)V')
    def onResult(self, hypothesis):
        try:
            self._owner.on_result(hypothesis)
        except Exception as e:
            Logger.info('vosk: result 回调异常 %s' % e)

    @java_method('(Ljava/lang/String;)V')
    def onFinalResult(self, hypothesis):
        try:
            self._owner.on_final(hypothesis)
        except Exception as e:
            Logger.info('vosk: final 回调异常 %s' % e)

    @java_method('(Ljava/lang/Exception;)V')
    def onError(self, exc):
        try:
            self._owner.on_error(exc)
        except Exception as e:
            Logger.info('vosk: error 回调异常 %s' % e)

    @java_method('()V')
    def onTimeout(self):
        try:
            self._owner.on_timeout()
        except Exception as e:
            Logger.info('vosk: timeout 回调异常 %s' % e)
