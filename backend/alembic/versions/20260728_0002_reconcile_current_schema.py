"""Reconcile imported databases with the current ORM schema.

Revision ID: 20260728_0002
Revises: 20260727_0001
Create Date: 2026-07-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_0002"
down_revision: Union[str, Sequence[str], None] = "20260727_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in _inspector().get_columns(table_name)
    }


def _ensure_index(
    table_name: str,
    index_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    indexes = {
        index["name"]: index
        for index in _inspector().get_indexes(table_name)
    }
    existing = indexes.get(index_name)
    if existing and (
        list(existing.get("column_names") or []) != columns
        or bool(existing.get("unique")) != unique
    ):
        op.drop_index(index_name, table_name=table_name)
        existing = None
    if existing is None:
        op.create_index(
            index_name,
            table_name,
            columns,
            unique=unique,
        )


def _ensure_foreign_key(
    table_name: str,
    local_columns: list[str],
    referred_table: str,
    remote_columns: list[str],
    *,
    constraint_name: str,
    ondelete: str,
) -> None:
    matches = [
        foreign_key
        for foreign_key in _inspector().get_foreign_keys(table_name)
        if foreign_key.get("constrained_columns") == local_columns
        and foreign_key.get("referred_table") == referred_table
        and foreign_key.get("referred_columns") == remote_columns
    ]
    correct = [
        foreign_key
        for foreign_key in matches
        if (foreign_key.get("options") or {}).get("ondelete", "").upper()
        == ondelete.upper()
    ]
    if len(matches) == 1 and len(correct) == 1:
        return
    for foreign_key in matches:
        name = foreign_key.get("name")
        if name:
            op.drop_constraint(name, table_name, type_="foreignkey")
    op.create_foreign_key(
        constraint_name,
        table_name,
        referred_table,
        local_columns,
        remote_columns,
        ondelete=ondelete,
    )


def _reconcile_conversation_summaries() -> None:
    table_name = "conversation_summaries"
    columns = _column_names(table_name)
    if "state_json" not in columns:
        op.add_column(table_name, sa.Column("state_json", sa.Text(), nullable=True))
    if "summarized_through_message_id" not in columns:
        op.add_column(
            table_name,
            sa.Column("summarized_through_message_id", sa.Integer(), nullable=True),
        )
    if "version" not in columns:
        op.add_column(
            table_name,
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            ),
        )
    if "updated_at" not in columns:
        op.add_column(
            table_name,
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    columns = _column_names(table_name)
    if "summary_json" in columns:
        op.execute(sa.text(
            "UPDATE conversation_summaries "
            "SET state_json = summary_json "
            "WHERE state_json IS NULL"
        ))
    if "upto_message_id" in columns:
        op.execute(sa.text(
            "UPDATE conversation_summaries "
            "SET summarized_through_message_id = upto_message_id "
            "WHERE summarized_through_message_id IS NULL"
        ))
    op.execute(sa.text(
        "UPDATE conversation_summaries "
        "SET updated_at = COALESCE(updated_at, created_at, UTC_TIMESTAMP())"
    ))

    # The current model stores one rolling summary per conversation. Imported
    # legacy databases may have multiple cursor snapshots, so retain the most
    # advanced/latest row before adding the unique index.
    op.execute(sa.text(
        "DELETE older FROM conversation_summaries AS older "
        "JOIN conversation_summaries AS newer "
        "  ON newer.conversation_id = older.conversation_id "
        " AND ("
        "      COALESCE(newer.summarized_through_message_id, 0) "
        "        > COALESCE(older.summarized_through_message_id, 0)"
        "   OR ("
        "      COALESCE(newer.summarized_through_message_id, 0) "
        "        = COALESCE(older.summarized_through_message_id, 0) "
        "      AND newer.id > older.id"
        "   )"
        " )"
    ))
    _ensure_index(
        table_name,
        "ix_conversation_summaries_conversation_id",
        ["conversation_id"],
        unique=True,
    )


def upgrade() -> None:
    _reconcile_conversation_summaries()
    _ensure_index(
        "chat_messages",
        "ix_chat_messages_client_message_id",
        ["client_message_id"],
    )
    _ensure_foreign_key(
        "chat_messages",
        ["in_reply_to_id"],
        "chat_messages",
        ["id"],
        constraint_name="fk_chat_messages_in_reply_to_id",
        ondelete="SET NULL",
    )
    _ensure_foreign_key(
        "conversation_summaries",
        ["conversation_id"],
        "conversations",
        ["id"],
        constraint_name="fk_conversation_summaries_conversation_id",
        ondelete="CASCADE",
    )
    _ensure_foreign_key(
        "chat_generation_locks",
        ["conversation_id"],
        "conversations",
        ["id"],
        constraint_name="fk_chat_generation_locks_conversation_id",
        ondelete="CASCADE",
    )
    _ensure_foreign_key(
        "memory_evidence",
        ["memory_id"],
        "memory_items",
        ["id"],
        constraint_name="fk_memory_evidence_memory_id",
        ondelete="CASCADE",
    )
    _ensure_foreign_key(
        "memory_evidence",
        ["conversation_id"],
        "conversations",
        ["id"],
        constraint_name="fk_memory_evidence_conversation_id",
        ondelete="CASCADE",
    )
    _ensure_foreign_key(
        "memory_evidence",
        ["message_id"],
        "chat_messages",
        ["id"],
        constraint_name="fk_memory_evidence_message_id",
        ondelete="CASCADE",
    )
    _ensure_foreign_key(
        "memory_jobs",
        ["conversation_id"],
        "conversations",
        ["id"],
        constraint_name="fk_memory_jobs_conversation_id",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    raise RuntimeError(
        "This reconciliation migration preserves imported legacy objects and "
        "is rolled back by restoring the matching pre-deployment database dump."
    )
