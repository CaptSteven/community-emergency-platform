from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from users.models import UserProfile
from .models import Notification


def make_user(username, role):
    user = User.objects.create_user(username=username, password='123456')
    UserProfile.objects.create(user=user, role=role)
    return user


class ReadStateOwnershipTests(APITestCase):
    """已读状态属于收件人本人：管理员浏览全量消息不得替他人清未读。"""

    def setUp(self):
        self.admin = make_user('nt_admin', 'admin')
        self.resident = make_user('nt_res', 'resident')
        self.n_res = Notification.objects.create(
            recipient=self.resident, title='给居民的', content='x', category='service')
        self.n_admin = Notification.objects.create(
            recipient=self.admin, title='给管理员的', content='x', category='system')

    def test_admin_cannot_mark_others_read(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f'/api/notifications/{self.n_res.id}/mark_read/')
        self.assertEqual(resp.status_code, 403)
        self.n_res.refresh_from_db()
        self.assertFalse(self.n_res.is_read)

    def test_mark_all_read_only_touches_own(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/notifications/mark_all_read/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)          # 只标了自己那 1 条
        self.n_res.refresh_from_db()
        self.n_admin.refresh_from_db()
        self.assertFalse(self.n_res.is_read)             # 居民未读保留
        self.assertTrue(self.n_admin.is_read)

    def test_recipient_marks_own_read(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.post(f'/api/notifications/{self.n_res.id}/mark_read/')
        self.assertEqual(resp.status_code, 200)
        self.n_res.refresh_from_db()
        self.assertTrue(self.n_res.is_read)

    def test_unread_count_scoped_to_self(self):
        self.client.force_authenticate(self.resident)
        resp = self.client.get('/api/notifications/unread_count/')
        self.assertEqual(resp.data['unread_count'], 1)
        # 管理员的角标也只统计自己的，而非全平台
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/notifications/unread_count/')
        self.assertEqual(resp.data['unread_count'], 1)
