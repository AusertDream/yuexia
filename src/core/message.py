"""消息协议"""
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid
import time


class MessageType(str, Enum):
    # Face -> Brain
    USER_TEXT_INPUT = "user_text_input"
    # Brain -> Face
    LLM_STREAM_CHUNK = "llm_stream_chunk"
    LLM_STREAM_END = "llm_stream_end"
    # Brain -> Perception
    TTS_REQUEST = "tts_request"
    # Perception -> Face
    TTS_DONE = "tts_done"
    # Perception -> Brain
    ASR_RESULT = "asr_result"
    # Brain -> Face (显示 ASR 文字为用户气泡)
    ASR_TEXT_DISPLAY = "asr_text_display"
    # Action -> Brain
    SCREENSHOT = "screenshot"
    SCREENSHOT_MEMORY = "screenshot_memory"
    # Brain -> Action
    ACTION_REQUEST = "action_request"
    ACTION_RESULT = "action_result"
    # Brain -> Face (表情/动作)
    EXPRESSION_UPDATE = "expression_update"
    # 麦克风控制 Face <-> Perception
    MIC_START_RECORDING = "mic_start_recording"
    MIC_STOP_RECORDING = "mic_stop_recording"
    MIC_MODE_CHANGE = "mic_mode_change"
    MIC_TEST_REQUEST = "mic_test_request"
    MIC_TEST_RESULT = "mic_test_result"
    # 会话管理 Face <-> Brain
    SESSION_CREATE = "session_create"
    SESSION_SWITCH = "session_switch"
    SESSION_LIST_REQUEST = "session_list_request"
    SESSION_LIST = "session_list"
    SESSION_LOADED = "session_loaded"
    SESSION_RENAME = "session_rename"
    SESSION_DELETE = "session_delete"
    # 系统
    SHUTDOWN = "shutdown"
    HEARTBEAT = "heartbeat"
    CONFIG_RELOAD = "config_reload"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: MessageType
    source: str = ""
    target: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
