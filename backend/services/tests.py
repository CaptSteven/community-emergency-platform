from datetime import date, datetime, time as dtime, timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from users.models import UserProfile
from tasks.models import TaskCancellation
from .models import ServiceType, ServiceSubscription, ServiceVisit
from . import scheduler

# 报到定位（乌鲁木齐，与演示居民同城）与健康检查必填数值的公共测试数据
CHECKIN = {'latitude': 43.8256, 'longitude': 87.6168}
VITALS = {'systolic': 120, 'diastolic': 80, 'heart_rate': 72, 'temperature': 36.5}

COMMUNITY = '乌鲁木齐水磨沟社区'


def make_user(username, role, password='123456', **profile):
    # 志愿者默认已认证（正式开通的账号都过了审核）；测未审核场景显式传 is_verified=False
    if role == 'volunteer':
        profile.setdefault('is_verified', True)
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
        created, skipped = scheduler.generate_due_visits(today=date.today())
        self.assertEqual(len(created), 1)
        self.assertEqual(len(skipped), 0)
        self.assertIsNotNone(created[0].volunteer)          # 已自动派单
        self.assertEqual(created[0].status, 'assigned')

    def test_not_due_again_within_period(self):
        ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly', is_active=True)
        scheduler.generate_due_visits(today=date.today())
        again, _ = scheduler.generate_due_visits(today=date.today())
        self.assertEqual(len(again), 0)                     # 未到周期不重复生成

    def test_due_after_period(self):
        sub = ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly', is_active=True)
        scheduler.generate_due_visits(today=date.today() - timedelta(days=7))
        # 关掉上一张开口工单，模拟已完成
        ServiceVisit.objects.filter(subscription=sub).update(status='completed')
        again, _ = scheduler.generate_due_visits(today=date.today())
        self.assertEqual(len(again), 1)

    def test_no_eligible_volunteer_skips_without_empty_visit(self):
        # 无合格志愿者 + 未编排循环组：不生成「无人接」的空工单，改为跳过并汇报
        no_skill_type = ServiceType.objects.create(name='稀有服务', code='rare', required_skill='稀有技能')
        sub = ServiceSubscription.objects.create(
            resident=self.resident, service_type=no_skill_type, frequency='weekly', is_active=True)
        created, skipped = scheduler.generate_due_visits(today=date.today())
        self.assertEqual(len(created), 0)                   # 未生成工单
        self.assertEqual(len(skipped), 1)                   # 记入跳过
        self.assertEqual(skipped[0]['subscription'], sub.id)
        self.assertFalse(ServiceVisit.objects.filter(subscription=sub).exists())
        # 未推进 last_generated_date，下次仍会尝试
        sub.refresh_from_db()
        self.assertIsNone(sub.last_generated_date)


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

    def test_start_complete_then_resident_confirm(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        r0 = self.client.post('/api/service-visits/%d/checkin/' % visit.id, CHECKIN, format='json')
        self.assertEqual(r0.status_code, 200)
        r1 = self.client.post('/api/service-visits/%d/start/' % visit.id, {}, format='json')
        self.assertEqual(r1.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'processing')

        # 志愿者提交完成 -> 待居民确认；此时不计分、不算最终完成
        r2 = self.client.post('/api/service-visits/%d/complete/' % visit.id, {
            'systolic': 128, 'diastolic': 82, 'heart_rate': 74, 'temperature': 36.6,
            'health_note': '血压略高，建议清淡饮食', 'feedback': '老人状态良好',
        }, format='json')
        self.assertEqual(r2.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'pending_confirm')
        self.assertEqual(visit.systolic, 128)
        self.assertEqual(float(visit.temperature), 36.6)
        self.assertIsNotNone(visit.completed_at)
        self.vol.profile.refresh_from_db()
        self.assertEqual(self.vol.profile.points or 0, 0)   # 未确认前不计分
        # 通知落到居民（请确认）
        self.assertTrue(self.resident.notifications.filter(category='service').exists())

        # 居民确认 -> 真正完成 + 给志愿者计分 + 通知志愿者
        self.client.force_authenticate(self.resident)
        r3 = self.client.post('/api/service-visits/%d/confirm/' % visit.id, {}, format='json')
        self.assertEqual(r3.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'completed')
        self.assertIsNotNone(visit.confirmed_at)
        self.vol.profile.refresh_from_db()
        self.assertGreater(self.vol.profile.points or 0, 0)
        self.assertEqual(r3.data['earned_points'], self.vol.profile.points)
        self.assertTrue(self.vol.notifications.filter(category='service').exists())

    def test_confirm_rejected_for_non_owner_resident(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        self.client.post('/api/service-visits/%d/checkin/' % visit.id, CHECKIN, format='json')
        self.client.post('/api/service-visits/%d/start/' % visit.id, {}, format='json')
        self.client.post('/api/service-visits/%d/complete/' % visit.id,
                         dict(VITALS, feedback='ok'), format='json')
        # 另一位居民不能确认别人的工单（get_queryset 收敛 -> 404）
        other_res = make_user('vl_res_x', 'resident', community=COMMUNITY)
        self.client.force_authenticate(other_res)
        resp = self.client.post('/api/service-visits/%d/confirm/' % visit.id, {}, format='json')
        self.assertIn(resp.status_code, (403, 404))
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'pending_confirm')   # 状态未变

    def test_volunteer_cannot_confirm_own_visit(self):
        visit = self._visit(status='pending_confirm')
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/confirm/' % visit.id, {}, format='json')
        self.assertIn(resp.status_code, (403, 404))

    def test_auto_confirm_stale_finalizes_and_scores(self):
        visit = self._visit(status='pending_confirm')
        visit.duration_minutes = 60
        # 完成提交时间设为 49 小时前（超过 48h 阈值）
        visit.completed_at = timezone.now() - timedelta(hours=49)
        visit.save(update_fields=['duration_minutes', 'completed_at'])
        count = scheduler.auto_confirm_stale(hours=48)
        self.assertEqual(count, 1)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'completed')
        self.assertIsNotNone(visit.confirmed_at)
        self.vol.profile.refresh_from_db()
        self.assertGreater(self.vol.profile.points or 0, 0)

    def test_auto_confirm_skips_recent(self):
        visit = self._visit(status='pending_confirm')
        visit.completed_at = timezone.now() - timedelta(hours=47)   # 未超 48h
        visit.save(update_fields=['completed_at'])
        self.assertEqual(scheduler.auto_confirm_stale(hours=48), 0)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'pending_confirm')

    def test_cannot_start_others_visit(self):
        visit = self._visit(volunteer=self.vol)
        self.client.force_authenticate(self.vol2)
        resp = self.client.post('/api/service-visits/%d/checkin/' % visit.id, CHECKIN, format='json')
        self.assertIn(resp.status_code, (403, 404))
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
        ServiceVisit.objects.filter(id=visit.id).update(status='processing')
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
        ServiceVisit.objects.filter(id=visit.id).update(status='processing')
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/complete/' % visit.id,
                                {'systolic': 99999}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_complete_accepts_valid_vitals(self):
        visit = self._visit()
        ServiceVisit.objects.filter(id=visit.id).update(status='processing')
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
            'preferred_slot': 10, 'note': '改了', 'address': '水磨沟区新地址1号', 'is_active': True,
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


