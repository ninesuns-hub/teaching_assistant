from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum
import secrets
import string
from datetime import datetime
from agent_core.config.settings import settings

SQLALCHEMY_DATABASE_URL = f"mysql+mysqlconnector://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


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
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    classroom = relationship("ClassRoom", back_populates="materials")


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
    submissions = relationship("HomeworkSubmission", back_populates="homework", cascade="all, delete-orphan")


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


def generate_invite_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def init_mysql():
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=settings.MYSQL_HOST,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DB} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")

    Base.metadata.create_all(bind=engine)
    _migrate_schema()


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
        conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
