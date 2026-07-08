"""社区服务自动排班：按技能匹配 + 轮流（负载最小）把到期的服务计划派给志愿者。

设计要点：
- 到期判定：距上次排班（或起始日）达到该计划周期天数即到期。
- 志愿者筛选：role=volunteer、账号可用、同社区（若居民有社区）、
  且 skills 包含服务类型所需技能关键字。
- 轮流规则：在候选人中选“该服务类型累计工单数最少”者，实现负载均衡式轮换。
- 无人可派：仍生成工单但 volunteer 为空，并通知管理员人工处理。
"""
from datetime import date, datetime, time, timedelta
from math import radians, sin, cos, asin, sqrt

from django.contrib.auth.models import User

from .models import ServiceSubscription, ServiceVisit

# 通知去重键（title + related_type + related_id），文案改动必须同步这里
UNDISPATCHED_TITLE = '单次任务超时未派单'
REMIND_TITLE = '请尽快确认服务完成'


FREQ_DAYS = {'daily': 1, 'weekly': 7, 'biweekly': 14, 'monthly': 30}


def haversine_km(lat1, lng1, lat2, lng2):
    """两点球面距离(公里)；任一坐标缺失返回一个大数(排到最后)。"""
    if None in (lat1, lng1, lat2, lng2):
        return 1e9
    lat1, lng1, lat2, lng2 = map(lambda v: radians(float(v)), (lat1, lng1, lat2, lng2))
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))


def build_rotation_group(subscription, save=True):
    """智能筛选循环组：技能+社区合格的志愿者，按到居民的距离由近到远排序，
    组成有序轮换名单存入 subscription.rotation_volunteers，重置 rotation_index=0。返回 id 列表。"""
    res = subscription.resident
    rp = getattr(res, 'profile', None)
    r_lat = getattr(rp, 'current_latitude', None) if rp else None
    r_lng = getattr(rp, 'current_longitude', None) if rp else None
    community = community_of(res)
    pool = list(eligible_volunteers(subscription.service_type, community).select_related('profile'))

    def dist(v):
        vp = getattr(v, 'profile', None)
        return haversine_km(r_lat, r_lng, getattr(vp, 'current_latitude', None) if vp else None,
                            getattr(vp, 'current_longitude', None) if vp else None)

    pool.sort(key=lambda v: (dist(v), _load(v, subscription.service_type), v.id))
    ids = [v.id for v in pool]
    if save:
        subscription.rotation_volunteers = ids
        subscription.rotation_index = 0
        subscription.save(update_fields=['rotation_volunteers', 'rotation_index'])
    return ids


def next_rotation_volunteer(subscription):
    """按循环组取下一位志愿者并推进指针；组为空返回 None。"""
    group = list(subscription.rotation_volunteers or [])
    if not group:
        return None
    idx = subscription.rotation_index % len(group)
    vol = User.objects.filter(id=group[idx], is_active=True, profile__is_verified=True).first()
    subscription.rotation_index = (idx + 1) % len(group)
    subscription.save(update_fields=['rotation_index'])
    return vol


def eligible_volunteers(service_type, community=''):
    """返回符合该服务类型的候选志愿者查询集（技能 + 社区匹配）。"""
    qs = User.objects.filter(is_active=True, profile__role='volunteer', profile__is_verified=True)
    if community:
        qs = qs.filter(profile__community=community)
    skill = (service_type.required_skill or '').strip()
    if skill:
        qs = qs.filter(profile__skills__icontains=skill)
    return qs


def _load(volunteer, service_type):
    """志愿者在该服务类型上的历史工单数（不含已取消），作为轮换权重。"""
    return ServiceVisit.objects.filter(
        volunteer=volunteer, service_type=service_type
    ).exclude(status='cancelled').count()


def pick_volunteer(service_type, community='', exclude_ids=None):
    """按轮流规则挑选一名志愿者；无候选返回 None。"""
    exclude_ids = set(exclude_ids or [])
    pool = [v for v in eligible_volunteers(service_type, community) if v.id not in exclude_ids]
    if not pool:
        return None
    # 负载最小优先，负载相同按 id 稳定排序，实现轮流
    pool.sort(key=lambda v: (_load(v, service_type), v.id))
    return pool[0]


def community_of(user):
    profile = getattr(user, 'profile', None)
    return (getattr(profile, 'community', '') or '') if profile else ''


def is_due(subscription, today):
    if not subscription.is_active:
        return False
    if subscription.start_date and subscription.start_date > today:
        return False
    period = FREQ_DAYS.get(subscription.frequency, 7)
    if subscription.last_generated_date is None:
        return True
    return (today - subscription.last_generated_date).days >= period


def has_open_visit(subscription):
    return subscription.visits.filter(status__in=['assigned', 'checked_in', 'processing']).exists()


