"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("asset_type", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker"),
    )

    op.create_table(
        "price_bars",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("fetched_at", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "date"),
    )

    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=True),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.String(30), nullable=False),
        sa.Column("fetched_at", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "url"),
    )

    op.create_table(
        "sentiment_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("positive", sa.Float(), nullable=False),
        sa.Column("negative", sa.Float(), nullable=False),
        sa.Column("neutral", sa.Float(), nullable=False),
        sa.Column("label", sa.String(10), nullable=False),
        sa.Column("scored_at", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "signal_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("computed_at", sa.String(30), nullable=False),
        sa.Column("close_price", sa.Float(), nullable=True),
        sa.Column("rsi_14", sa.Float(), nullable=True),
        sa.Column("macd", sa.Float(), nullable=True),
        sa.Column("macd_signal", sa.Float(), nullable=True),
        sa.Column("macd_hist", sa.Float(), nullable=True),
        sa.Column("ma_20", sa.Float(), nullable=True),
        sa.Column("ma_50", sa.Float(), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("sentiment_article_count", sa.Integer(), nullable=True),
        sa.Column("momentum_score", sa.Float(), nullable=True),
        sa.Column("composite_signal", sa.Float(), nullable=True),
        sa.Column("signal_label", sa.String(20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("signal_snapshots")
    op.drop_table("sentiment_scores")
    op.drop_table("news_articles")
    op.drop_table("price_bars")
    op.drop_table("assets")
