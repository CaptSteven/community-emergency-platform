from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from users.models import UserProfile


class WarningPermissionTests(APITestCase):
    def setUp(self):
        self.resident = User.objects.create_user(username='resident_test', password='123456')
        UserProfile.objects.create(user=self.resident, role='resident')

        self.admin = User.objects.create_user(username='admin_test', password='123456')
        UserProfile.objects.create(user=self.admin, role='admin')

        self.resident_token = Token.objects.create(user=self.resident)
        self.admin_token = Token.objects.create(user=self.admin)

    def test_resident_cannot_create_warning(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.resident_token.key)

        res = self.client.post('/api/warnings/', {
            'title': '测试预警',
            'warning_type': 'rainstorm',
            'level': 'blue',
            'content': '水磨沟社区暴雨预警，请注意防范内涝并减少外出',
            'community': '乌鲁木齐水磨沟社区',
            'is_active': True
        })

        self.assertEqual(res.status_code, 403)

    def test_admin_can_create_warning(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)

        res = self.client.post('/api/warnings/', {
            'title': '测试预警',
            'warning_type': 'rainstorm',
            'level': 'blue',
            'content': '水磨沟社区暴雨预警，请注意防范内涝并减少外出',
            'community': '乌鲁木齐水磨沟社区',
            'is_active': True
        })

        self.assertEqual(res.status_code, 201)