"""志愿者取消行为的统一月度管控。

应急任务（tasks）取消与上门服务（services）取消共用同一个月度计数器：
- 本月取消次数 > 5 触发警告；
- 本月取消次数 > 7 自动撤销志愿者资格（停用账号）。

各调用方在自己的事务里先创建对应的 TaskCancellation 记录（task 或 visit），
再调用 evaluate_cancellation 得到 (month_count, warned, revoked)，
随后按各自场景（应急任务 / 上门服务）发送文案不同的通知。
"""
from django.utils import timezone

from .models import TaskCancellation

# 月度取消阈值：> 警告线警告，> 撤销线撤销资格
WARN_THRESHOLD = 5
REVOKE_THRESHOLD = 7


def evaluate_cancellation(volunteer, now=None):
    """统计志愿者本月取消次数并按阈值判定警告/撤销。

    调用前应已创建当次的 TaskCancellation 记录（会被计入本月计数）。
    达到撤销阈值时会就地停用该志愿者账号（is_active=False）。

    返回 (month_count, warned, revoked)。
    """
    now = now or timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_count = TaskCancellation.objects.filter(
        volunteer=volunteer, created_at__gte=month_start
    ).count()

    revoked = month_count > REVOKE_THRESHOLD
    warned = (not revoked) and month_count > WARN_THRESHOLD
    if revoked:
        volunteer.is_active = False
        volunteer.save(update_fields=['is_active'])

    return month_count, warned, revoked
