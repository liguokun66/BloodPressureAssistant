# 血压记录助手（深色极简风）

一个支持 **语音 / 键盘** 录入的血压与脉搏记录工具。深蓝/深灰主背景、高对比文字，默认深色护眼模式（可切浅色）。数据默认仅保存在本机，不上传云端。

---

## 一、功能

| 模块 | 说明 |
| --- | --- |
| 底部四大标签 | 记录 / 分析 / 知识 / 我的，图标 + **加粗大字**标签 |
| 健康看板 | 超大字号并排展示最近一次 收缩压 / 舒张压 / 脉搏，**居中排列**，单位内嵌，与「最近测量」分隔 |
| 血压趋势 | 垂直**圆头**柱状图（柱体由低压延伸到高压），按状态着色；异常柱顶显示 偏低 / 偏高 / 高血压标签（正常不显示）；**默认按「日」显示当天**，**左右滑动**或点按切换 日 / 周 / 月 |
| 历史记录 | 卡片流：左侧状态色条 + 时间 / 脉搏 / 备注，**血压值居中靠右**，右侧编辑、删除图标（删除二次确认） |
| 快捷录入 | 底部醒目「＋ 添加记录」大按钮；**轻点**进入表单，**长按 0.55 秒**在当前页直接开始语音录入（显示“正在输入…”与**声波动画**）→ 弹确认后保存（不跳转页面）；时间默认当前，可在表单中修改 |
| 双模输入 | 语音说出「高压一百二，低压八十，脉搏七十二」自动解析填入；键盘可校正 |
| 智能防错 | 高压必须大于低压；超出正常区间实时**描边高亮**（黄=异常、红=高压≤低压），仍可强制保存 |
| 识别确认 | 语音识别后先弹出确认预览；表单内点「填入」，首页长按直录点「保存」 |
| 数据分析 | 折线趋势（高压 / 低压 / 脉搏）、平均值、健康状态分布；支持近 7 天 / 近 30 天 / **自定义范围** / 全部 |
| 科普知识库 | 6 篇血压科普，高饱和大圆角彩色卡片 + 矢量插画，点卡片看图文详情 |
| 设置与隐私 | 本地存储不上传云端、深色模式切换、导出 CSV（导出后可直接**分享到微信**）、本地备份、清空数据 |

---

## 二、界面与视觉规范

- **整体风格**：深蓝/深灰主背景（`#1E2233`），高对比文字，科技感与护眼感。
- **色彩语义**：蓝色用于主操作按钮与常规数据；明黄 / 红用于偏高、异常预警；状态色（偏低蓝、正常绿、正常高值黄、偏高橙、高血压红）贯穿看板、柱状图与记录卡片。
- **字体排版**：核心数据（高压 / 低压 / 脉搏）使用无衬线加粗数字，正文使用清晰黑体。
- **UI 细节**：数据卡片微投影 + 圆角；底部导航为简约扁平化图标。
- **图标**：底部导航、语音/编辑/删除等按钮使用 **Google Material Icons** 矢量图标字体（`assets/icons/MaterialIcons-Regular.ttf`，Apache 2.0），单色可跟随主题着色；不再使用 emoji（中文字体不含 emoji 字形，会渲染成空白/方框）。

---

## 三、目录结构

```
BloodPressureAssistant/
├── main.py            # 应用入口
├── screens.py         # 页面：记录 / 分析 / 知识 / 文章详情 / 我的 / 新增编辑
├── widgets.py         # 通用组件（卡片 / 按钮 / 图表 / 导航）
├── theme.py           # 配色与字体
├── icons.py           # 图标字体（Material Icons）封装
├── db.py              # SQLite 数据层
├── voice.py           # 语音识别（Android / 桌面）
├── voice_parser.py    # 语音文本解析（含中文数字）
├── share.py           # Android 文件分享（MediaStore + ACTION_SEND）
├── assets/            # 字体与图标（icons/ 为 Material Icons）
├── data/              # 本地数据库
├── buildozer.spec     # 安卓打包配置
├── extra_manifest.xml  # 注入 AndroidManifest（声明可查询语音识别服务）
└── requirements.txt   # 桌面端依赖
```

---