class SingleTaskAndPointsTests(APITestCase):
    """单次任务、志愿积分/时长、循环组轮换。"""

    def setUp(self):
        self.admin = make_user('sp_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('sp_res', 'resident', community=COMMUNITY, address='水磨沟区1号',
                                  current_latitude=43.83, current_longitude=87.64)
        self.stype = ServiceType.objects.create(
            name='健康检查', code='health', required_skill='医疗', needs_health_record=True, duration_minutes=30)
        self.vol1 = make_user('sp_v1', 'volunteer', community=COMMUNITY, skills='医疗',
                             current_latitude=43.831, current_longitude=87.641)   # 近
        self.vol2 = make_user('sp_v2', 'volunteer', community=COMMUNITY, skills='医疗',
                             current_latitude=43.90, current_longitude=87.70)     # 远

    # #1 单次任务
    def test_resident_request_single_task(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/service-visits/request-once/', {
            'service_type': self.stype.id, 'address': '水磨沟区临时地址', 'note': '帮忙量血压',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        v = ServiceVisit.objects.get(id=resp.data['visit']['id'])
        self.assertIsNone(v.subscription)          # 单次(无订阅)
        self.assertIsNone(v.volunteer)             # 待管理员派单
        self.assertEqual(v.resident, self.resident)
        self.assertEqual(v.address, '水磨沟区临时地址')
        # 无志愿者时序列化必须给出稳定的空串与「待派单」展示（曾因 SkipField 导致前端 undefined/已排班）
        self.assertEqual(resp.data['visit']['volunteer_name'], '')
        self.assertEqual(resp.data['visit']['status_display'], '待派单')
        # 管理员应收到通知
        self.assertTrue(self.admin.notifications.filter(category='service').exists())

    def test_single_task_kind_filter(self):
        ServiceVisit.objects.create(service_type=self.stype, resident=self.resident,
                                    scheduled_date=date.today(), status='assigned')  # single
        sub = ServiceSubscription.objects.create(resident=self.resident, service_type=self.stype, frequency='weekly')
        ServiceVisit.objects.create(subscription=sub, service_type=self.stype, resident=self.resident,
                                    volunteer=self.vol1, scheduled_date=date.today(), status='assigned')  # recurring
        self.client.force_authenticate(self.admin)
        single = self.client.get('/api/service-visits/?kind=single')
        rows = single.data if isinstance(single.data, list) else single.data.get('results', [])
        self.assertTrue(all(r['subscription'] is None for r in rows))

    # #6 积分 + 时长（积分在居民确认后发放）
    def test_confirm_awards_points_and_duration(self):
        visit = ServiceVisit.objects.create(service_type=self.stype, resident=self.resident,
                                            volunteer=self.vol1, scheduled_date=date.today(), status='assigned')
        self.client.force_authenticate(self.vol1)
        self.client.post('/api/service-visits/%d/checkin/' % visit.id, CHECKIN, format='json')
        self.client.post('/api/service-visits/%d/start/' % visit.id, {}, format='json')
        resp = self.client.post('/api/service-visits/%d/complete/' % visit.id, dict(VITALS, feedback='ok'), format='json')
        self.assertEqual(resp.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'pending_confirm')
        self.assertIsNotNone(visit.duration_minutes)
        self.vol1.profile.refresh_from_db()
        self.assertEqual(self.vol1.profile.points or 0, 0)   # 确认前不计分

        # 居民确认后才计分
        self.client.force_authenticate(self.resident)
        cresp = self.client.post('/api/service-visits/%d/confirm/' % visit.id, {}, format='json')
        self.assertEqual(cresp.status_code, 200)
        self.assertGreaterEqual(cresp.data['earned_points'], 10)
        self.vol1.profile.refresh_from_db()
        self.assertGreaterEqual(self.vol1.profile.points, 10)

    def test_my_stats(self):
        self.client.force_authenticate(self.vol1)
        resp = self.client.get('/api/service-visits/my-stats/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('points', resp.data)
        self.assertIn('week_minutes', resp.data)

    def test_leaderboard(self):
        self.vol1.profile.points = 50; self.vol1.profile.save()
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/analytics/volunteer-leaderboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(any(r['volunteer'] == 'sp_v1' and r['points'] == 50 for r in resp.data))

    # #2 循环组轮换（距离近的排前）
    def test_build_rotation_group_and_rotate(self):
        sub = ServiceSubscription.objects.create(resident=self.resident, service_type=self.stype,
                                                 frequency='weekly', is_active=True)
        ids = scheduler.build_rotation_group(sub)
        self.assertEqual(ids[0], self.vol1.id)   # 近的排第一
        self.assertIn(self.vol2.id, ids)
        v1 = scheduler.create_visit_for(sub, date.today(), notify=False)
        self.assertEqual(v1.volunteer, self.vol1)
        ServiceVisit.objects.filter(id=v1.id).update(status='completed')
        v2 = scheduler.create_visit_for(sub, date.today(), notify=False)
        self.assertEqual(v2.volunteer, self.vol2)   # 轮到下一位

    def test_build_group_admin_only(self):
        sub = ServiceSubscription.objects.create(resident=self.resident, service_type=self.stype, frequency='weekly')
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/service-subscriptions/%d/build-group/' % sub.id, {}, format='json')
        self.assertEqual(resp.status_code, 403)


class ServiceModeAndDailyTests(APITestCase):
    """服务适用方式(单次/周期/通用)过滤 + 每日周期。"""

    def setUp(self):
        self.admin = make_user('mode_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('mode_res', 'resident', community=COMMUNITY)
        # 送餐无技能门槛，配一名同社区志愿者，保证每日到期能自动派单（否则会被空工单守卫跳过）
        self.vol = make_user('mode_v1', 'volunteer', community=COMMUNITY, skills='')
        self.t_single = ServiceType.objects.create(name='维修', code='repair_t', service_mode='single')
        self.t_recur = ServiceType.objects.create(name='送餐', code='meal_t', service_mode='recurring', default_frequency='daily')
        self.t_both = ServiceType.objects.create(name='代购', code='grocery_t', service_mode='both')
        self.t_inactive = ServiceType.objects.create(name='停用单次', code='off_t', service_mode='single', is_active=False)

    def test_for_single_returns_single_and_both_active(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/service-types/?for=single')
        codes = {r['code'] for r in (resp.data if isinstance(resp.data, list) else resp.data['results'])}
        self.assertIn('repair_t', codes)
        self.assertIn('grocery_t', codes)       # both 也出现在单次
        self.assertNotIn('meal_t', codes)        # recurring 不出现
        self.assertNotIn('off_t', codes)         # 停用的不出现

    def test_for_recurring_returns_recurring_and_both(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/service-types/?for=recurring')
        codes = {r['code'] for r in (resp.data if isinstance(resp.data, list) else resp.data['results'])}
        self.assertIn('meal_t', codes)
        self.assertIn('grocery_t', codes)
        self.assertNotIn('repair_t', codes)

    def test_service_mode_in_serializer(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/service-types/?for=single')
        rows = resp.data if isinstance(resp.data, list) else resp.data['results']
        row = next(r for r in rows if r['code'] == 'repair_t')
        self.assertEqual(row['service_mode'], 'single')
        self.assertEqual(row['service_mode_display'], '单次')

    def test_daily_frequency_due_after_one_day(self):
        sub = ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.t_recur, frequency='daily', is_active=True)
        scheduler.generate_due_visits(today=date.today() - timedelta(days=1))
        ServiceVisit.objects.filter(subscription=sub).update(status='completed')
        again, _ = scheduler.generate_due_visits(today=date.today())
        self.assertEqual(len(again), 1)   # 每日：隔天即到期


class ManualRotationGroupTests(APITestCase):
    """管理员手动编排循环组：set-group 覆盖顺序，派单按该顺序。"""

    def setUp(self):
        self.admin = make_user('mg_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('mg_res', 'resident', community=COMMUNITY)
        self.stype = ServiceType.objects.create(name='健康检查', code='mg_health', required_skill='医疗')
        self.v1 = make_user('mg_v1', 'volunteer', community=COMMUNITY, skills='医疗')
        self.v2 = make_user('mg_v2', 'volunteer', community=COMMUNITY, skills='医疗')
        self.sub = ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly', is_active=True)

    def test_admin_set_group_orders_and_dispatches(self):
        self.client.force_authenticate(self.admin)
        # 手动指定顺序：v2 在前
        resp = self.client.post('/api/service-subscriptions/%d/set-group/' % self.sub.id,
                                {'volunteer_ids': [self.v2.id, self.v1.id]}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.rotation_volunteers, [self.v2.id, self.v1.id])
        v = scheduler.create_visit_for(self.sub, date.today(), notify=False)
        self.assertEqual(v.volunteer, self.v2)      # 按手动顺序，第一位是 v2

    def test_set_group_filters_non_volunteers_and_bad_ids(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-subscriptions/%d/set-group/' % self.sub.id,
                                {'volunteer_ids': [self.v1.id, 99999, self.resident.id]}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.rotation_volunteers, [self.v1.id])   # 过滤掉不存在/非志愿者

    def test_set_group_non_admin_forbidden(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/service-subscriptions/%d/set-group/' % self.sub.id,
                                {'volunteer_ids': [self.v1.id]}, format='json')
        self.assertEqual(resp.status_code, 403)


class GenerateNowGuardTests(APITestCase):
    """立即排班守卫：循环组为空必须 400 且不生成工单；编排后正常排班。"""

    def setUp(self):
        self.admin = make_user('gn_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('gn_res', 'resident', community=COMMUNITY)
        self.stype = ServiceType.objects.create(name='健康检查', code='gn_health', required_skill='医疗')
        self.vol = make_user('gn_v1', 'volunteer', community=COMMUNITY, skills='医疗')
        self.sub = ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly', is_active=True)

    def test_generate_now_requires_rotation_group(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-subscriptions/%d/generate-now/' % self.sub.id)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('循环组', resp.data['message'])
        self.assertFalse(ServiceVisit.objects.filter(subscription=self.sub).exists())

    def test_generate_now_ok_with_rotation_group(self):
        self.sub.rotation_volunteers = [self.vol.id]
        self.sub.save(update_fields=['rotation_volunteers'])
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-subscriptions/%d/generate-now/' % self.sub.id)
        self.assertEqual(resp.status_code, 200)
        visit = ServiceVisit.objects.get(subscription=self.sub)
        self.assertEqual(visit.volunteer, self.vol)


class UnverifiedVolunteerGuardTests(APITestCase):
    """未通过审核（is_verified=False）的志愿者不能被安排任务：匹配池、轮换、改派、手动编组全挡。"""

    def setUp(self):
        self.admin = make_user('uv_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('uv_res', 'resident', community=COMMUNITY)
        self.stype = ServiceType.objects.create(name='健康检查', code='uv_health', required_skill='医疗')
        self.ok_vol = make_user('uv_ok', 'volunteer', community=COMMUNITY, skills='医疗')
        self.raw_vol = make_user('uv_raw', 'volunteer', community=COMMUNITY, skills='医疗', is_verified=False)

    def test_eligible_pool_excludes_unverified(self):
        ids = {u.id for u in scheduler.eligible_volunteers(self.stype, COMMUNITY)}
        self.assertIn(self.ok_vol.id, ids)
        self.assertNotIn(self.raw_vol.id, ids)

    def test_rotation_skips_unverified(self):
        sub = ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly', is_active=True,
            rotation_volunteers=[self.raw_vol.id])
        self.assertIsNone(scheduler.next_rotation_volunteer(sub))

    def test_reassign_rejects_unverified(self):
        visit = ServiceVisit.objects.create(
            service_type=self.stype, resident=self.resident, volunteer=self.ok_vol,
            scheduled_date=date.today(), status='assigned')
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-visits/%d/reassign/' % visit.id,
                                {'volunteer_id': self.raw_vol.id}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('未通过审核', resp.data['message'])
        visit.refresh_from_db()
        self.assertEqual(visit.volunteer, self.ok_vol)   # 原志愿者不变

    def test_set_group_filters_unverified(self):
        sub = ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly', is_active=True)
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-subscriptions/%d/set-group/' % sub.id,
                                {'volunteer_ids': [self.raw_vol.id, self.ok_vol.id]}, format='json')
        self.assertEqual(resp.status_code, 200)
        sub.refresh_from_db()
        self.assertEqual(sub.rotation_volunteers, [self.ok_vol.id])

    def test_users_api_verified_filter(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/users/?role=volunteer&verified=true')
        rows = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        names = {r['username'] for r in rows}
        self.assertIn('uv_ok', names)
        self.assertNotIn('uv_raw', names)


class CheckinTests(APITestCase):
    """到场报到：定位必填、距离判定、远程标记、照片补传。"""

    def setUp(self):
        self.resident = make_user('ck_res', 'resident', community=COMMUNITY)
        self.vol = make_user('ck_v1', 'volunteer', community=COMMUNITY, skills='医疗')
        self.stype = ServiceType.objects.create(name='健康检查', code='ck_health', required_skill='医疗')

    def _visit(self, lat=43.8256, lng=87.6168, slot=9):
        return ServiceVisit.objects.create(
            service_type=self.stype, resident=self.resident, volunteer=self.vol,
            scheduled_date=date.today(), scheduled_slot=slot, status='assigned',
            latitude=lat, longitude=lng)

    def test_checkin_requires_location(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/checkin/' % visit.id, {}, format='json')
        self.assertEqual(resp.status_code, 400)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'assigned')   # 状态未变

    def test_checkin_near_ok(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/checkin/' % visit.id, CHECKIN, format='json')
        self.assertEqual(resp.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'checked_in')
        self.assertIsNotNone(visit.checkin_at)
        self.assertLessEqual(visit.checkin_distance_m, 500)
        self.assertFalse(visit.checkin_remote)

    def test_checkin_far_marks_remote_and_notifies(self):
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        # 北京坐标 → 距乌鲁木齐千里之外，仍可报到但标记远程并提醒志愿者数据异常
        resp = self.client.post('/api/service-visits/%d/checkin/' % visit.id,
                                {'latitude': 39.915, 'longitude': 116.404}, format='json')
        self.assertEqual(resp.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'checked_in')
        self.assertTrue(visit.checkin_remote)
        self.assertGreater(visit.checkin_distance_m, 500)
        self.assertIn('远程报到', resp.data['message'])
        self.assertTrue(self.vol.notifications.filter(title='报到位置距离异常').exists())

    def test_checkin_photo_upload(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        self.client.post('/api/service-visits/%d/checkin/' % visit.id, CHECKIN, format='json')
        photo = SimpleUploadedFile('checkin.jpg', b'fakejpegbytes', content_type='image/jpeg')
        resp = self.client.post('/api/service-visits/%d/checkin-photo/' % visit.id,
                                {'photo': photo}, format='multipart')
        self.assertEqual(resp.status_code, 200)
        visit.refresh_from_db()
        self.assertTrue(bool(visit.checkin_photo))

    def test_checkin_photo_base64_channel(self):
        # App 走 base64 JSON 通道（鸿蒙 multipart 在部分设备上发空文件）
        import base64
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        self.client.post('/api/service-visits/%d/checkin/' % visit.id, CHECKIN, format='json')
        b64 = base64.b64encode(b'fake-jpeg-bytes-123').decode()
        resp = self.client.post('/api/service-visits/%d/checkin-photo/' % visit.id,
                                {'photo_b64': b64, 'field': 'photo'}, format='json')
        self.assertEqual(resp.status_code, 200)
        visit.refresh_from_db()
        self.assertTrue(bool(visit.checkin_photo))
        self.assertGreater(visit.checkin_photo.size, 0)

    def test_confirm_photo_base64_channel(self):
        import base64
        visit = self._visit()
        ServiceVisit.objects.filter(id=visit.id).update(status='pending_confirm')
        self.client.force_authenticate(self.resident)
        b64 = base64.b64encode(b'confirm-photo-bytes').decode()
        resp = self.client.post('/api/service-visits/%d/confirm/' % visit.id,
                                {'photo_b64': b64}, format='json')
        self.assertEqual(resp.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'completed')
        self.assertTrue(bool(visit.confirm_photo))
        self.assertGreater(visit.confirm_photo.size, 0)

    def test_checkin_photo_rejected_before_checkin(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        photo = SimpleUploadedFile('checkin.jpg', b'x', content_type='image/jpeg')
        resp = self.client.post('/api/service-visits/%d/checkin-photo/' % visit.id,
                                {'photo': photo}, format='multipart')
        self.assertEqual(resp.status_code, 400)   # 未报到不能传报到照

    def test_others_cannot_checkin(self):
        other = make_user('ck_v2', 'volunteer', community=COMMUNITY, skills='医疗')
        visit = self._visit()
        self.client.force_authenticate(other)
        resp = self.client.post('/api/service-visits/%d/checkin/' % visit.id, CHECKIN, format='json')
        self.assertIn(resp.status_code, (403, 404))

    def test_three_step_flow_enforced(self):
        """三段流程强约束：未报到不能开始/完成；报到后未开始不能完成；全链路走通。"""
        visit = self._visit()
        self.client.force_authenticate(self.vol)
        # 未报到：开始/完成都被拦
        r = self.client.post('/api/service-visits/%d/start/' % visit.id, {}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('报到', r.data['message'])
        r = self.client.post('/api/service-visits/%d/complete/' % visit.id, {'feedback': 'x'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('报到', r.data['message'])
        # 报到后：完成仍被拦（要求先开始）
        self.client.post('/api/service-visits/%d/checkin/' % visit.id, CHECKIN, format='json')
        r = self.client.post('/api/service-visits/%d/complete/' % visit.id, {'feedback': 'x'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('开始任务', r.data['message'])
        # 开始 → 完成 全链路
        r = self.client.post('/api/service-visits/%d/start/' % visit.id, {}, format='json')
        self.assertEqual(r.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'processing')
        self.assertIsNotNone(visit.started_at)
        r = self.client.post('/api/service-visits/%d/complete/' % visit.id, {'feedback': 'ok'}, format='json')
        self.assertEqual(r.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'pending_confirm')

    def test_checked_in_not_punished(self):
        # 已报到的工单即使过了 DDL 也不罚（罚的是根本没到场的）
        visit = self._visit(slot=9)
        ServiceVisit.objects.filter(id=visit.id).update(
            status='checked_in', scheduled_date=date.today() - timedelta(days=1))
        self.assertEqual(scheduler.punish_overdue(), 0)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'checked_in')


class DeadlinePenaltyTests(APITestCase):
    """DDL 罚分：超时未报到转已错过、扣 10 分不为负、双向通知；未到期/待派单不受影响。"""

    def setUp(self):
        self.admin = make_user('dl_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('dl_res', 'resident', community=COMMUNITY)
        self.vol = make_user('dl_v1', 'volunteer', community=COMMUNITY, skills='医疗')
        self.stype = ServiceType.objects.create(name='健康检查', code='dl_health', required_skill='医疗')

    def _visit(self, **kw):
        base = dict(service_type=self.stype, resident=self.resident, volunteer=self.vol,
                    scheduled_date=date.today(), status='assigned')
        base.update(kw)
        return ServiceVisit.objects.create(**base)

    def test_overdue_punished(self):
        self.vol.profile.points = 5
        self.vol.profile.save(update_fields=['points'])
        visit = self._visit(scheduled_date=date.today() - timedelta(days=1), scheduled_slot=9)
        count = scheduler.punish_overdue()
        self.assertEqual(count, 1)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'missed')
        self.vol.profile.refresh_from_db()
        self.assertEqual(self.vol.profile.points, 0)   # 5-10 → 不为负
        self.assertTrue(self.vol.notifications.filter(title__contains='超时未报到').exists())
        self.assertTrue(self.admin.notifications.filter(title__contains='超时未报到').exists())

    def test_not_due_yet_untouched(self):
        # 今天 19 点槽（DDL=20:00）与无槽（DDL=次日0点）在当天上午都不该被罚
        early = datetime.combine(date.today(), dtime(8, 30))
        v1 = self._visit(scheduled_slot=19)
        v2 = self._visit(scheduled_slot=None)
        self.assertEqual(scheduler.punish_overdue(now=early), 0)
        v1.refresh_from_db(); v2.refresh_from_db()
        self.assertEqual(v1.status, 'assigned')
        self.assertEqual(v2.status, 'assigned')

    def test_undispatched_single_task_untouched(self):
        visit = self._visit(volunteer=None, scheduled_date=date.today() - timedelta(days=2))
        self.assertEqual(scheduler.punish_overdue(), 0)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'assigned')   # 待派单不罚

    def test_notify_undispatched_dedup(self):
        visit = self._visit(volunteer=None)
        ServiceVisit.objects.filter(id=visit.id).update(created_at=timezone.now() - timedelta(hours=25))
        self.assertEqual(scheduler.notify_undispatched(), 1)
        self.assertTrue(self.admin.notifications.filter(
            title=scheduler.UNDISPATCHED_TITLE, related_id=visit.id).exists())
        # 再跑一次不重复提醒
        self.assertEqual(scheduler.notify_undispatched(), 0)

    def test_run_maintenance_aggregates(self):
        m = scheduler.run_maintenance()
        self.assertEqual(set(m.keys()), {'auto_confirmed', 'punished', 'undispatched'})


class RemindConfirmTests(APITestCase):
    """催促确认：本人可催、24h 去重、非待确认不可催。"""

    def setUp(self):
        self.resident = make_user('rm_res', 'resident', community=COMMUNITY)
        self.vol = make_user('rm_v1', 'volunteer', community=COMMUNITY, skills='医疗')
        self.stype = ServiceType.objects.create(name='助浴', code='rm_bath', required_skill='')
        self.visit = ServiceVisit.objects.create(
            service_type=self.stype, resident=self.resident, volunteer=self.vol,
            scheduled_date=date.today(), status='pending_confirm')

    def test_remind_then_dedup(self):
        self.client.force_authenticate(self.vol)
        r1 = self.client.post('/api/service-visits/%d/remind-confirm/' % self.visit.id, {}, format='json')
        self.assertEqual(r1.status_code, 200)
        self.assertTrue(self.resident.notifications.filter(title=scheduler.REMIND_TITLE).exists())
        r2 = self.client.post('/api/service-visits/%d/remind-confirm/' % self.visit.id, {}, format='json')
        self.assertEqual(r2.status_code, 400)   # 24h 内不可重复催

    def test_remind_rejected_for_wrong_status(self):
        ServiceVisit.objects.filter(id=self.visit.id).update(status='assigned')
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/remind-confirm/' % self.visit.id, {}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_remind_rejected_for_resident(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/service-visits/%d/remind-confirm/' % self.visit.id, {}, format='json')
        self.assertIn(resp.status_code, (403, 404))


class AssignNotifyResidentTests(APITestCase):
    """派单后通知居民：自动排班与管理员改派都要让居民知道。"""

    def setUp(self):
        self.admin = make_user('an_admin', 'admin', community=COMMUNITY)
        self.resident = make_user('an_res', 'resident', community=COMMUNITY)
        self.vol = make_user('an_v1', 'volunteer', community=COMMUNITY, skills='医疗')
        self.stype = ServiceType.objects.create(name='健康检查', code='an_health', required_skill='医疗')

    def test_auto_assign_notifies_resident(self):
        sub = ServiceSubscription.objects.create(
            resident=self.resident, service_type=self.stype, frequency='weekly',
            preferred_slot=9, is_active=True)
        visit = scheduler.create_visit_for(sub, date.today(), notify=True)
        self.assertIsNotNone(visit.volunteer)
        self.assertEqual(visit.scheduled_slot, 9)   # 订阅时段带入工单
        self.assertTrue(self.resident.notifications.filter(title='服务已安排志愿者').exists())

    def test_reassign_notifies_resident(self):
        visit = ServiceVisit.objects.create(
            service_type=self.stype, resident=self.resident, volunteer=None,
            scheduled_date=date.today(), scheduled_slot=10, status='assigned')
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/service-visits/%d/reassign/' % visit.id,
                                {'volunteer_id': self.vol.id}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(self.resident.notifications.filter(title='服务已安排志愿者').exists())


class RequestOnceValidationTests(APITestCase):
    """单次任务标准化时间校验：坏日期 400（回归原 500 隐患）、槽范围校验。"""

    def setUp(self):
        self.resident = make_user('rq_res', 'resident', community=COMMUNITY)
        self.stype = ServiceType.objects.create(name='代购', code='rq_buy', required_skill='')

    def _post(self, extra):
        self.client.force_authenticate(self.resident)
        payload = {'service_type': self.stype.id, 'address': '地址1号'}
        payload.update(extra)
        return self.client.post('/api/service-visits/request-once/', payload, format='json')

    def test_bad_date_400(self):
        self.assertEqual(self._post({'scheduled_date': 'not-a-date'}).status_code, 400)

    def test_date_out_of_range_400(self):
        far = (date.today() + timedelta(days=30)).isoformat()
        self.assertEqual(self._post({'scheduled_date': far}).status_code, 400)

    def test_bad_slot_400(self):
        self.assertEqual(self._post({'scheduled_slot': 7}).status_code, 400)
        self.assertEqual(self._post({'scheduled_slot': 20}).status_code, 400)

    def test_valid_slot_saved(self):
        resp = self._post({'scheduled_slot': 8,
                           'scheduled_date': (date.today() + timedelta(days=1)).isoformat()})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['visit']['scheduled_slot'], 8)
        self.assertEqual(resp.data['visit']['slot_display'], '08:00-09:00')


class HealthRecordRequiredTests(APITestCase):
    """健康检查服务不能提交空记录；非健康服务不受影响。"""

    def setUp(self):
        self.resident = make_user('hr_res', 'resident', community=COMMUNITY)
        self.vol = make_user('hr_v1', 'volunteer', community=COMMUNITY, skills='医疗 家政')
        self.health_type = ServiceType.objects.create(
            name='健康检查', code='hr_health', required_skill='医疗', needs_health_record=True)
        self.plain_type = ServiceType.objects.create(
            name='保洁', code='hr_clean', required_skill='家政', needs_health_record=False)

    def _visit(self, stype):
        return ServiceVisit.objects.create(
            service_type=stype, resident=self.resident, volunteer=self.vol,
            scheduled_date=date.today(), status='processing')

    def test_health_service_rejects_empty_vitals(self):
        visit = self._visit(self.health_type)
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/complete/' % visit.id,
                                {'feedback': '做完了'}, format='json')
        self.assertEqual(resp.status_code, 400)
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'processing')

    def test_health_service_rejects_partial_vitals(self):
        visit = self._visit(self.health_type)
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/complete/' % visit.id,
                                {'systolic': 120, 'diastolic': 80}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_plain_service_allows_empty_vitals(self):
        visit = self._visit(self.plain_type)
        self.client.force_authenticate(self.vol)
        resp = self.client.post('/api/service-visits/%d/complete/' % visit.id,
                                {'feedback': 'ok'}, format='json')
        self.assertEqual(resp.status_code, 200)
