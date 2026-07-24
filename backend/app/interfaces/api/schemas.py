from pydantic import BaseModel, Field, field_validator, model_validator


class ChatRequest(BaseModel):
    message: str = ""
    conversation_id: str | None = None
    class_id: int | None = None
    image_base64: str | None = None
    image_mime: str | None = None

    @model_validator(mode="after")
    def require_message_or_image(self):
        if not self.message.strip() and not self.image_base64:
            raise ValueError("请输入文字或上传图片")
        return self


class ChatResponse(BaseModel):
    reply: str


class SendCodeRequest(BaseModel):
    email: str


class UserRegister(BaseModel):
    email: str
    code: str
    name: str
    password: str
    confirm_password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("code")
    @classmethod
    def code_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("请输入验证码")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码长度至少为 8 位")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("姓名不能为空")
        return v.strip()

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self

class UserLogin(BaseModel):
    email: str
    password: str


class SelectRoleRequest(BaseModel):
    role: str  # student | teacher


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str | None
    name: str | None = None
    email: str | None = None
    needs_role_selection: bool = False


class UserProfile(BaseModel):
    id: int
    email: str
    name: str
    role: str | None
    needs_role_selection: bool


class CreateClassRequest(BaseModel):
    name: str


class JoinClassRequest(BaseModel):
    invite_code: str


class ClassResponse(BaseModel):
    id: int
    name: str
    invite_code: str
    teacher_id: int
    role_in_class: str  # owner | member


class MaterialResponse(BaseModel):
    id: int
    class_id: int
    filename: str
    file_type: str
    file_size: int
    uploaded_at: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    class_id: int | None
    created_at: str
    updated_at: str


class RenameConversationRequest(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("会话标题不能为空")
        if len(title) > 50:
            raise ValueError("会话标题不能超过 50 个字符")
        return title


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    image_url: str | None = None
    feedback: str | None = None
    created_at: str


class MessageFeedbackRequest(BaseModel):
    feedback_type: str


class AddStudentRequest(BaseModel):
    email: str


class StudentBriefResponse(BaseModel):
    id: int
    name: str
    email: str
    joined_at: str | None
    message_count: int = 0
    effective_question_count: int = 0


class LearningReportResponse(BaseModel):
    id: int
    student_id: int
    student_name: str | None = None
    class_id: int
    summary: str
    stats: dict
    message_count: int
    created_at: str


class ClassFeedbackResponse(BaseModel):
    id: int
    class_id: int
    summary: str
    stats: dict
    student_count: int
    created_at: str


class HomeworkAttachmentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int = 0


class HomeworkResponse(BaseModel):
    id: int
    class_id: int
    title: str
    description: str | None = None
    due_at: str | None = None
    attachment_name: str | None = None
    has_attachment: bool = False
    attachments: list[HomeworkAttachmentResponse] = Field(default_factory=list)
    created_at: str
    submission_count: int = 0
    my_submission: dict | None = None


class HomeworkSubmissionResponse(BaseModel):
    id: int
    homework_id: int
    student_id: int
    student_name: str | None = None
    content: str | None = None
    filename: str | None = None
    file_type: str | None = None
    file_size: int = 0
    has_file: bool = False
    submitted_at: str | None = None
