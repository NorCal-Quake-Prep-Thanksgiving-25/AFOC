"""Create core tables."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply the initial schema."""

    op.create_table(
        "usage_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("service", sa.String(length=128), nullable=False),
        sa.Column("cost", sa.Numeric(14, 4), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_table(
        "resource_inventory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_table(
        "utilization",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_id", sa.Integer(), sa.ForeignKey("resource_inventory.id"), nullable=False),
        sa.Column("usage_event_id", sa.Integer(), sa.ForeignKey("usage_events.id"), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("memory_percent", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "anomalies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("resource_id", sa.Integer(), sa.ForeignKey("resource_inventory.id"), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("z_score", sa.Float(), nullable=True),
    )
    op.create_table(
        "rightsizing_recs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_id", sa.Integer(), sa.ForeignKey("resource_inventory.id"), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("estimated_savings", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "forecasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("point_estimate", sa.Numeric(14, 4), nullable=False),
        sa.Column("lower_bound", sa.Numeric(14, 4), nullable=True),
        sa.Column("upper_bound", sa.Numeric(14, 4), nullable=True),
    )
    op.create_table(
        "value_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("value_score", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Drop the initial schema."""

    op.drop_table("value_reports")
    op.drop_table("forecasts")
    op.drop_table("rightsizing_recs")
    op.drop_table("anomalies")
    op.drop_table("utilization")
    op.drop_table("resource_inventory")
    op.drop_table("usage_events")
