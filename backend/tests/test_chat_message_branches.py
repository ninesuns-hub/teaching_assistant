import importlib.util
from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260804_0006_chat_message_branches.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location("chat_branch_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ChatMessageBranchMigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = sa.create_engine("sqlite:///:memory:")
        metadata = sa.MetaData()
        self.conversations = sa.Table(
            "conversations",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
        )
        self.messages = sa.Table(
            "chat_messages",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("conversation_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("in_reply_to_id", sa.Integer(), nullable=True),
        )
        metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_upgrade_backfills_linear_parents_and_active_leaf(self):
        with self.engine.begin() as connection:
            connection.execute(self.conversations.insert().values(id=1))
            connection.execute(self.messages.insert(), [
                {"id": 1, "conversation_id": 1, "role": "user", "in_reply_to_id": None},
                {"id": 2, "conversation_id": 1, "role": "assistant", "in_reply_to_id": 1},
                {"id": 3, "conversation_id": 1, "role": "user", "in_reply_to_id": None},
                {"id": 4, "conversation_id": 1, "role": "assistant", "in_reply_to_id": 3},
            ])
            context = MigrationContext.configure(connection)
            migration = load_migration()
            migration.op = Operations(context)
            migration.upgrade()

            reflected = sa.MetaData()
            conversations = sa.Table("conversations", reflected, autoload_with=connection)
            messages = sa.Table("chat_messages", reflected, autoload_with=connection)
            active_leaf = connection.execute(
                sa.select(conversations.c.active_leaf_message_id)
            ).scalar_one()
            parent = connection.execute(
                sa.select(messages.c.in_reply_to_id).where(messages.c.id == 3)
            ).scalar_one()

        self.assertEqual(active_leaf, 4)
        self.assertEqual(parent, 2)
