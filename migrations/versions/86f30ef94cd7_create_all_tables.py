"""Create all tables

Revision ID: 86f30ef94cd7
Revises: 
Create Date: 2026-03-06 13:58:20.328814

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86f30ef94cd7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add consent fields to patients
    with op.batch_alter_table('patients') as batch_op:
        batch_op.add_column(sa.Column('consent_given', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('consent_given_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('data_deletion_requested', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('data_deletion_requested_at', sa.DateTime(), nullable=True))

    # Add rate-limit tracking to predictions
    with op.batch_alter_table('predictions') as batch_op:
        batch_op.add_column(sa.Column('ip_address', sa.String(50), nullable=True))

    # Add index on audit_logs.action for fast blacklist lookups
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade():
    op.drop_index('ix_audit_logs_created_at', 'audit_logs')
    op.drop_index('ix_audit_logs_action', 'audit_logs')
    with op.batch_alter_table('predictions') as batch_op:
        batch_op.drop_column('ip_address')
    with op.batch_alter_table('patients') as batch_op:
        batch_op.drop_column('data_deletion_requested_at')
        batch_op.drop_column('data_deletion_requested')
        batch_op.drop_column('consent_given_at')
        batch_op.drop_column('consent_given')
