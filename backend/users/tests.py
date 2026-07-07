from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from users.models import UserProfile


def make_user(username, role, password='123456', **profile):
    user = User.objects.create_user(username=username, password=password)
    UserProfile.objects.create(user=user, role=role, **profile)
    return user


class UserManagementTests(APITestCase):
    """管理员用户管理 + 志愿者账号仅管理员开通。"""

    def setUp(self):
        self.admin = make_user('admin_u', 'admin')
        self.resident = make_user('res_u', 'resident')

    def test_admin_creates_volunteer(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/users/', {
            'username': 'newvol', 'password': '123456', 'role': 'volunteer',
            'phone': '13800000001', 'community': '乌鲁木齐水磨沟社区', 'skills': '医疗'
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['role'], 'volunteer')
        u = User.objects.get(username='newvol')
        self.assertEqual(u.profile.role, 'volunteer')
        self.assertTrue(u.check_password('123456'))

    def test_non_admin_cannot_list_users(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, 403)

    def test_non_admin_cannot_create_user(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.post('/api/users/', {
            'username': 'x', 'password': '123456', 'role': 'volunteer'
        }, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_edit_and_reset_password(self):
        vol = make_user('editvol', 'volunteer')
        self.client.force_authenticate(self.admin)
        resp = self.client.patch('/api/users/%d/' % vol.id,
                                 {'password': 'newpass1', 'phone': '13999999999'}, format='json')
        self.assertEqual(resp.status_code, 200)
        vol.refresh_from_db()
        self.assertTrue(vol.check_password('newpass1'))
        self.assertEqual(vol.profile.phone, '13999999999')

    def test_cannot_delete_superuser(self):
        su = User.objects.create_superuser('root_u', '', '123456')
        self.client.force_authenticate(self.admin)
        resp = self.client.delete('/api/users/%d/' % su.id)
        self.assertEqual(resp.status_code, 400)

    def test_admin_can_delete_volunteer(self):
        vol = make_user('delvol', 'volunteer')
        self.client.force_authenticate(self.admin)
        resp = self.client.delete('/api/users/%d/' % vol.id)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(User.objects.filter(username='delvol').exists())

    def test_user_list_has_monthly_cancel_count(self):
        make_user('listvol', 'volunteer')
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, 200)
        rows = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        self.assertTrue(any('monthly_cancel_count' in r for r in rows))


class VolunteerApplicationTests(APITestCase):
    """志愿者线上申请：提交建 inactive 账号 → 审核通过后可登录且已认证。"""

    def setUp(self):
        self.admin = make_user('va_admin', 'admin')

    def test_submit_creates_inactive_volunteer_and_notifies_admin(self):
        resp = self.client.post('/api/volunteer-applications/', {
            'username': 'newvol', 'password': '123456', 'phone': '13900000000',
            'community': '乌鲁木齐水磨沟社区', 'skills': '维修 家政', 'note': '有经验',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        u = User.objects.get(username='newvol')
        self.assertFalse(u.is_active)                       # 审核前不可用
        self.assertEqual(u.profile.role, 'volunteer')
        self.assertFalse(u.profile.is_verified)
        self.assertTrue(self.admin.notifications.filter(category='system').exists())

    def test_duplicate_username_rejected(self):
        make_user('dupvol', 'resident')
        resp = self.client.post('/api/volunteer-applications/', {
            'username': 'dupvol', 'password': '123456'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_short_password_rejected(self):
        resp = self.client.post('/api/volunteer-applications/', {
            'username': 'shortpw', 'password': '123'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_inactive_applicant_cannot_login(self):
        self.client.post('/api/volunteer-applications/', {
            'username': 'pendvol', 'password': '123456'}, format='json')
        resp = self.client.post('/api/auth/login/', {
            'username': 'pendvol', 'password': '123456'}, format='json')
        self.assertEqual(resp.status_code, 400)             # inactive → 登录失败

    def test_admin_approve_activates_and_verifies(self):
        self.client.post('/api/volunteer-applications/', {
            'username': 'okvol', 'password': '123456'}, format='json')
        from users.models import VolunteerApplication
        app = VolunteerApplication.objects.get(user__username='okvol')
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/volunteer-applications/%d/approve/' % app.id, {}, format='json')
        self.assertEqual(resp.status_code, 200)
        u = User.objects.get(username='okvol')
        self.assertTrue(u.is_active)
        self.assertTrue(u.profile.is_verified)
        app.refresh_from_db(); self.assertEqual(app.status, 'approved')
        # 通过后可登录
        self.client.force_authenticate(user=None)
        login = self.client.post('/api/auth/login/', {'username': 'okvol', 'password': '123456'}, format='json')
        self.assertEqual(login.status_code, 200)

    def test_reject_keeps_inactive(self):
        self.client.post('/api/volunteer-applications/', {
            'username': 'novol', 'password': '123456'}, format='json')
        from users.models import VolunteerApplication
        app = VolunteerApplication.objects.get(user__username='novol')
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/volunteer-applications/%d/reject/' % app.id,
                                {'note': '资料不全'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.get(username='novol').is_active)

    def test_non_admin_cannot_list_applications(self):
        res = make_user('va_res', 'resident')
        self.client.force_authenticate(res)
        self.assertEqual(self.client.get('/api/volunteer-applications/').status_code, 403)

    def test_admin_verify_toggle(self):
        vol = make_user('verifyvol', 'volunteer')
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/users/%d/verify/' % vol.id, {}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['is_verified'])
        vol.refresh_from_db(); self.assertTrue(vol.profile.is_verified)
