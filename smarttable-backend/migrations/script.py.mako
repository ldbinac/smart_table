"""${message}

修订 ID: ${up_revision}
创建时间: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# 修订标识符
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """升级数据库模式"""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """降级数据库模式"""
    ${downgrades if downgrades else "pass"}
