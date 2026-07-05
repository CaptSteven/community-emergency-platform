from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('resident', '居民'),
        ('volunteer', '志愿者'),
        ('admin', '管理员'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='用户'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name='用户角色'
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='联系电话'
    )

    community = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='所属社区'
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='详细地址'
    )

    current_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name='当前纬度'
    )

    current_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name='当前经度'
    )

    location_updated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='位置更新时间'
    )

    skills = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='擅长任务'
    )

    is_available = models.BooleanField(
        default=True,
        verbose_name='是否空闲'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )

    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'

    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'