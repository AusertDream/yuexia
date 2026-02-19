"""设置页面 - Fluent Design"""
from __future__ import annotations
from pathlib import Path
import yaml
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PySide6.QtCore import Qt, Signal
from qfluentwidgets import (
    GroupHeaderCardWidget, SwitchButton, SpinBox, DoubleSpinBox,
    ComboBox, LineEdit, PushButton, FluentIcon, SmoothScrollArea,
    ProgressBar,
)

_ENUMS = {
    "brain.engine": ["transformers", "vllm"],
    "perception.asr.mic_mode": ["always_on", "push_to_talk"],
    "action.screen.mode": ["screenshot", "video_stream"],
}
_PATH_KEYS = {"model_path", "db_path", "system_prompt_path", "output_dir",
              "emotion_refs_dir"}
_SECTION_ICONS = {
    "brain": FluentIcon.ROBOT,
    "perception": FluentIcon.MICROPHONE,
    "action": FluentIcon.FULL_SCREEN,
    "face": FluentIcon.EMOJI_TAB_SYMBOLS,
}

# 中英文翻译
_I18N = {
    # 分区标题
    "brain":       {"zh": "大脑", "en": "Brain"},
    "perception":  {"zh": "感知", "en": "Perception"},
    "action":      {"zh": "动作", "en": "Action"},
    "face":        {"zh": "界面", "en": "Face"},
    "memory":      {"zh": "记忆", "en": "Memory"},
    "diary":       {"zh": "日记", "en": "Diary"},
    # 字段
    "ai_name":     {"zh": "AI 名称", "en": "AI Name"},
    "model_path":  {"zh": "模型路径", "en": "Model Path"},
    "engine":      {"zh": "推理引擎", "en": "Engine"},
    "gpu_memory_utilization": {"zh": "显存占用率", "en": "GPU Memory"},
    "max_model_len": {"zh": "最大长度", "en": "Max Length"},
    "enable_thinking": {"zh": "启用思考链", "en": "Enable Thinking"},
    "system_prompt_path": {"zh": "系统提示词路径", "en": "System Prompt Path"},
    "db_path":     {"zh": "数据库路径", "en": "DB Path"},
    "device":      {"zh": "设备", "en": "Device"},
    "compute_type": {"zh": "计算精度", "en": "Compute Type"},
    "vad_threshold": {"zh": "VAD 阈值", "en": "VAD Threshold"},
    "mic_mode":    {"zh": "麦克风模式", "en": "Mic Mode"},
    "mic_device":  {"zh": "麦克风设备", "en": "Mic Device"},
    "ptt_key":     {"zh": "按键说话快捷键", "en": "PTT Key"},
    "emotion_refs_dir": {"zh": "情感参考目录", "en": "Emotion Refs Dir"},
    "output_dir":  {"zh": "输出目录", "en": "Output Dir"},
    "width":       {"zh": "宽度", "en": "Width"},
    "height":      {"zh": "高度", "en": "Height"},
    "always_on_top": {"zh": "置顶", "en": "Always On Top"},
    "transparent": {"zh": "透明", "en": "Transparent"},
    "mode":        {"zh": "模式", "en": "Mode"},
    "interval":    {"zh": "间隔(秒)", "en": "Interval(s)"},
    "fps":         {"zh": "帧率", "en": "FPS"},
    "headless":    {"zh": "无头模式", "en": "Headless"},
}


