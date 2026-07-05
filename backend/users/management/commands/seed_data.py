from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

from users.models import UserProfile
from alerts.models import Warning
from resources.models import Shelter, Material


class Command(BaseCommand):
    help = '初始化演示数据'

    def create_user(self, username, password, role, phone='', community='阳光社区', address=''):
        user, created = User.objects.get_or_create(username=username)

        if created:
            user.set_password(password)
            user.save()

        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': role,
                'phone': phone,
                'community': community,
                'address': address,
                'is_available': True,
            }
        )

        profile.role = role
        profile.phone = phone
        profile.community = community
        profile.address = address
        profile.save()

        Token.objects.get_or_create(user=user)
        return user

    def handle(self, *args, **options):
        self.create_user('admin02', '123456', 'admin', '13800000001')
        self.create_user('resident02', '123456', 'resident', '13800000002', address='阳光社区1号楼')
        self.create_user('volunteer02', '123456', 'volunteer', '13800000003')

        Warning.objects.get_or_create(
            title='暴雨蓝色预警',
            defaults={
                'warning_type': 'rainstorm',
                'level': 'blue',
                'content': '预计未来数小时可能出现强降雨，请居民注意出行安全。',
                'community': '阳光社区',
                'is_active': True,
            }
        )

        Shelter.objects.get_or_create(
            name='阳光社区应急避难点',
            defaults={
                'address': '阳光社区广场',
                'capacity': 300,
                'contact_phone': '13800000000',
                'is_available': True,
            }
        )

        Material.objects.get_or_create(
            name='矿泉水',
            defaults={
                'category': '饮用水',
                'quantity': 100,
                'unit': '箱',
                'storage_location': '社区仓库A区',
                'warning_quantity': 20,
            }
        )

        self.stdout.write(self.style.SUCCESS('演示数据初始化完成'))