## 四、桌面端运行（先验证功能）

```bash
cd C:\Users\zitu\Desktop\BloodPressureAssistant
pip install -r requirements.txt
python main.py
```

> 语音输入在桌面端使用 `speech_recognition`（需联网 + 麦克风）。
> 如果 `PyAudio` 安装失败，可暂时只用键盘录入，或：
> `pip install pipwin && pipwin install pyaudio`

---

## 五、编译安卓 APK

Buildozer 官方仅支持 Linux，Windows 用户推荐两种方式。

### 方式 A：GitHub Actions 云编译（最简单，推荐）

1. 把本项目推送到 GitHub 仓库。
2. 已内置 `.github/workflows/build-apk.yml`。
3. 推送一个 tag（如 `v1.0`）或手动触发：
   - 打开仓库 **Actions** → **Build APK** → **Run workflow**。
4. 编译完成后，在 Actions 页面下载 `apk` 产物，解压得到 `bin/*.apk`，传到手机安装。

### 方式 B：WSL2 + Ubuntu 本地编译

```bash
# 在 WSL Ubuntu 中
sudo apt update
sudo apt install -y python3-pip python3-venv git zip unzip openjdk-17-jdk \
    autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
    libffi-dev libssl-dev

pip3 install --upgrade pip
pip3 install buildozer cython==0.29.36

cd /mnt/c/Users/zitu/Desktop/BloodPressureAssistant
buildozer android debug
```

编译产物在 `bin/` 目录，例如 `bin/bpassistant-1.0-arm64-v8a_armeabi-v7a-debug.apk`。

---

## 六、语音输入说明

- **Android**：调用系统 `SpeechRecognizer`，支持中文（zh-CN）。
- **支持的说法**：
  - 「高压120，低压80，脉搏70」
  - 「高压一百二，低压八十，脉搏七十二」
  - 「收缩压130，舒张压85，心率75」
- 识别完成后进入 **确认预览**；表单内点「填入」，首页长按直录点「保存」；识别失败会提示重新说一遍或改用键盘。

首次使用语音需在系统弹窗中允许 **麦克风权限**。

Android 11 及以上启用了「包可见性」过滤，若不声明 `<queries>`，
`SpeechRecognizer.isRecognitionAvailable()` 会误判为无识别服务。
项目通过 `extra_manifest.xml` 注入以下声明（见 `buildozer.spec` 的
`android.extra_manifest_xml`）：

```xml
<queries>
    <intent>
        <action android:name="android.speech.RecognitionService" />
    </intent>
</queries>
```

若仍然失败，应用会给出具体原因（无识别服务 / 无麦克风权限 / 创建失败），
可据此在系统设置中处理。

**桌面（Windows）**：需安装 `SpeechRecognition` 与 `PyAudio`（已随 `requirements.txt` 提供），识别走 Google 网页接口，需联网；麦克风不可用时会提示改用键盘。

**快捷方式**：在「记录」页 **长按「＋ 添加记录」** 直接在当前页开始聆听，说完弹确认 → 保存，全程不跳转页面（轻点按钮则进入完整表单）。

---

## 七、隐私

- 所有记录保存在本机 SQLite 数据库（`bp.db`）。
- 应用不会自动上传任何健康数据。
- 删除记录需二次确认；「清空数据」同样需要确认。

---

## 八、常见问题

**Q：中文显示成方框？**
A：把中文字体（如 `NotoSansSC-Regular.otf`）放入 `assets/` 目录即可，应用会自动加载。

**Q：APK 安装后语音没反应？**
A：先确认已授予麦克风权限。若提示「没有可用的语音识别服务」，说明该机型/ROM
没有可用的识别服务（常见于未装 Google 服务的机型），请改用键盘输入；
若提示其它具体错误，把提示文字发出来便于定位。

**Q：导出的 CSV 怎么发到微信？**
A：在「我的 → 导出 CSV 表格」点击后，系统分享面板会自动弹出，选择微信即可
（Android 10+ 会把文件写入「下载」目录再以系统分享发送；旧系统退化为文本分享）。

**Q：如何备份数据？**
A：在「我的 → 本地备份数据库」生成备份文件；或「导出 CSV」得到表格。
