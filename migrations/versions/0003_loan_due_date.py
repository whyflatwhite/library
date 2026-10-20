"""Срок возврата выдачи: loans.due_at (новая функция «просроченные выдачи»)."""
from datetime import timedelta

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

BACKFILL_DAYS = 14

loans = sa.table(
    "loans",
    sa.column("id", sa.Integer),
    sa.column("issued_at", sa.DateTime),
    sa.column("due_at", sa.DateTime),
)


def upgrade():
    op.add_column("loans", sa.Column("due_at", sa.DateTime, nullable=True))
    bind = op.get_bind()
    rows = bind.execute(sa.select(loans.c.id, loans.c.issued_at)).fetchall()
    for loan_id, issued_at in rows:
        due_at = issued_at + timedelta(days=BACKFILL_DAYS)
        bind.execute(sa.update(loans).where(loans.c.id == loan_id).values(due_at=due_at))
    with op.batch_alter_table("loans") as batch_op:
        batch_op.alter_column("due_at", existing_type=sa.DateTime(), nullable=False)


def downgrade():
    with op.batch_alter_table("loans") as batch_op:
        batch_op.drop_column("due_at")