def create_visit_for(subscription, today, notify=True):
    """为一个到期计划生成一张工单并自动派单；返回 ServiceVisit，无可派志愿者则返回 None。
    优先按循环组轮换(若已建组)；否则回退到负载最小的合格志愿者。
    关键：若既无循环组、又匹配不到可用志愿者，则不生成「无人接」的空工单（返回 None，由上层跳过并汇报）。"""
    community = community_of(subscription.resident)
    if subscription.rotation_volunteers:
        volunteer = next_rotation_volunteer(subscription)
        if volunteer is None:  # 组内志愿者都不可用则回退
            volunteer = pick_volunteer(subscription.service_type, community)
    else:
        volunteer = pick_volunteer(subscription.service_type, community)
    if volunteer is None:
        # 无循环组且无合格志愿者：拒绝生成空工单，也不推进 last_generated_date（下次仍会尝试）
        return None
    visit = ServiceVisit.objects.create(
        subscription=subscription,
        service_type=subscription.service_type,
        resident=subscription.resident,
        volunteer=volunteer,
        scheduled_date=today,
        scheduled_slot=subscription.preferred_slot,
        status='assigned',
        address=subscription.address or '',
        latitude=subscription.latitude,
        longitude=subscription.longitude,
    )
    subscription.last_generated_date = today
    subscription.save(update_fields=['last_generated_date'])
    if notify:
        _notify_new_visit(visit)
    return visit


def generate_due_visits(today=None, notify=True):
    """遍历所有到期且无进行中工单的服务计划，批量生成工单并派单。

    返回 (created, skipped)：
    - created：成功生成并派单的 ServiceVisit 列表；
    - skipped：因无循环组且无可用志愿者而跳过的计划信息 [{'subscription','resident','service_type'}]。
    """
    if today is None:
        today = date.today()
    created = []
    skipped = []
    subs = ServiceSubscription.objects.filter(is_active=True).select_related(
        'service_type', 'resident'
    )
    for sub in subs:
        if not is_due(sub, today):
            continue
        if has_open_visit(sub):
            continue
        visit = create_visit_for(sub, today, notify=notify)
        if visit is None:
            skipped.append({
                'subscription': sub.id,
                'resident': sub.resident.username,
                'service_type': sub.service_type.name,
            })
            continue
        created.append(visit)
    return created, skipped


