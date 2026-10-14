# Pydantic v2 Schema（PRD 8.5 / 12.2：orm_mode 已改为 from_attributes）
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# CEFR 难度等级：A1/A2/B1/B2（原 1-5 数字难度，已按需求改为欧洲语言共同参考框架等级）
CEFR_LEVELS = ("A1", "A2", "B1", "B2")
CefrLevel = Literal["A1", "A2", "B1", "B2"]


# ---------- 认证 ----------
class WxLoginRequest(BaseModel):
    code: str = Field(..., min_length=1, description="wx.login 临时凭证")


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str | None = None
    avatar_url: str | None = None
    role: str
    current_level: str | None = None
    sensitive_opt_in: bool


class WxLoginResponse(BaseModel):
    token: str
    user: UserPublic
    is_new_user: bool


# ---------- 闪卡 ----------
class FlashcardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lesson_id: int | None = None
    front_text: str
    back_text: str
    front_audio_url: str | None = None
    example_sentence: str | None = None
    example_translation: str | None = None
    difficulty: CefrLevel
    tags: list = []
    is_sensitive: bool = False
    tip: str | None = None


class FlashcardPage(BaseModel):
    items: list[FlashcardOut]
    total: int
    page: int
    page_size: int


class FlashcardProgressIn(BaseModel):
    flashcard_id: int
    result: str = Field(..., pattern="^(correct|wrong|skip)$")
    response_time_ms: int | None = None
    lesson_id: int | None = None


class FlashcardProgressOut(BaseModel):
    status: str
    next_review_date: str | None = None
    correct_count: int
    wrong_count: int


# ---------- 用户 ----------
class SensitiveOptInRequest(BaseModel):
    sensitive_opt_in: bool


class ReminderUpdateRequest(BaseModel):
    reminder_enabled: bool | None = None
    reminder_time: str | None = None
    reminder_days: list[int] | None = None
    daily_goal: int | None = Field(None, ge=5, le=100)


# ---------- 后台：认证 ----------
class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


# ---------- 后台：闪卡 ----------
class AdminFlashcardCreate(BaseModel):
    lesson_id: int | None = None
    front_text: str = Field(..., min_length=1)
    back_text: str = Field(..., min_length=1)
    example_sentence: str | None = None
    example_translation: str | None = None
    tip: str | None = None
    difficulty: CefrLevel = "A1"
    tags: list[str] = []
    is_sensitive: bool = False
    status: str = Field("published", pattern="^(draft|published|archived)$")
    sort_order: int = 0


class AdminFlashcardUpdate(BaseModel):
    lesson_id: int | None = None
    front_text: str | None = Field(None, min_length=1)
    back_text: str | None = Field(None, min_length=1)
    example_sentence: str | None = None
    example_translation: str | None = None
    tip: str | None = None
    difficulty: CefrLevel | None = None
    tags: list[str] | None = None
    is_sensitive: bool | None = None
    status: str | None = Field(None, pattern="^(draft|published|archived)$")
    sort_order: int | None = None


class AdminFlashcardBatch(BaseModel):
    items: list[AdminFlashcardCreate] = Field(..., min_length=1, max_length=200)


# ---------- 后台：课时 ----------
class AdminLessonCreate(BaseModel):
    level_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    lesson_type: str = Field("vocabulary", pattern="^(vocabulary|phrase|dialogue|culture)$")
    sort_order: int = 0
    status: str = Field("draft", pattern="^(draft|published|archived)$")
    content: dict | None = None
    metadata: dict | None = None


class AdminLessonUpdate(BaseModel):
    level_id: int | None = None
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    lesson_type: str | None = Field(None, pattern="^(vocabulary|phrase|dialogue|culture)$")
    sort_order: int | None = None
    status: str | None = Field(None, pattern="^(draft|published|archived)$")
    content: dict | None = None
    metadata: dict | None = None


class AdminLevelUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class AdminUserStatusUpdate(BaseModel):
    is_active: bool


class AdminSettingUpdate(BaseModel):
    value: str = Field(..., min_length=0, max_length=2000)


# ---------- 埋点分析（V0）----------
class TrackEvent(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=40)
    payload: dict | None = None


class TrackBatch(BaseModel):
    events: list[TrackEvent] = Field(..., min_length=1, max_length=50)


class TopCardStat(BaseModel):
    flashcard_id: int
    count: int
    front_text: str | None = None


class LevelStat(BaseModel):
    level: str
    count: int


class AnalyticsDashboard(BaseModel):
    total_users: int
    active_users_1d: int
    active_users_7d: int
    events_1d: int
    events_7d: int
    top_cards_7d: list[TopCardStat]
    level_distribution: list[LevelStat]
