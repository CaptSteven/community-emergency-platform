from datetime import date, timedelta

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from users.models import UserProfile
from tasks.models import TaskCancellation
from .models import ServiceType, ServiceSubscription, ServiceVisit
from . import scheduler

COMMUNITY = '乌鲁木齐水磨沟社区'


def make_user(username, role, password='123456', **profile):
    user = User.objects.create_user(username=username, password=password)
    UserProfile.objects.create(user=user, role=role, **profile)
    return user


class ServiceCatalogTests(APITestCase):
    """服务目录权限：仅管理员可维护。"""

    def setUp(self):
        self.admin = make_user('svc_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('svc_res', 'resident', community=COMMUNITY)

    def test_admin_creates_service_type(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-types/', {
            'name': '老人健康检查', 'code': 'health_check', 'category': '医疗健康',
            'required_skill': '医疗', 'default_frequency': 'weekly',
            'needs_health_record': True,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(ServiceType.objects.filter(code='health_check').exists())

    def test_non_admin_cannot_create_service_type(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/service-types/', {
            'name': 'x', 'code': 'x', 'required_skill': '医疗',
        }, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_any_user_can_read_catalog(self):
        ServiceType.objects.create(name='保洁', code='clean', required_skill='')
        self.client.force_authenticate(self.resident)
        resp = self.client.get('/api/service-types/')
        self.assertEqual(resp.status_code, 200)


class SubscriptionTests(APITestCase):
    """服务计划：居民只能为自己订阅。"""

    def setUp(self):
        self.admin = make_user('sub_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('sub_res', 'resident', community=COMMUNITY, address='水磨沟区xx路1号')
        self.other = make_user('sub_other', 'resident', community=COMMUNITY)
        self.stype = ServiceType.objects.create(
            name='健康检查', code='health', required_skill='医疗', needs_health_record=True)

    def test_resident_subscribe_for_self(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/service-subscriptions/', {
            'resident': self.other.id,  # 尝试给别人订阅，应被强制改为自己
            'service_type': self.stype.id, 'frequency': 'weekly', 'preferred_weekday': 0,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        sub = ServiceSubscription.objects.get(id=resp.data['id'])
        self.assertEqual(sub.resident, self.resident)          # 强制为自己
        self.assertEqual(sub.created_by, self.resident)
        self.assertEqual(sub.start_date, date.today())          # 默认起始日期
        self.assertEqual(sub.address, '水磨沟区xx路1号')          # 缺省取居民地址

    def test_resident_only_sees_own_subscriptions(self):
        ServiceSubscription.objects.create(resident=self.resident, service_type=self.stype, frequency='weekly')
        ServiceSubscription.objects.create(resident=self.other, service_type=self.stype, frequency='weekly')
        self.client.force_authenticate(self.resident)
        resp = self.client.get('/api/service-subscriptions/')
        rows = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        self.assertTrue(all(r['resident'] == self.resident.id for r in rows))


class SchedulerRotationTests(APITestCase):
    """自动排班核心：技能匹配 + 轮流（负载最小）。"""

    def setUp(self):
        self.resident = make_user('rot_res', 'resident', community=COMMUNITY, address='水磨沟')
        self.stype = ServiceType.objects.create(
            name='健康检查', code='health', required_skill='医疗', needs_health_record=True)
        self.vol1 = make_user('rot_v1', 'volunteer', community=COMMUNITY, skills='医疗,护理')
        self.vol2 = make_user('rot_v2', 'volunteer', community=COMMUNITY, skills='医疗')
        self.vol_nomed = make_user('rot_v3', 'volunteer', community=COMMUNITY, skills='保洁')
        self.vol_other_comm = make_user('rot_v4', 'volunteer', community='别的社区', skills='医疗')

    def test_pool_matches_skill_and_community(self):
        pool = list(scheduler.eligible_volunteers(self.stype, COMMUNITY))
        ids = {u.id for u in pool}
        self.assertIn(self.vol1.id, ids)
        self.assertIn(self.vol2.id, ids)
        self.assertNotIn(self.vol_nomed.id, ids)        # 技能不符
        self.assertNotIn(self.vol_other_comm.id, ids)   # 社区不符

    def test_rotation_picks_least_loaded(self):
        # vol1 已有一张该类型完成工单 -> 下次应轮到 vol2
        ServiceVisit.objects.create(
            service_type=self.stype, resident=self.resident, volunteer=self.vol1,
            scheduled_date=date.today(), status='completed')
        picked = scheduler.pick_volunteer(self.stype, COMMUNITY)
        self.assertEqual(picked, self.vol2)

    def test_exclude_canceller(self):
        picked = scheduler.pick_volunteer(self.stype, COMMUNITY, exclude_ids=[self.vol1.id])
        self.assertNotEqual(picked, self.vol1)

    def test_generate_due_visits_assigns(self):
        ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly', is_active=True)
        created = scheduler.generate_due_visits(today=date.today())
        self.assertEqual(len(created), 1)
        self.assertIsNotNone(created[0].volunteer)          # 已自动派单
        self.assertEqual(created[0].status, 'assigned')

    def test_not_due_again_within_period(self):
        ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly', is_active=True)
        scheduler.generate_due_visits(today=date.today())
        again = scheduler.generate_due_visits(today=date.today())
        self.assertEqual(len(again), 0)                     # 未到周期不重复生成

    def test_due_after_period(self):
        sub = ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly', is_active=True)
        scheduler.generate_due_visits(today=date.today() - timedelta(days=7))
        # 关掉上一张开口工单，模拟已完成
        ServiceVisit.objects.filter(subscription=sub).update(status='completed')
        again = scheduler.generate_due_visits(today=date.today())
        self.assertEqual(len(again), 1)

    def test_no_eligible_volunteer_notifies_admin(self):
        admin = make_user('rot_admin', 'admin', community=COMMUNITY)
        no_skill_type = ServiceType.objects.create(name='稀有服务', code='rare', required_skill='稀有技能')
        ServiceSubscription.objects.create(
            resident=self.resident, service_type=no_skill_type, frequency='weekly', is_active=True)
        created = scheduler.generate_due_visits(today=date.today())
        self.assertEqual(len(created), 1)
        self.assertIsNone(created[0].volunteer)             # 无人可派
        self.assertTrue(admin.notifications.filter(category='service').exists())


class VisitLifecycleTests(APITestCase):
    """工单生命周期：开始 -> 完成(录健康记录) / 取消(轮换+管控)。"""

    def setUp(self):
        self.admin = make_user('vl_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('vl_res', 'resident', community=COMMUNITY)
        self.stype = ServiceType.objects.create(
            name='健康检查', code='health', required_skill='医疗', needs_health_record=True)
        self.vol = make_user('vl_v1', 'volunteer', community=COMMUNITY, skills='医疗')
        self.vol2 = make_user('vl_v2', 'volunteer', community=COMMUNITY, skills='医疗')

    def _visit(self, volunteer=None, status='assigned'):
        return ServiceVisit.objects.create(
            service_type=self.stype, resident=self.resident,
            volunteer=volunteer or self.vol, scheduled_date=date.today(), status=status)

    def test_start_and_complete_with_health_record(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        r1 = self.client.post('/api/service-visits/%d/start/' % visit.id, {}, format='json')
        self.assertEqual(r1.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'processing')

        r2 = self.client.post('/api/service-visits/%d/complete/' % visit.id, {
            'systolic': 128, 'diastolic': 82, 'heart_rate': 74, 'temperature': 36.6,
            'health_note': '血压略高，建议清淡饮食', 'feedback': '老人状态良好',
        }, format='json')
        self.assertEqual(r2.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'completed')
        self.assertEqual(visit.systolic, 128)
        self.assertEqual(float(visit.temperature), 36.6)
        self.assertIsNotNone(visit.completed_at)
        self.assertTrue(self.resident.notifications.filter(category='service').exists())

    def test_cannot_start_others_visit(self):
        visit = self._visit(volunteer=self.vol)
        self.client.force_authenticate(self.vol2)
        resp = self.client.post('/api/service-visits/%d/start/' % visit.id, {}, format='json')
        self.assertIn(resp.status_code, (403, 404))

    def test_cancel_reverts_and_reassigns(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/cancel/' % visit.id,
                                {'reason': 'illness', 'note': '临时生病'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['monthly_cancel_count'], 1)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'cancelled')
        # 生成一张替补工单，改派给另一位志愿者
        replacement = ServiceVisit.objects.filter(status='assigned', service_type=self.stype).first()
        self.assertIsNotNone(replacement)
        self.assertEqual(replacement.volunteer, self.vol2)
        self.assertEqual(TaskCancellation.objects.filter(volunteer=self.vol, visit__isnull=False).count(), 1)

    def test_resident_sees_own_visits_only(self):
        self._visit()
        other_res = make_user('vl_res2', 'resident', community=COMMUNITY)
        ServiceVisit.objects.create(
            service_type=self.stype, resident=other_res, volunteer=self.vol,
            scheduled_date=date.today(), status='assigned')
        self.client.force_authenticate(self.resident)
        resp = self.client.get('/api/service-visits/')
        rows = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        self.assertTrue(all(r['resident'] == self.resident.id for r in rows))

    def test_admin_reassign(self):
        visit = self._visit()
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-visits/%d/reassign/' % visit.id,
                                {'volunteer_id': self.vol2.id}, format='json')
        self.assertEqual(resp.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.volunteer, self.vol2)


class UnifiedCancelControlTests(APITestCase):
    """服务取消与应急任务取消共用一个月度计数器：>5 警告，>7 撤销。"""

    def setUp(self):
        make_user('uc_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('uc_res', 'resident', community=COMMUNITY)
        self.stype = ServiceType.objects.create(name='代购', code='buy', required_skill='')
        self.vol = make_user('uc_v1', 'volunteer', community=COMMUNITY, skills='')

    def _cancel_once(self):
        visit = ServiceVisit.objects.create(
            service_type=self.stype, resident=self.resident, volunteer=self.vol,
            scheduled_date=date.today(), status='assigned')
        self.client.force_authenticate(self.vol)
        return self.client.post('/api/service-visits/%d/cancel/' % visit.id,
                                {'reason': 'family'}, format='json')

    def test_warning_after_five(self):
        results = [self._cancel_once() for _ in range(6)]
        for i in range(5):
            self.assertFalse(results[i].data['warned'])
        self.assertTrue(results[5].data['warned'])
        self.assertFalse(results[5].data['revoked'])

    def test_revoke_after_seven(self):
        results = [self._cancel_once() for _ in range(8)]
        self.assertTrue(results[7].data['revoked'])
        self.assertEqual(results[7].data['monthly_cancel_count'], 8)
        self.vol.refresh_from_db()
        self.assertFalse(self.vol.is_active)
