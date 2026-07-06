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