class SettingsPage(QWidget):
    mic_test_requested = Signal()
    config_saved = Signal()

    def __init__(self, config_path: str = "config.yaml"):
        super().__init__()
        self._path = Path(config_path)
        self._widgets: dict[str, QWidget] = {}
        self._lang = "zh"
        self._mic_thread = None
        self._setup_ui()
        self._load()

    def _tr(self, key: str) -> str:
        return _I18N.get(key, {}).get(self._lang, key)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        # 顶部：语言切换
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        self._lang_btn = PushButton("EN")
        self._lang_btn.setFixedWidth(50)
        self._lang_btn.clicked.connect(self._toggle_lang)
        top_bar.addWidget(self._lang_btn)
        outer.addLayout(top_bar)

        # 滚动区域
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        container.setObjectName("settingsContainer")
        container.setStyleSheet("#settingsContainer{background:transparent}")
        self._form_layout = QVBoxLayout(container)
        self._form_layout.setSpacing(12)
        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

        # 麦克风测试区
        self._mic_card = GroupHeaderCardWidget()
        self._mic_card.setTitle(self._tr("perception"))
        self._mic_card.setBorderRadius(8)
        self._mic_bar = ProgressBar()
        self._mic_bar.setRange(0, 100)
        self._mic_bar.setValue(0)
        self._mic_bar.setMinimumWidth(200)
        self._mic_toggle = PushButton(FluentIcon.MICROPHONE, "开始测试")
        self._mic_toggle.setFixedWidth(140)
        self._mic_toggle.clicked.connect(self._toggle_mic_test)
        mic_row = QWidget()
        mic_row.setStyleSheet("background:transparent")
        mh = QHBoxLayout(mic_row)
        mh.setContentsMargins(0, 0, 0, 0)
        mh.addWidget(self._mic_bar, stretch=1)
        mh.addWidget(self._mic_toggle)
        self._mic_card.addGroup(FluentIcon.MICROPHONE, "麦克风测试",
                                "实时检测麦克风音量", mic_row)
        outer.addWidget(self._mic_card)

        # 底部按钮
        btn_bar = QHBoxLayout()
        save_btn = PushButton(FluentIcon.SAVE, "保存配置")
        save_btn.clicked.connect(self._save)
        btn_bar.addWidget(save_btn)
        outer.addLayout(btn_bar)

    def _load(self):
        if not self._path.exists():
            return
        data = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        while self._form_layout.count():
            item = self._form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._widgets.clear()

        for section, values in data.items():
            if not isinstance(values, dict):
                continue
            icon = _SECTION_ICONS.get(section, FluentIcon.SETTING)
            card = GroupHeaderCardWidget()
            card.setTitle(self._tr(section))
            card.setBorderRadius(8)
            self._add_fields(card, values, prefix=section, icon=icon)
            self._form_layout.addWidget(card)
        self._form_layout.addStretch()

    def _add_fields(self, card: GroupHeaderCardWidget, d: dict,
                    prefix: str, icon):
        for key, val in d.items():
            full_key = f"{prefix}.{key}"
            if isinstance(val, dict):
                for k2, v2 in val.items():
                    self._add_single(card, f"{full_key}.{k2}", k2, v2, icon)
            else:
                self._add_single(card, full_key, key, val, icon)

    def _add_single(self, card: GroupHeaderCardWidget, full_key: str,
                    label: str, val, icon):
        # 麦克风设备：下拉列表
        if full_key == "perception.asr.mic_device":
            w = self._make_mic_device_widget(val)
            self._widgets[full_key] = w
            card.addGroup(icon, self._tr(label), full_key.replace(".", " > "), w)
            return
        if full_key in _ENUMS:
            w = ComboBox()
            w.addItems(_ENUMS[full_key])
            if val is not None:
                idx = w.findText(str(val))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            w.setMinimumWidth(160)
        elif isinstance(val, bool):
            w = SwitchButton()
            w.setChecked(val)
        elif isinstance(val, int):
            w = SpinBox()
            w.setRange(0, 999999)
            w.setValue(val)
            w.setMinimumWidth(120)
        elif isinstance(val, float):
            w = DoubleSpinBox()
            w.setRange(0, 999999)
            w.setDecimals(3)
            w.setValue(val)
            w.setMinimumWidth(120)
        elif isinstance(val, str) and label.split(".")[-1] in _PATH_KEYS:
            w = self._make_path_widget(val)
        elif val is None:
            w = LineEdit()
            w.setPlaceholderText("null")
            w.setMinimumWidth(200)
        else:
            w = LineEdit()
            if val is not None:
                w.setText(str(val))
            w.setMinimumWidth(200)

        self._widgets[full_key] = w
        display = self._tr(label)
        desc = full_key.replace(".", " > ")
        card.addGroup(icon, display, desc, w)

    def _make_path_widget(self, val: str) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background:transparent")
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        le = LineEdit()
        le.setText(val)
        le.setMinimumWidth(180)
        h.addWidget(le)
        btn = PushButton("...")
        btn.setFixedWidth(36)
        btn.clicked.connect(lambda: self._browse(le))
        h.addWidget(btn)
        container._line_edit = le  # type: ignore
        return container

    def _make_mic_device_widget(self, current_val) -> ComboBox:
        import sounddevice as sd
        w = ComboBox()
        w.addItem("默认设备")
        devices = sd.query_devices()
        self._mic_device_indices = [None]
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                w.addItem(d["name"])
                self._mic_device_indices.append(i)
        # 选中当前值
        if current_val is not None:
            try:
                idx = self._mic_device_indices.index(int(current_val))
                w.setCurrentIndex(idx)
            except (ValueError, TypeError):
                pass
        w.setMinimumWidth(200)
        return w

    def _browse(self, le: LineEdit):
        path = QFileDialog.getExistingDirectory(self, "选择路径", le.text())
        if path:
            le.setText(path)

    def _collect(self) -> dict:
        if not self._path.exists():
            return {}
        data = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        for full_key, w in self._widgets.items():
            parts = full_key.split(".")
            node = data
            for p in parts[:-1]:
                if p not in node or not isinstance(node[p], dict):
                    node[p] = {}
                node = node[p]
            if full_key == "perception.asr.mic_device" and hasattr(self, '_mic_device_indices'):
                idx = w.currentIndex()
                node[parts[-1]] = self._mic_device_indices[idx] if idx < len(self._mic_device_indices) else None
            else:
                node[parts[-1]] = self._get_value(w, node.get(parts[-1]))
        return data

    def _get_value(self, w, original):
        if isinstance(w, SwitchButton):
            return w.isChecked()
        if isinstance(w, SpinBox):
            return w.value()
        if isinstance(w, DoubleSpinBox):
            return w.value()
        if isinstance(w, ComboBox):
            return w.currentText()
        if isinstance(w, LineEdit):
            t = w.text().strip()
            return None if t == "" else t
        if hasattr(w, '_line_edit'):
            t = w._line_edit.text().strip()
            return None if t == "" else t
        return original

    def _save(self):
        data = self._collect()
        self._path.write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False,
                      sort_keys=False),
            encoding="utf-8",
        )
        self.config_saved.emit()

    def _toggle_lang(self):
        self._lang = "en" if self._lang == "zh" else "zh"
        self._lang_btn.setText("中文" if self._lang == "en" else "EN")
        self._mic_card.setTitle(self._tr("perception"))
        self._load()

    def _toggle_mic_test(self):
        if self._mic_thread and self._mic_thread.isRunning():
            self._mic_thread.stop()
            self._mic_thread = None
            self._mic_bar.setValue(0)
            self._mic_toggle.setText("开始测试" if self._lang == "zh" else "Start")
            return
        from src.face.mic_level_thread import MicLevelThread
        self._mic_thread = MicLevelThread(parent=self)
        self._mic_thread.level_changed.connect(self._mic_bar.setValue)
        self._mic_thread.start()
        self._mic_toggle.setText("停止测试" if self._lang == "zh" else "Stop")

    def cleanup(self):
        if self._mic_thread and self._mic_thread.isRunning():
            self._mic_thread.stop()
