from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from users.models import UserProfile
from requests_app.models import HelpRequest
from tasks.models import VolunteerTask, TaskCancellation


def make_user(username, role, password='123456', **profile):
    # 志愿者默认已认证（正式开通的账号都过了审核）；测未审核场景显式传 is_verified=False
    if role == 'volunteer':
        profile.setdefault('is_verified', True)
    user = User.objects.create_user(username=username, password=password)
    UserProfile.objects.create(user=user, role=role, **profile)
    return user


class VolunteerFlowTests(APITestCase):
    """志愿者流程测试：强制分配、取消、月度警告/撤销。"""

    def setUp(self):
        self.admin = make_user('admin_v', 'admin')
        self.resident = make_user('res_v', 'resident')
        self.volunteer = make_user('vol_v', 'volunteer')

    def _new_request(self, i=0):
        return HelpRequest.objects.create(
            resident=self.resident, request_type='medical', urgency='high',
            description='志愿者测试求助 %d' % i, address='地址 %d' % i, status='pending')

    def _assign(self, hr):
        self.client.force_authenticate(self.admin)
        return self.client.post('/api/help-requests/%d/assign/' % hr.id,
                                {'volunteer_id': self.volunteer.id}, format='json')

    def test_forced_assign_goes_processing_no_accept(self):
        hr = self._new_request()
        resp = self._assign(hr)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['task']['status'], 'processing')
        hr.refresh_from_db()
        self.assertEqual(hr.status, 'processing')
        task = VolunteerTask.objects.get(help_request=hr)
        self.assertEqual(task.volunteer, self.volunteer)
        self.assertIsNotNone(task.accepted_at)

    def test_volunteer_cancel_reverts_request_and_counts(self):
        hr = self._new_request()
        self._assign(hr)
        task = VolunteerTask.objects.get(help_request=hr)
        self.client.force_authenticate(self.volunteer)
        resp = self.client.post('/api/tasks/%d/cancel/' % task.id,
                                {'reason': 'illness', 'note': '临时生病'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['monthly_cancel_count'], 1)
        self.assertFalse(resp.data['warned'])
        self.assertFalse(resp.data['revoked'])
        task.refresh_from_db()
        hr.refresh_from_db()
        self.assertEqual(task.status, 'cancelled')
        self.assertEqual(hr.status, 'pending')  # 求助回退待分配
        self.assertEqual(TaskCancellation.objects.filter(volunteer=self.volunteer).count(), 1)
        self.volunteer.refresh_from_db()
        self.assertTrue(self.volunteer.profile.is_available)  # 释放为空闲

    def test_cannot_cancel_others_task(self):
        hr = self._new_request()
        self._assign(hr)
        task = VolunteerTask.objects.get(help_request=hr)
        other = make_user('vol_other', 'volunteer')
        self.client.force_authenticate(other)
        resp = self.client.post('/api/tasks/%d/cancel/' % task.id, {'reason': 'other'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_invalid_reason_defaults_other(self):
        hr = self._new_request()
        self._assign(hr)
        task = VolunteerTask.objects.get(help_request=hr)
        self.client.force_authenticate(self.volunteer)
        resp = self.client.post('/api/tasks/%d/cancel/' % task.id, {'reason': '乱填的'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(TaskCancellation.objects.get(volunteer=self.volunteer).reason, 'other')

    def _cancel_once(self):
        hr = self._new_request()
        self._assign(hr)
        task = VolunteerTask.objects.get(help_request=hr)
        self.client.force_authenticate(self.volunteer)
        return self.client.post('/api/tasks/%d/cancel/' % task.id, {'reason': 'family'}, format='json')

    def test_warning_threshold_after_five(self):
        results = [self._cancel_once() for _ in range(6)]
        # 第 1-5 次不警告
        for i in range(5):
            self.assertFalse(results[i].data['warned'], '第%d次不应警告' % (i + 1))
        # 第 6 次(超过5)触发警告，但未撤销
        self.assertTrue(results[5].data['warned'])
        self.assertFalse(results[5].data['revoked'])
        self.assertEqual(results[5].data['monthly_cancel_count'], 6)

    def test_revoke_threshold_after_seven(self):
        results = [self._cancel_once() for _ in range(8)]
        # 第 6、7 次警告
        self.assertTrue(results[5].data['warned'])
        self.assertTrue(results[6].data['warned'])
        # 第 8 次(再2次)撤销资格
        self.assertTrue(results[7].data['revoked'])
        self.assertEqual(results[7].data['monthly_cancel_count'], 8)
        self.volunteer.refresh_from_db()
        self.assertFalse(self.volunteer.is_active)  # 账号被停用

    def test_revoked_volunteer_cannot_login(self):
        for _ in range(8):
            self._cancel_once()
        # 撤销后用真实登录接口应失败
        self.client.force_authenticate(user=None)
        resp = self.client.post('/api/auth/login/',
                                {'username': 'vol_v', 'password': '123456'}, format='json')
        self.assertEqual(resp.status_code, 400)
