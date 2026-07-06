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


class AccessControlHardeningTests(APITestCase):
    """评审修复回归：工单直连增删改、越权代订、居民自助订阅。"""

    def setUp(self):
        self.admin = make_user('ac_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('ac_res', 'resident', community=COMMUNITY, address='水磨沟区1号')
        self.other = make_user('ac_other', 'resident', community=COMMUNITY)
        self.vol = make_user('ac_vol', 'volunteer', community=COMMUNITY, skills='医疗')
        self.stype = ServiceType.objects.create(
            name='健康检查', code='health', required_skill='医疗', needs_health_record=True)

    def _visit(self, volunteer=None, resident=None):
        return ServiceVisit.objects.create(
            service_type=self.stype, resident=resident or self.resident,
            volunteer=volunteer or self.vol, scheduled_date=date.today(), status='assigned')

    # B1: 直接创建工单不再 500，而是 405
    def test_direct_visit_create_blocked(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/service-visits/',
                                {'scheduled_date': str(date.today())}, format='json')
        self.assertEqual(resp.status_code, 405)

    # B2: 志愿者不能 DELETE 工单绕过取消管控
    def test_volunteer_cannot_delete_visit(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        resp = self.client.delete('/api/service-visits/%d/' % visit.id)
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(ServiceVisit.objects.filter(id=visit.id).exists())

    # B2: 居民不能 PATCH 伪造健康记录
    def test_resident_cannot_patch_health_record(self):
        visit = self._visit()
        self.client.force_authenticate(self.resident)
        resp = self.client.patch('/api/service-visits/%d/' % visit.id,
                                 {'systolic': 999}, format='json')
        self.assertEqual(resp.status_code, 403)

    # B3: 志愿者不能替他人创建服务计划
    def test_volunteer_cannot_create_subscription(self):
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-subscriptions/', {
            'resident': self.resident.id, 'service_type': self.stype.id, 'frequency': 'weekly',
        }, format='json')
        self.assertEqual(resp.status_code, 403)

    # B3: 居民即使传别人的 resident 也被强制为自己
    def test_resident_subscription_resident_forced_self(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/service-subscriptions/', {
            'resident': self.other.id, 'service_type': self.stype.id, 'frequency': 'weekly',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(ServiceSubscription.objects.get(id=resp.data['id']).resident, self.resident)

    # B6: 居民不传 resident 也能成功自助订阅（App 场景）
    def test_resident_subscribe_without_resident_field(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/service-subscriptions/', {
            'service_type': self.stype.id, 'frequency': 'weekly', 'preferred_weekday': 0,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(ServiceSubscription.objects.get(id=resp.data['id']).resident, self.resident)

    # 管理员不指定 resident 应报 400 而非 500
    def test_admin_subscription_requires_resident(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-subscriptions/', {
            'service_type': self.stype.id, 'frequency': 'weekly',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    # 对抗测试回归：非对象请求体(数组/字符串)不得触发 500
    def test_cancel_with_non_dict_body_no_500(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/cancel/' % visit.id,
                                [1, 2], format='json')
        self.assertNotEqual(resp.status_code, 500)  # 之前会 AttributeError→500

    def test_cancel_nonexistent_with_array_body_no_500(self):
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/99999/cancel/', [1], format='json')
        self.assertIn(resp.status_code, (403, 404))  # 归属/存在校验，绝不 500

    def test_complete_with_string_body_no_500(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/complete/' % visit.id,
                                '"x"', content_type='application/json')
        self.assertNotEqual(resp.status_code, 500)

    def test_reassign_with_array_body_no_500(self):
        visit = self._visit()
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-visits/%d/reassign/' % visit.id,
                                [1], format='json')
        self.assertIn(resp.status_code, (400, 403))  # 缺 volunteer_id → 400

    # 对抗测试回归：超范围体温不得落库（曾导致该行读取 500 的数据投毒 DoS）
    def test_complete_rejects_out_of_range_temperature(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/complete/' % visit.id,
                                {'temperature': 99999.9}, format='json')
        self.assertEqual(resp.status_code, 400)
        visit.refresh_from_db()
        self.assertIsNone(visit.temperature)          # 未落库
        self.assertNotEqual(visit.status, 'completed')  # 未完成
        # 列表仍可正常读取，未被投毒
        self.assertEqual(self.client.get('/api/service-visits/').status_code, 200)

    def test_complete_rejects_out_of_range_systolic(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/complete/' % visit.id,
                                {'systolic': 99999}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_complete_accepts_valid_vitals(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/complete/' % visit.id,
                                {'systolic': 120, 'diastolic': 80, 'heart_rate': 72, 'temperature': 36.6},
                                format='json')
        self.assertEqual(resp.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(float(visit.temperature), 36.6)

    def test_reassign_non_numeric_volunteer_id_no_500(self):
        visit = self._visit()
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-visits/%d/reassign/' % visit.id,
                                {'volunteer_id': 'abc'}, format='json')
        self.assertEqual(resp.status_code, 400)

    # 居民可修改自己的服务计划（App 用 PUT 提交地址/周期等）
    def test_resident_edit_own_subscription_via_put(self):
        sub = ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly')
        self.client.force_authenticate(self.resident)
        resp = self.client.put('/api/service-subscriptions/%d/' % sub.id, {
            'service_type': self.stype.id, 'frequency': 'monthly', 'preferred_weekday': 2,
            'preferred_time': '10:00', 'note': '改了', 'address': '水磨沟区新地址1号', 'is_active': True,
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        sub.refresh_from_db()
        self.assertEqual(sub.frequency, 'monthly')
        self.assertEqual(sub.address, '水磨沟区新地址1号')
        self.assertEqual(sub.resident, self.resident)  # 受益居民不变

    def test_resident_toggle_active_own_subscription(self):
        sub = ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly', is_active=True)
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/service-subscriptions/%d/toggle-active/' % sub.id, {}, format='json')
        self.assertEqual(resp.status_code, 200)
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)


class SubscriptionToggleTests(APITestCase):
    """服务计划暂停/恢复：管理员可操作任意计划，居民仅可操作自己的。"""

    def setUp(self):
        self.admin = make_user('tg_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('tg_res', 'resident', community=COMMUNITY)
        self.other = make_user('tg_other', 'resident', community=COMMUNITY)
        self.vol = make_user('tg_vol', 'volunteer', community=COMMUNITY, skills='医疗')
        self.stype = ServiceType.objects.create(name='代购', code='tg_buy', required_skill='')

    def _sub(self, resident=None, is_active=True):
        return ServiceSubscription.objects.create(
            resident=resident or self.resident, service_type=self.stype,
            frequency='weekly', is_active=is_active)

    def test_owner_can_pause_and_resume(self):
        sub = self._sub()
        self.client.force_authenticate(self.resident)
        r1 = self.client.post('/api/service-subscriptions/%d/toggle-active/' % sub.id, {}, format='json')
        self.assertEqual(r1.status_code, 200)
        self.assertFalse(r1.data['is_active'])
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)
        # 再次调用恢复
        r2 = self.client.post('/api/service-subscriptions/%d/toggle-active/' % sub.id, {}, format='json')
        self.assertTrue(r2.data['is_active'])

    def test_admin_can_toggle_any(self):
        sub = self._sub(resident=self.resident)
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-subscriptions/%d/toggle-active/' % sub.id, {}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['is_active'])

    def test_resident_cannot_toggle_others(self):
        sub = self._sub(resident=self.other)
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/service-subscriptions/%d/toggle-active/' % sub.id, {}, format='json')
        self.assertEqual(resp.status_code, 404)  # get_queryset 收敛后取不到他人计划
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)  # 未被改动

    def test_volunteer_cannot_toggle(self):
        sub = self._sub()
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-subscriptions/%d/toggle-active/' % sub.id, {}, format='json')
        self.assertEqual(resp.status_code, 404)


class UpcomingVisitsTests(APITestCase):
    """未来上门筛选与只读分析接口。"""

    def setUp(self):
        self.admin = make_user('up_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('up_res', 'resident', community=COMMUNITY)
        self.vol = make_user('up_vol', 'volunteer', community=COMMUNITY, skills='医疗')
        self.stype = ServiceType.objects.create(name='健康检查', code='up_health', required_skill='医疗')

    def _visit(self, offset_days, status='assigned'):
        return ServiceVisit.objects.create(
            service_type=self.stype, resident=self.resident, volunteer=self.vol,
            scheduled_date=date.today() + timedelta(days=offset_days), status=status)

    def test_upcoming_filter_on_list(self):
        today_v = self._visit(0)                       # 今天，已排班 -> 命中
        future_v = self._visit(3)                      # 未来，已排班 -> 命中
        self._visit(-2)                                # 过去 -> 不命中
        self._visit(1, status='completed')             # 未来但已完成 -> 不命中
        self.client.force_authenticate(self.vol)
        resp = self.client.get('/api/service-visits/?upcoming=1')
        rows = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        ids = {r['id'] for r in rows}
        self.assertEqual(ids, {today_v.id, future_v.id})

    def test_upcoming_analytics_endpoint(self):
        self._visit(0)
        self._visit(6)
        self._visit(10)                                # 超出 7 天窗口 -> 不计入
        self._visit(-1)                                # 过去 -> 不计入
        self._visit(2, status='cancelled')             # 已取消 -> 不计入
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/analytics/service-upcoming/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 2)
        self.assertEqual(len(resp.data['visits']), 2)


class CancellationHelperTests(APITestCase):
    """共享月度取消管控函数（应急任务与上门服务复用）的直接单元测试。"""

    def setUp(self):
        self.vol = make_user('ch_vol', 'volunteer', community=COMMUNITY)
        self.stype = ServiceType.objects.create(name='代购', code='ch_buy', required_skill='')
        self.resident = make_user('ch_res', 'resident', community=COMMUNITY)

    def _add_cancellations(self, n):
        for _ in range(n):
            visit = ServiceVisit.objects.create(
                service_type=self.stype, resident=self.resident, volunteer=self.vol,
                scheduled_date=date.today(), status='cancelled')
            TaskCancellation.objects.create(volunteer=self.vol, visit=visit, reason='family')

    def test_thresholds(self):
        from tasks.cancellation import evaluate_cancellation
        self._add_cancellations(5)
        count, warned, revoked = evaluate_cancellation(self.vol)
        self.assertEqual((count, warned, revoked), (5, False, False))
        self._add_cancellations(1)  # ->6
        count, warned, revoked = evaluate_cancellation(self.vol)
        self.assertEqual((count, warned, revoked), (6, True, False))
        self._add_cancellations(2)  # ->8
        count, warned, revoked = evaluate_cancellation(self.vol)
        self.assertEqual((count, warned, revoked), (8, False, True))
        self.vol.refresh_from_db()
        self.assertFalse(self.vol.is_active)  # 撤销即停用账号
