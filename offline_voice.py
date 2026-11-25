# -*- coding: utf-8 -*-
"""
离线语音识别模块（Vosk）
- Android：通过 pyjnius 调用 vosk-android（AAR，Maven Central）在本地离线识别
- 无需网络、无需系统 SpeechRecognizer；模型随 APK 打包（assets/vosk-model）
- 首次使用时把 assets 里的模型解压到 user_data_dir/vosk-model（之后复用）

⚠️ 线程约束（真机踩坑结论）：
  Android 的 JNI FindClass 在「非主线程」只能用系统类加载器，看不到应用
  自己的 dex，于是 autoclass('org.vosk.Model') 会抛 ClassNotFoundException。
  因此所有 Java 类的解析必须先在主（UI）线程完成一次；pyjnius 解析后会存进
  进程内 jclass_register，之后任意线程再 autoclass 都直接命中缓存。

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


def _selected_model_dir():
    """当前选择的模型目录：高精度（若已下载且被选中）或内置小模型。"""
    try:
        import model_store
        return model_store.model_dir()
    except Exception:
        pass
    try:
        from kivy.app import App
        app = App.get_running_app()
        base = getattr(app, 'user_data_dir', None) or os.path.dirname(
            os.path.abspath(__file__))
    except Exception:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, ASSET_MODEL_DIR)


def _run_on_ui(fn):
    """在 Android 主（UI）线程执行 fn；拿不到 activity 时在当前线程执行。"""
    try:
        from jnius import autoclass, PythonJavaClass, java_method
        activity = autoclass('org.kivy.android.PythonActivity').mActivity

        class _Task(PythonJavaClass):
            __javainterfaces__ = ['java/lang/Runnable']
            __javacontext__ = 'app'

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

    # 所有尚未释放完的实例：同一时刻只允许一个 AudioRecord 打开，
    # 否则第二次 startListening 可能抢不到麦克风（甚至触发 native 异常）
    _INFLIGHT = []

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
        self._primed = False
        self._shutting_down = False   # shutdown 幂等，防重复释放 native
        self._final_done = False      # 已收最终结果：onResult 不再重复上报
        self._seg_texts = []          # 本次会话已识别出的片段（端点检测会切段）
        VoskOfflineRecognizer._INFLIGHT.append(self)

    def _release_others(self):
        """把还没释放完的旧会话就地清掉（在 Kivy 主线程调用，同步完成）。"""
        for other in list(VoskOfflineRecognizer._INFLIGHT):
            if other is self or other._shutting_down:
                continue
            try:
                other.shutdown()
            except Exception:
                pass

    # ---------------- Java 类解析（必须在主线程） ----------------
    def _jc(self, attr, name):
        """取已缓存的 Java 类；没有则现解析（仅在主线程安全）。"""
        c = getattr(self, attr, None)
        if c is None:
            c = self._autoclass_safe(name)
            setattr(self, attr, c)
        return c

    def _prime_java_classes(self):
        """在主（UI）线程把所有会用到的 Java 类解析一遍并缓存。"""
        from jnius import autoclass  # noqa: F401
        self._jc('_ClsActivity', 'org.kivy.android.PythonActivity')
        self._jc('_ClsModel', 'org.vosk.Model')
        self._jc('_ClsRecognizer', 'org.vosk.Recognizer')
        self._jc('_ClsSpeechService', 'org.vosk.android.SpeechService')
        self._primed = True

    def _run_on_ui_blocking(self, fn, timeout=15.0):
        """把 fn 丢到 Android 主线程执行并等结果；失败时把异常抛回调用方。

        Activity.runOnUiThread 在「当前线程就是 UI 线程」时会立即内联执行，
        所以从 Kivy 主循环调用不会死锁。
        """
        box = {}
        done = threading.Event()

        def task():
            try:
                box['r'] = fn()
            except Exception as e:  # noqa: BLE001
                box['e'] = e
            finally:
                done.set()

        _run_on_ui(task)
        if not done.wait(timeout):
            raise RuntimeError('主线程任务超时')
        if 'e' in box:
            raise box['e']
        return box.get('r')

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
        return _selected_model_dir()

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
        """确保所选模型存在且完整；返回 Model 或抛异常。"""
        d = self.model_dir()
        if not self._model_files_ok(d):
            # 只有内置小模型可以从 assets 解压；高精度模型需先下载
            if os.path.basename(d) != ASSET_MODEL_DIR:
                raise RuntimeError('HIGH_MODEL_MISSING')
            self._copy_assets(d)
        Model = self._jc('_ClsModel', 'org.vosk.Model')
        return Model(d)

    @staticmethod
    def _autoclass_safe(name):
        from jnius import autoclass
        return autoclass(name)

    def _copy_assets(self, dst_dir):
        """把 assets/vosk-model 整棵目录树复制到 dst_dir。"""
        PythonActivity = self._jc('_ClsActivity',
                                  'org.kivy.android.PythonActivity')
        ctx = PythonActivity.mActivity
        if ctx is None:
            raise RuntimeError('无法获取应用上下文')
        am = ctx.getAssets()

        def copy_dir(asset_path, out_dir):
            names = am.list(asset_path)
            if names is None:
                names = []
            else:
                try:
                    names = [names[i] for i in range(len(names))]
                except Exception:
                    names = list(names)
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
        self._release_others()
        if not self.supported():
            self._fire_error('设备不支持离线语音引擎。')
            return
        self._preparing = True
        kbdbg.KB['eng'] = 'vosk'
        kbdbg.KB['vk'] = 'prepare'
        # 关键：Java 类必须在主线程解析（子线程 FindClass 看不到应用 dex）
        try:
            self._run_on_ui_blocking(self._prime_java_classes)
        except Exception as e:
            Logger.info('vosk: Java 类准备失败 %s（%s）\n%s'
                        % (type(e).__name__, e,
                           __import__('traceback').format_exc()))
            self._failed = True
            self._preparing = False
            kbdbg.KB['vk'] = 'err:prime:%s' % type(e).__name__
            self._fire_error('OFFLINE_MODEL_FAIL:%s:%s'
                             % (type(e).__name__, e))
            return
        threading.Thread(target=self._prepare_worker, daemon=True).start()

    def _prepare_worker(self):
        try:
            d = self.model_dir()
            if not self._model_files_ok(d):
                kbdbg.KB['vk'] = 'unpack'
                self._copy_assets(d)
            kbdbg.KB['vk'] = 'model'
            model = self._ensure_model()
            kbdbg.KB['vk'] = 'model_ok'
        except Exception as e:
            Logger.info('vosk: 模型准备失败 %s（%s）\n%s'
                        % (type(e).__name__, e,
                           __import__('traceback').format_exc()))
            self._failed = True
            self._preparing = False
            kbdbg.KB['vk'] = 'err:%s' % type(e).__name__
            self._fire_error('OFFLINE_MODEL_FAIL:%s:%s'
                             % (type(e).__name__, e))
            return
        # 创建 Recognizer / SpeechService 需要在主 Looper 线程
        self._post(self._start_ui, model)

    def _start_ui(self, model):
        try:
            kbdbg.KB['vk'] = 'recognizer'
            Recognizer = self._jc('_ClsRecognizer', 'org.vosk.Recognizer')
            SpeechService = self._jc('_ClsSpeechService',
                                     'org.vosk.android.SpeechService')
            self._recognizer = Recognizer(model, SAMPLE_RATE)
            self._configure_recognizer(self._recognizer)
            kbdbg.KB['vk'] = 'service'
            self._service = SpeechService(self._recognizer, SAMPLE_RATE)
            kbdbg.KB['vk'] = 'listen'
            self._listener = _VoskListener(self)
            ok = bool(self._service.startListening(self._listener))
            if not ok:
                raise RuntimeError('startListening 返回 false')
            self._preparing = False
            self._started = True
            kbdbg.KB['vk'] = 'done'
            self._fire_ready()
        except Exception as e:
            Logger.info('vosk: 启动失败 %s（%s）\n%s'
                        % (type(e).__name__, e,
                           __import__('traceback').format_exc()))
            self._failed = True
            self._preparing = False
            kbdbg.KB['vk'] = 'err:%s' % type(e).__name__
            self._cleanup_java()
            self._fire_error('OFFLINE_START_FAIL:%s:%s'
                             % (type(e).__name__, e))

    def _configure_recognizer(self, rec):
        """解码器调优：默认端点检测约 1s 没说话就把句子截断，导致「高压…低压…」
        这类长句被切成几段、只剩最后一段。调成 LONG 让它等更久；
        我们本身是按住说话（松手才停），所以拉长不会带来副作用。
        """
        try:
            rec.setEndpointerMode(2)   # 0=DEFAULT 1=SHORT 2=LONG 3=VERY_LONG
        except Exception as e:
            Logger.info('vosk: setEndpointerMode 失败 %s' % e)
        try:
            rec.setWords(True)         # 输出词级结果，便于后续利用
        except Exception as e:
            Logger.info('vosk: setWords 失败 %s' % e)

    def stop(self):
        """松手结束：取最终识别结果（onFinalResult 回调）。"""
        service, self._service = self._service, None
        self._started = False
        if service is None:
            return
        _run_on_ui(lambda: service.stop())

    def cancel(self):
        """取消本次识别（不停模型），回 final；空文本不算错误。"""
        service, self._service = self._service, None
        self._started = False
        if service is not None:
            _run_on_ui(service.cancel)

    def shutdown(self):
        """彻底释放资源；多次调用安全。

        顺序重要：先停掉 Vosk 的识别线程（内部会 join），再释放 native
        recognizer，最后释放 AudioRecord。反过来做（边收音频边 free）是
        真机偶发闪退的典型成因。
        """
        if (self._shutting_down and self._service is None
                and self._recognizer is None):
            return
        self._shutting_down = True
        service, self._service = self._service, None
        rec, self._recognizer = self._recognizer, None
        self._started = False
        if rec is None and service is None:
            return

        def task():
            try:
                if service is not None:
                    service.stop()        # interrupt + join 工作线程
            except Exception:
                pass
            try:
                if rec is not None:
                    rec.close()
            except Exception:
                pass
            try:
                if service is not None:
                    service.shutdown()    # 释放 AudioRecord
            except Exception:
                pass
            try:
                if self in VoskOfflineRecognizer._INFLIGHT:
                    VoskOfflineRecognizer._INFLIGHT.remove(self)
            except Exception:
                pass
        _run_on_ui(task)

    def _cleanup_java(self):
        """异常路径的统一释放入口（异步、与 shutdown 同序）"""
        self.shutdown()

    def _defer_shutdown(self, delay=0.35):
        """把释放动作挪出 Vosk 的 Java 回调线程。

        onFinalResult/onError/onTimeout 都运行在 Vosk 自己的工作线程里，
        在那里原地 close()/shutdown() 会在回调线程内 join/释放 native，
        真机上偶发 SIGSEGV 闪退。延迟到 Kivy 主循环再释放即可避开。
        """
        if self._shutting_down:
            return
        self._shutting_down = True
        try:
            Clock.schedule_once(lambda dt: self._safe_shutdown(), delay)
        except Exception:
            self._safe_shutdown()

    def _safe_shutdown(self):
        try:
            self.shutdown()
        except Exception:
            Logger.info('vosk: shutdown 异常\n%s'
                        % __import__('traceback').format_exc())

    def _cleanup_java(self):
        """异常路径的统一释放入口（异步、与 shutdown 同序）"""
        self.shutdown()

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

    @staticmethod
    def _merge_segments(segments):
        """拼接多个识别片段，去掉完全重复 / 已被包含的段。"""
        out = []
        for seg in segments:
            seg = (seg or '').strip()
            if not seg:
                continue
            if out and (seg == out[-1] or out[-1].endswith(seg)):
                continue
            out.append(seg)
        return ''.join(out)

    def on_result(self, hypothesis):
        """一段（utterance）结束：Vosk 会在每次静音后回调。这里只做累积，
        不当作最终结果，避免一句长句被切成几段后只保留最后一段。"""
        if self._final_done:
            return
        text = self._extract_text(hypothesis, 'text')
        if text:
            self._seg_texts.append(text)
            self._fire_partial(self._merge_segments(self._seg_texts))

    def on_final(self, hypothesis):
        """识别结束：把所有片段拼成完整句子再上报一次。"""
        self._final_done = True
        self._started = False
        text = self._extract_text(hypothesis, 'text')
        if text:
            self._seg_texts.append(text)
        merged = self._merge_segments(self._seg_texts)
        self._seg_texts = []
        if merged:
            self._fire_result(merged)
        else:
            self._fire_error('没有听到清晰语音，请按住按钮重说。')
        self._defer_shutdown()

    def on_error(self, exc):
        self._final_done = True
        self._started = False
        msg = ''
        try:
            msg = exc.getMessage() if hasattr(exc, 'getMessage') else str(exc)
        except Exception:
            msg = str(exc)
        self._fire_error('离线识别出错：%s' % (msg or type(exc).__name__))
        self._defer_shutdown()

    def on_timeout(self):
        self._final_done = True
        self._started = False
        self._fire_error('说话超时，请重试。')
        self._defer_shutdown()


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
    # 关键：org.vosk.* 在应用 dex 里，系统类加载器看不到；必须用当前线程的
    # ContextClassLoader（app 加载器）来建动态代理。
    __javacontext__ = 'app'

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
