# -*- coding: utf-8 -*-
"""语音识别模型管理

- 内置小模型：vosk-model-small-cn-0.22（随 APK 打包，离线可用，体积/内存友好）
- 高精度模型：vosk-model-cn-0.22（约 1.27 GB，需联网下载，识别准确率明显更高）

大模型由用户主动下载，存到 user_data_dir/vosk-model-large；
下载进度/结果通过回调抛给调用方（调用方负责转到 Kivy 主循环刷新界面）。
"""

import json
import os
import shutil
import threading
import time
import urllib.request
import zipfile

from kivy.logger import Logger

SMALL = {
    'key': 'small',
    'dir': 'vosk-model',
    'label': '内置小模型',
    'desc': '随安装包自带，离线可用',
}

LARGE = {
    'key': 'large',
    'dir': 'vosk-model-large',
    'url': 'https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip',
    'zip_name': 'vosk-model-cn-0.22.zip',
    'size': 1358736686,
    'label': '高精度模型',
    'desc': '中文识别准确率显著更高（约 1.27 GB，需 Wi-Fi 下载）',
}

PROBES = ('am/final.mdl', 'ivector/final.ie')


# ---------------- 路径 / 偏好 ----------------
def user_dir():
    try:
        from kivy.app import App
        app = App.get_running_app()
        d = getattr(app, 'user_data_dir', None)
        if d:
            return d
    except Exception:
        pass
    return os.getcwd()


def prefs_file():
    return os.path.join(user_dir(), 'model_prefs.json')


def load_prefs():
    try:
        with open(prefs_file(), 'r', encoding='utf-8') as f:
            d = json.load(f)
        if d.get('quality') in ('small', 'large'):
            return d
    except Exception:
        pass
    return {'quality': 'small'}


def save_prefs(d):
    try:
        with open(prefs_file(), 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
    except Exception as e:
        Logger.info('model_store: 保存偏好失败 %s' % e)


def quality():
    return load_prefs()['quality']


def set_quality(q):
    save_prefs({'quality': q})


def info(q=None):
    q = q or quality()
    return LARGE if q == 'large' else SMALL


def model_dir(q=None):
    """实际生效的模型目录：选了高精度但还没下载好时，自动用内置小模型。"""
    q = q or quality()
    if q == 'large' and large_ready():
        return os.path.join(user_dir(), LARGE['dir'])
    return os.path.join(user_dir(), SMALL['dir'])


def files_ok(d):
    if not d or not os.path.isdir(d):
        return False
    for probe in PROBES:
        if not os.path.exists(os.path.join(d, probe)):
            return False
    return True


def large_ready():
    return files_ok(model_dir('large'))


def current_ready():
    """当前所选模型是否可用"""
    return files_ok(model_dir())


def free_space(path):
    try:
        return shutil.disk_usage(path).free
    except Exception:
        return -1


# ---------------- 下载 ----------------
class ModelDownloader:
    """下载并解压高精度模型。

    用法：
        dl = ModelDownloader(on_progress=lambda r,t: ...,
                             on_done=lambda p: ...,
                             on_error=lambda m: ...)
        dl.start()      # 后台线程
        dl.cancel()     # 用户取消
    """

    def __init__(self, on_progress=None, on_done=None, on_error=None):
        self.on_progress = on_progress
        self.on_done = on_done
        self.on_error = on_error
        self._cancel = threading.Event()
        self._thread = None
        self._zip_path = os.path.join(user_dir(), '.model_dl',
                                      LARGE['zip_name'])
        self._dst = model_dir('large')

    # ---------- 对外 ----------
    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        self._cancel.set()

    @property
    def target(self):
        return self._dst

    # ---------- 内部 ----------
    def _emit(self, fn, *a):
        if fn is None:
            return
        try:
            fn(*a)
        except Exception as e:
            Logger.info('model_store: 回调异常 %s' % e)

    def _run(self):
        try:
            os.makedirs(os.path.dirname(self._zip_path), exist_ok=True)
            need = LARGE['size']
            free = free_space(user_dir())
            if 0 <= free < need * 2 + 512 * 1024 * 1024:
                raise RuntimeError(
                    '存储空间不足：下载并解压大约需要 %.1f GB 空闲空间。'
                    % ((need * 2.2) / (1024.0 ** 3)))
            self._download(self._zip_path, need)
            if self._cancel.is_set():
                raise RuntimeError('已取消')
            self._extract(self._zip_path, self._dst)
            if self._cancel.is_set():
                raise RuntimeError('已取消')
            self._cleanup()
            self._emit(self.on_done, self._dst)
        except Exception as e:
            Logger.info('model_store: 下载失败 %s' % e)
            self._cleanup_quiet()
            self._emit(self.on_error, str(e))

    def _download(self, path, total):
        req = urllib.request.Request(LARGE['url'], headers={
            'User-Agent': 'Mozilla/5.0 (Android) BloodPressureAssistant',
        })
        received = 0
        last = 0.0
        with urllib.request.urlopen(req, timeout=60) as resp, \
                open(path, 'wb') as f:
            while True:
                if self._cancel.is_set():
                    return
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)
                now = time.time()
                if now - last > 0.25:
                    last = now
                    self._emit(self.on_progress, received, total)
        if received <= 0:
            raise RuntimeError('下载为空，请检查网络后重试')
        self._emit(self.on_progress, received, total)

    def _extract(self, zip_path, dst):
        tmp = dst + '_tmp'
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp, exist_ok=True)
        with zipfile.ZipFile(zip_path) as z:
            names = [n for n in z.namelist() if not n.endswith('/')]
            # 压缩包根目录（例如 vosk-model-cn-0.22/）
            roots = set()
            for n in names:
                parts = n.split('/')
                if len(parts) > 1:
                    roots.add(parts[0])
            z.extractall(tmp)
        src = tmp
        if len(roots) == 1:
            src = os.path.join(tmp, list(roots)[0])
        shutil.rmtree(dst, ignore_errors=True)
        shutil.move(src, dst)
        shutil.rmtree(tmp, ignore_errors=True)
        if not files_ok(dst):
            raise RuntimeError('模型文件不完整，请删除后重新下载')

    def _cleanup(self):
        try:
            if os.path.isdir(os.path.dirname(self._zip_path)):
                shutil.rmtree(os.path.dirname(self._zip_path),
                              ignore_errors=True)
        except Exception:
            pass

    def _cleanup_quiet(self):
        try:
            if os.path.isfile(self._zip_path):
                os.remove(self._zip_path)
        except Exception:
            pass
