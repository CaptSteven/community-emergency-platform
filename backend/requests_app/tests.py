from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from users.models import UserProfile
from requests_app.models import HelpRequest
from tasks.models import VolunteerTask


def make_user(username, role, password='123456', **profile):
    # 志愿者默认已认证（正式开通的账号都过了审核）；测未审核场景显式传 is_verified=False
    if role == 'volunteer':
        profile.setdefault('is_verified', True)
    user = User.objects.create_user(username=username, password=password)
    UserProfile.objects.create(user=user, role=role, **profile)
    return user


class ResidentFlowTests(APITestCase):
    """求助者(居民)流程测试。"""

    def setUp(self):
        self.admin = make_user('admin_r', 'admin')
        self.resident = make_user('res_r', 'resident', community='乌鲁木齐水磨沟社区')
        self.volunteer = make_user('vol_r', 'volunteer')

    def test_register_forces_resident(self):
        # 自助注册即使传 role=volunteer 也强制为居民
        resp = self.client.post('/api/auth/register/', {
            'username': 'selfreg', 'password': '123456', 'role': 'volunteer', 'phone': '13800000000'
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['user']['role'], 'resident')

    def test_only_resident_can_submit(self):
        self.client.force_authenticate(self.volunteer)
        resp = self.client.post('/api/help-requests/', {
            'request_type': 'medical', 'urgency': 'high',
            'description': '志愿者不应能提交求助', 'address': '某地'
        }, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_resident_submit_sets_pending_and_summary(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/help-requests/', {
            'request_type': 'medical', 'urgency': 'high',
            'description': '老人突发不适需要急救', 'address': '朝阳区某小区'
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        hr = HelpRequest.objects.get(id=resp.data['id'])
        self.assertEqual(hr.status, 'pending')
        self.assertEqual(hr.resident, self.resident)
        self.assertTrue(hr.ai_summary)

    def test_resident_cancel_own_request(self):
        hr = HelpRequest.objects.create(
            resident=self.resident, request_type='medical', urgency='high',
            description='测试取消求助', address='地址', status='pending')
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/help-requests/%d/cancel/' % hr.id, {}, format='json')
        self.assertEqual(resp.status_code, 200)
        hr.refresh_from_db()
        self.assertEqual(hr.status, 'cancelled')

    def test_confirm_complete_requires_photo(self):
        hr = HelpRequest.objects.create(
            resident=self.resident, request_type='medical', urgency='high',
            description='处理中的求助', address='地址', status='processing')
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/help-requests/%d/confirm-complete/' % hr.id, {}, format='multipart')
        self.assertEqual(resp.status_code, 400)

    def test_resident_confirm_complete_with_photo(self):
        hr = HelpRequest.objects.create(
            resident=self.resident, request_type='medical', urgency='high',
            description='处理中的求助', address='地址', status='processing')
        VolunteerTask.objects.create(help_request=hr, volunteer=self.volunteer, status='processing')
        self.client.force_authenticate(self.resident)
        photo = SimpleUploadedFile('proof.jpg', b'\xff\xd8jpegbytes', content_type='image/jpeg')
        resp = self.client.post('/api/help-requests/%d/confirm-complete/' % hr.id,
                                {'photo': photo}, format='multipart')
        self.assertEqual(resp.status_code, 200)
        hr.refresh_from_db()
        self.assertEqual(hr.status, 'completed')
        self.assertTrue(hr.completion_photo)
        # 志愿者应被释放为空闲
        self.volunteer.refresh_from_db()
        self.assertTrue(self.volunteer.profile.is_available)

    def test_other_resident_cannot_confirm(self):
        hr = HelpRequest.objects.create(
            resident=self.resident, request_type='medical', urgency='high',
            description='处理中的求助', address='地址', status='processing')
        other = make_user('res_other', 'resident')
        self.client.force_authenticate(other)
        photo = SimpleUploadedFile('proof.jpg', b'x', content_type='image/jpeg')
        resp = self.client.post('/api/help-requests/%d/confirm-complete/' % hr.id,
                                {'photo': photo}, format='multipart')
        self.assertIn(resp.status_code, (403, 404))


class UnverifiedVolunteerAssignTests(APITestCase):
    """未通过审核的志愿者不能被指派求助任务。"""

    def setUp(self):
        self.admin = make_user('admin_uv', 'admin')
        self.resident = make_user('res_uv', 'resident')
        self.raw_vol = make_user('vol_uv', 'volunteer', is_verified=False)

    def test_assign_rejects_unverified_volunteer(self):
        hr = HelpRequest.objects.create(
            resident=self.resident, request_type='medical', urgency='high',
            description='测试', address='地址', status='pending')
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/help-requests/%d/assign/' % hr.id,
                                {'volunteer_id': self.raw_vol.id}, format='json')
        self.assertEqual(resp.status_code, 404)
        self.assertIn('未通过审核', resp.data['message'])
        self.assertFalse(VolunteerTask.objects.filter(help_request=hr).exists())
