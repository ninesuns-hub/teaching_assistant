"""Add persistent chat document attachments.

Revision ID: 20260730_0005
Revises: 20260729_0004
Create Date: 2026-07-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_0005"
down_revision: Union[str, Sequence[str], None] = "20260729_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = "chat_message_attachments"
    if not inspector.has_table(table_name):
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(length=36), nullable=False),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "message_id",
                sa.Integer(),
                sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("file_path", sa.String(length=500), nullable=False),
            sa.Column("file_type", sa.String(length=20), nullable=False),
            sa.Column("mime_type", sa.String(length=150), nullable=False),
            sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
            sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("extracted_content", sa.JSON(), nullable=True),
            sa.Column("extraction_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("requires_ocr", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("error_message", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("public_id", name="uq_chat_message_attachments_public_id"),
        )
        inspector = sa.inspect(bind)

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes(table_name)
    }
    for name, columns in (
        ("ix_chat_message_attachments_id", ["id"]),
        ("ix_chat_message_attachments_public_id", ["public_id"]),
        ("ix_chat_message_attachments_user_id", ["user_id"]),
        ("ix_chat_message_attachments_message_id", ["message_id"]),
        ("ix_chat_message_attachments_status", ["status"]),
        ("ix_chat_message_attachments_requires_ocr", ["requires_ocr"]),
    ):
        if name not in existing_indexes:
            op.create_index(name, table_name, columns)


def downgrade() -> None:
    op.drop_table("chat_message_attachments")