def finalize_visit(visit):
    """把「待居民确认」工单结单为「已完成」，给志愿者计分并通知。返回本次积分。

    唯一的计分落点（居民 confirm 与 auto_confirm_stale 共用），避免重复计分。
    """
    from django.utils import timezone
    from notifications.utils import create_notification

    visit.status = 'completed'
    visit.confirmed_at = timezone.now()
    visit.save(update_fields=['status', 'confirm_photo', 'confirmed_at'])

    # 志愿积分：每次服务基础 10 分 + 每满 30 分钟加 5 分
    earned = 10 + ((visit.duration_minutes or 0) // 30) * 5
    vol = visit.volunteer
    vp = getattr(vol, 'profile', None) if vol else None
    if vp is not None:
        vp.points = (vp.points or 0) + earned
        vp.save(update_fields=['points'])
        create_notification(
            recipient=vol,
            title='居民已确认服务完成',
            content=f'{visit.resident.username} 已确认你的「{visit.service_type.name}」服务，获得 {earned} 积分。',
            category='service', related_type='service_visit', related_id=visit.id,
        )
    return earned


def auto_confirm_stale(hours=48, now=None):
    """把超过 N 小时仍未被居民确认的「待居民确认」工单自动结单并计分。返回自动确认的数量。"""
    from django.utils import timezone

    if now is None:
        now = timezone.now()
    deadline = now - timedelta(hours=hours)
    stale = ServiceVisit.objects.filter(
        status='pending_confirm', completed_at__lt=deadline
    ).select_related('volunteer', 'volunteer__profile', 'resident', 'service_type')
    count = 0
    for visit in stale:
        finalize_visit(visit)
        count += 1
    return count


def slot_display(slot):
    """整点槽显示文本；None 返回空串。"""
    if slot is None:
        return ''
    return f'{slot:02d}:00-{slot + 1:02d}:00'


def visit_deadline(visit):
    """报到 DDL：所选时段结束整点；未选时段则为服务日次日 00:00（naive 本地时间，USE_TZ=False）。"""
    if visit.scheduled_slot is not None:
        return datetime.combine(visit.scheduled_date, time(visit.scheduled_slot + 1, 0))
    return datetime.combine(visit.scheduled_date + timedelta(days=1), time(0, 0))


OVERDUE_PENALTY = 10  # 超时未报到扣分


def punish_overdue(now=None):
    """超过 DDL 仍未到场报到的工单：转「已错过」、志愿者扣分(不为负)、通知志愿者与管理员。

    只处理已派单(volunteer 非空)且仍为 assigned 的工单——待派单的单次任务不在此列。
    须在 generate_due_visits 之前执行：missed 后订阅才能生成下一张工单。
    """
    from django.utils import timezone
    from notifications.utils import create_notification

    if now is None:
        now = timezone.now()
    candidates = ServiceVisit.objects.filter(
        status='assigned', volunteer__isnull=False, scheduled_date__lte=now.date()
    ).select_related('volunteer', 'volunteer__profile', 'resident', 'service_type')
    admins = list(User.objects.filter(is_active=True).filter(models_q_admin()))
    count = 0
    for visit in candidates:
        if now < visit_deadline(visit):
            continue
        visit.status = 'missed'
        visit.save(update_fields=['status'])
        vp = getattr(visit.volunteer, 'profile', None)
        if vp is not None:
            vp.points = max(0, (vp.points or 0) - OVERDUE_PENALTY)
            vp.save(update_fields=['points'])
        slot_part = f'（时段 {slot_display(visit.scheduled_slot)}）' if visit.scheduled_slot is not None else ''
        create_notification(
            recipient=visit.volunteer,
            title='服务超时未报到，已扣分',
            content=f'{visit.resident.username} 的「{visit.service_type.name}」服务'
                    f'{slot_part}已超时未到场报到，工单转为已错过，扣除 {OVERDUE_PENALTY} 积分。',
            category='service', related_type='service_visit', related_id=visit.id,
        )
        for admin in admins:
            create_notification(
                recipient=admin,
                title='工单超时未报到',
                content=f'志愿者 {visit.volunteer.username} 未在 DDL 前报到，'
                        f'{visit.resident.username} 的「{visit.service_type.name}」已转已错过，请改派。',
                category='service', related_type='service_visit', related_id=visit.id,
            )
        count += 1
    return count


def notify_undispatched(now=None):
    """单次任务提交超 24 小时仍未派单：提醒管理员（按通知标题+工单去重，只提醒一次）。"""
    from django.utils import timezone
    from notifications.models import Notification
    from notifications.utils import create_notification

    if now is None:
        now = timezone.now()
    stale = ServiceVisit.objects.filter(
        subscription__isnull=True, volunteer__isnull=True, status='assigned',
        created_at__lt=now - timedelta(hours=24),
    ).select_related('resident', 'service_type')
    admins = list(User.objects.filter(is_active=True).filter(models_q_admin()))
    count = 0
    for visit in stale:
        if Notification.objects.filter(
            title=UNDISPATCHED_TITLE, related_type='service_visit', related_id=visit.id
        ).exists():
            continue
        for admin in admins:
            create_notification(
                recipient=admin,
                title=UNDISPATCHED_TITLE,
                content=f'{visit.resident.username} 的「{visit.service_type.name}」单次任务'
                        f'已提交超过 24 小时仍未分配志愿者，请尽快在地图上派单。',
                category='service', related_type='service_visit', related_id=visit.id,
            )
        count += 1
    return count


def run_maintenance(now=None):
    """例行维护聚合入口（每日命令与管理员「生成排班」共用）：
    自动确认超时未确认 → 惩罚超时未报到 → 提醒超时未派单。顺序不可调换（punish 需在生成前）。"""
    return {
        'auto_confirmed': auto_confirm_stale(now=now),
        'punished': punish_overdue(now=now),
        'undispatched': notify_undispatched(now=now),
    }


def _notify_new_visit(visit):
    """新工单通知：有志愿者通知志愿者，无志愿者通知管理员。"""
    # 延迟导入避免应用加载期循环依赖
    from notifications.utils import create_notification

    st = visit.service_type
    slot_part = f' {slot_display(visit.scheduled_slot)}' if visit.scheduled_slot is not None else ''
    if visit.volunteer:
        create_notification(
            recipient=visit.volunteer,
            title='新的上门服务任务',
            content=f'您被安排为 {visit.resident.username} 提供「{st.name}」服务，'
                    f'计划日期 {visit.scheduled_date}{slot_part}。',
            category='service',
            related_type='service_visit',
            related_id=visit.id,
        )
        # 同步告知居民：任务已分配到人
        create_notification(
            recipient=visit.resident,
            title='服务已安排志愿者',
            content=f'您的「{st.name}」服务已安排志愿者 {visit.volunteer.username} 上门，'
                    f'计划日期 {visit.scheduled_date}{slot_part}。',
            category='service',
            related_type='service_visit',
            related_id=visit.id,
        )
    else:
        for admin in User.objects.filter(is_active=True).filter(
            models_q_admin()
        ):
            create_notification(
                recipient=admin,
                title='服务工单待人工派单',
                content=f'{visit.resident.username} 的「{st.name}」服务暂无匹配志愿者，请人工指派。',
                category='service',
                related_type='service_visit',
                related_id=visit.id,
            )


def models_q_admin():
    """管理员筛选条件：超级用户或 profile.role=admin。"""
    from django.db.models import Q
    return Q(is_superuser=True) | Q(profile__role='admin')
