"""Add active chat branches and backfill the legacy linear history.

Revision ID: 20260804_0006
Revises: 20260730_0005
Create Date: 2026-08-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260804_0006"
down_revision: Union[str, Sequence[str], None] = "20260730_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("conversations")}
    if "active_leaf_message_id" not in columns:
        with op.batch_alter_table("conversations") as batch_op:
            batch_op.add_column(
                sa.Column("active_leaf_message_id", sa.Integer(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_conversations_active_leaf_message_id",
                "chat_messages",
                ["active_leaf_message_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_index(
                "ix_conversations_active_leaf_message_id",
                ["active_leaf_message_id"],
            )

    metadata = sa.MetaData()
    conversations = sa.Table("conversations", metadata, autoload_with=bind)
    messages = sa.Table("chat_messages", metadata, autoload_with=bind)
    for conversation_id, in bind.execute(
        sa.select(conversations.c.id).order_by(conversations.c.id)
    ):
        rows = list(bind.execute(
            sa.select(messages.c.id, messages.c.role, messages.c.in_reply_to_id)
            .where(messages.c.conversation_id == conversation_id)
            .order_by(messages.c.id)
        ))
        previous_assistant_id = None
        for row in rows:
            if row.role == "user" and row.in_reply_to_id is None and previous_assistant_id:
                bind.execute(
                    messages.update()
                    .where(messages.c.id == row.id)
                    .values(in_reply_to_id=previous_assistant_id)
                )
            if row.role == "assistant":
                previous_assistant_id = row.id
        if rows:
            bind.execute(
                conversations.update()
                .where(conversations.c.id == conversation_id)
                .values(active_leaf_message_id=rows[-1].id)
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("conversations")}
    if "active_leaf_message_id" in columns:
        with op.batch_alter_table("conversations") as batch_op:
            batch_op.drop_index("ix_conversations_active_leaf_message_id")
            batch_op.drop_constraint(
                "fk_conversations_active_leaf_message_id",
                type_="foreignkey",
            )
            batch_op.drop_column("active_leaf_message_id")
