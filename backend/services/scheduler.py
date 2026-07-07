"""社区服务自动排班：按技能匹配 + 轮流（负载最小）把到期的服务计划派给志愿者。

设计要点：
- 到期判定：距上次排班（或起始日）达到该计划周期天数即到期。
- 志愿者筛选：role=volunteer、账号可用、同社区（若居民有社区）、
  且 skills 包含服务类型所需技能关键字。
- 轮流规则：在候选人中选“该服务类型累计工单数最少”者，实现负载均衡式轮换。
- 无人可派：仍生成工单但 volunteer 为空，并通知管理员人工处理。
"""
from datetime import date, timedelta
from math import radians, sin, cos, asin, sqrt

from django.contrib.auth.models import User

from .models import ServiceSubscription, ServiceVisit


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
    vol = User.objects.filter(id=group[idx], is_active=True).first()
    subscription.rotation_index = (idx + 1) % len(group)
    subscription.save(update_fields=['rotation_index'])
    return vol


def eligible_volunteers(service_type, community=''):
    """返回符合该服务类型的候选志愿者查询集（技能 + 社区匹配）。"""
    qs = User.objects.filter(is_active=True, profile__role='volunteer')
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
    return subscription.visits.filter(status__in=['assigned', 'processing']).exists()


def create_visit_for(subscription, today, notify=True):
    """为一个到期计划生成一张工单并自动派单；返回 ServiceVisit。
    优先按循环组轮换(若已建组)；否则回退到负载最小的合格志愿者。"""
    community = community_of(subscription.resident)
    if subscription.rotation_volunteers:
        volunteer = next_rotation_volunteer(subscription)
        if volunteer is None:  # 组内志愿者都不可用则回退
            volunteer = pick_volunteer(subscription.service_type, community)
    else:
        volunteer = pick_volunteer(subscription.service_type, community)
    visit = ServiceVisit.objects.create(
        subscription=subscription,
        service_type=subscription.service_type,
        resident=subscription.resident,
        volunteer=volunteer,
        scheduled_date=today,
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
    """遍历所有到期且无进行中工单的服务计划，批量生成工单并派单。"""
    if today is None:
        today = date.today()
    created = []
    subs = ServiceSubscription.objects.filter(is_active=True).select_related(
        'service_type', 'resident'
    )
    for sub in subs:
        if not is_due(sub, today):
            continue
        if has_open_visit(sub):
            continue
        created.append(create_visit_for(sub, today, notify=notify))
    return created


def _notify_new_visit(visit):
    """新工单通知：有志愿者通知志愿者，无志愿者通知管理员。"""
    # 延迟导入避免应用加载期循环依赖
    from notifications.utils import create_notification

    st = visit.service_type
    if visit.volunteer:
        create_notification(
            recipient=visit.volunteer,
            title='新的上门服务任务',
            content=f'您被安排为 {visit.resident.username} 提供「{st.name}」服务，'
                    f'计划日期 {visit.scheduled_date}。',
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
