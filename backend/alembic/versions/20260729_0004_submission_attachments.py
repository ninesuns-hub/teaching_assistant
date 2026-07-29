"""Add multiple attachments to homework submissions.

Revision ID: 20260729_0004
Revises: 20260728_0003
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260729_0004"
down_revision: Union[str, Sequence[str], None] = "20260728_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = "homework_submission_attachments"

    # The original baseline migration creates the then-current ORM metadata.
    # On a brand-new database that can mean this table already exists before
    # Alembic reaches this revision, while an upgraded beta.6 database still
    # needs it created here.
    if not inspector.has_table(table_name):
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "submission_id",
                sa.Integer(),
                sa.ForeignKey("homework_submissions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("file_path", sa.String(length=500), nullable=False),
            sa.Column("file_type", sa.String(length=20), nullable=False),
            sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        inspector = sa.inspect(bind)

    index_names = {
        index["name"]
        for index in inspector.get_indexes(table_name)
    }
    if "ix_homework_submission_attachments_id" not in index_names:
        op.create_index(
            "ix_homework_submission_attachments_id",
            table_name,
            ["id"],
        )
    if "ix_homework_submission_attachments_submission_id" not in index_names:
        op.create_index(
            "ix_homework_submission_attachments_submission_id",
            table_name,
            ["submission_id"],
        )
    op.execute(
        sa.text(
            """
            INSERT INTO homework_submission_attachments
                (submission_id, filename, file_path, file_type, file_size, created_at)
            SELECT
                id,
                COALESCE(NULLIF(filename, ''), 'submission'),
                file_path,
                COALESCE(
                    NULLIF(file_type, ''),
                    LOWER(SUBSTRING_INDEX(filename, '.', -1)),
                    'file'
                ),
                COALESCE(file_size, 0),
                submitted_at
            FROM homework_submissions
            WHERE file_path IS NOT NULL
              AND file_path <> ''
              AND NOT EXISTS (
                  SELECT 1
                  FROM homework_submission_attachments existing
                  WHERE existing.submission_id = homework_submissions.id
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_homework_submission_attachments_id",
        table_name="homework_submission_attachments",
    )
    op.drop_index(
        "ix_homework_submission_attachments_submission_id",
        table_name="homework_submission_attachments",
    )
    op.drop_table("homework_submission_attachments")
