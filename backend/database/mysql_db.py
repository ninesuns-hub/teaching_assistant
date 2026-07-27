import logging

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum
import secrets
import string
import uuid
from datetime import datetime, timezone
from agent_core.config.settings import settings

SQLALCHEMY_DATABASE_URL = f"mysql+mysqlconnector://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"

logger = logging.getLogger(__name__)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=5,
    connect_args={
        "connection_timeout": 5,
        "read_timeout": 10,
        "write_timeout": 10,
    },
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserRole(enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        Enum(
            UserRole,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            length=20,
        ),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    taught_classes = relationship("ClassRoom", back_populates="teacher")
    memberships = relationship("ClassMember", back_populates="student")


class CourseInfo(Base):
    __tablename__ = "course_info"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)
    keywords = Column(Text, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClassRoom(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    invite_code = Column(String(8), unique=True, nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship("User", back_populates="taught_classes")
    members = relationship("ClassMember", back_populates="classroom", cascade="all, delete-orphan")
    materials = relationship("ClassMaterial", back_populates="classroom", cascade="all, delete-orphan")
    homeworks = relationship("HomeworkAssignment", back_populates="classroom", cascade="all, delete-orphan")


class ClassMember(Base):
    __tablename__ = "class_members"
    __table_args__ = (UniqueConstraint("class_id", "student_id", name="uq_class_student"),)

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    classroom = relationship("ClassRoom", back_populates="members")
    student = relationship("User", back_populates="memberships")


class ClassMaterial(Base):
    __tablename__ = "class_materials"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(BigInteger, default=0)
    content_hash = Column(String(64), nullable=True, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    classroom = relationship("ClassRoom", back_populates="materials")


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id = Column(Integer, primary_key=True, index=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    file_type = Column(String(20), nullable=False)
    file_size = Column(BigInteger, default=0)
    index_status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sources = relationship(
        "RagDocumentSource",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class RagDocumentSource(Base):
    __tablename__ = "rag_document_sources"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("rag_documents.id"), nullable=False, index=True)
    scope_type = Column(String(20), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True, index=True)
    material_id = Column(Integer, ForeignKey("class_materials.id"), nullable=True, unique=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("RagDocument", back_populates="sources")


class HomeworkAssignment(Base):
    __tablename__ = "homework_assignments"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    due_at = Column(DateTime, nullable=True)
    attachment_path = Column(String(500), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    classroom = relationship("ClassRoom", back_populates="homeworks")
    attachments = relationship("HomeworkAttachment", back_populates="homework", cascade="all, delete-orphan")
    submissions = relationship("HomeworkSubmission", back_populates="homework", cascade="all, delete-orphan")


class HomeworkAttachment(Base):
    __tablename__ = "homework_attachments"

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homework_assignments.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    homework = relationship("HomeworkAssignment", back_populates="attachments")


class HomeworkSubmission(Base):
    __tablename__ = "homework_submissions"
    __table_args__ = (UniqueConstraint("homework_id", "student_id", name="uq_homework_student"),)

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homework_assignments.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True)
    filename = Column(String(255), nullable=True)
    file_type = Column(String(20), nullable=True)
    file_size = Column(BigInteger, default=0)
    submitted_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    homework = relationship("HomeworkAssignment", back_populates="submissions")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False, default="新对话")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    image_path = Column(String(300), nullable=True)
    retrieved_context = Column(Text, nullable=True)
    feedback_type = Column(String(20), nullable=True)
    feedback_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class StudentLearningReport(Base):
    __tablename__ = "student_learning_reports"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    summary = Column(Text, nullable=False)
    stats_json = Column(Text, nullable=True)
    message_count = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)


class ClassLearningFeedback(Base):
    __tablename__ = "class_learning_feedback"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    stats_json = Column(Text, nullable=True)
    student_count = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)


class LearningGenerationJob(Base):
    __tablename__ = "learning_generation_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kind = Column(String(30), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="queued", index=True)
    dedupe_key = Column(String(100), nullable=True, unique=True)
    result_id = Column(Integer, nullable=True)
    error_message = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


def generate_invite_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def init_mysql():
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            connection_timeout=5,
            read_timeout=10,
            write_timeout=10,
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DB} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")

    try:
        Base.metadata.create_all(bind=engine)
        _migrate_schema()
    except SQLAlchemyError as exc:
        # Database availability must not prevent the API process from starting.
        # Requests will receive a controlled 503 until MySQL recovers.
        logger.error("数据库初始化暂不可用: %s", exc)


def _migrate_schema():
    """兼容已有数据库的简单迁移"""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE users MODIFY COLUMN role VARCHAR(20) NULL"
            ))
        except Exception:
            pass
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN name VARCHAR(100) NOT NULL DEFAULT '' AFTER email"
            ))
        except Exception:
            pass
        try:
            conn.execute(text(
                "ALTER TABLE chat_messages ADD COLUMN image_path VARCHAR(300) NULL AFTER content"
            ))
        except Exception:
            pass
        try:
            conn.execute(text(
                "ALTER TABLE chat_messages ADD COLUMN feedback_type VARCHAR(20) NULL AFTER retrieved_context"
            ))
        except Exception:
            pass
        try:
            conn.execute(text(
                "ALTER TABLE chat_messages ADD COLUMN feedback_at DATETIME NULL AFTER feedback_type"
            ))
        except Exception:
            pass
        try:
            conn.execute(text(
                "ALTER TABLE conversations ADD COLUMN public_id VARCHAR(36) NULL AFTER id"
            ))
        except Exception:
            pass
        rows = conn.execute(text(
            "SELECT id FROM conversations WHERE public_id IS NULL OR public_id = ''"
        )).fetchall()
        for row in rows:
            conn.execute(
                text("UPDATE conversations SET public_id = :public_id WHERE id = :id"),
                {"public_id": str(uuid.uuid4()), "id": row[0]},
            )
        try:
            conn.execute(text(
                "CREATE UNIQUE INDEX ix_conversations_public_id ON conversations (public_id)"
            ))
        except Exception:
            pass
        try:
            conn.execute(text(
                "ALTER TABLE conversations MODIFY COLUMN public_id VARCHAR(36) NOT NULL"
            ))
        except Exception:
            pass
        try:
            conn.execute(text(
                "ALTER TABLE class_materials ADD COLUMN content_hash VARCHAR(64) NULL AFTER file_size"
            ))
        except Exception:
            pass
        try:
            conn.execute(text(
                "CREATE INDEX ix_class_materials_content_hash ON class_materials (content_hash)"
            ))
        except Exception:
            pass
        try:
            conn.execute(text(
                """
                INSERT INTO homework_attachments
                    (homework_id, filename, file_path, file_type, file_size, created_at)
                SELECT
                    h.id,
                    COALESCE(h.attachment_name, 'attachment'),
                    h.attachment_path,
                    LOWER(SUBSTRING_INDEX(COALESCE(h.attachment_name, ''), '.', -1)),
                    0,
                    COALESCE(h.created_at, UTC_TIMESTAMP())
                FROM homework_assignments h
                WHERE h.attachment_path IS NOT NULL
                  AND h.attachment_path <> ''
                  AND NOT EXISTS (
                      SELECT 1
                      FROM homework_attachments a
                      WHERE a.homework_id = h.id
                        AND a.file_path = h.attachment_path
                  )
                """
            ))
        except Exception as exc:
            logger.warning("迁移旧作业附件失败: %s", exc)
        conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
