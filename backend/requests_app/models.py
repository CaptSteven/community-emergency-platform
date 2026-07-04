from django.db import models
from django.contrib.auth.models import User


class HelpRequest(models.Model):
    REQUEST_TYPE_CHOICES = (
        ('medical', '医疗求助'),
        ('material', '物资求助'),
        ('transfer', '转移求助'),
        ('trapped', '被困求助'),
        ('elderly', '老人求助'),
        ('child', '儿童求助'),
        ('fire', '火灾求助'),
        ('flood', '积水求助'),
        ('other', '其他求助'),
    )

    URGENCY_CHOICES = (
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '紧急'),
    )

    STATUS_CHOICES = (
        ('pending', '待处理'),
        ('assigned', '已分配'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    )

    resident = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='help_requests',
        verbose_name='求助居民'
    )

    request_type = models.CharField(
        max_length=30,
        choices=REQUEST_TYPE_CHOICES,
        verbose_name='求助类型'
    )

    urgency = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default='medium',
        verbose_name='紧急程度'
    )

    description = models.TextField(
        verbose_name='求助描述'
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='求助地址'
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name='纬度'
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name='经度'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='处理状态'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='完成时间'
    )

    def __str__(self):
        return f'{self.resident.username} - {self.get_request_type_display()} - {self.get_status_display()}'

    class Meta:
        verbose_name = '居民求助'
        verbose_name_plural = '居民求助'
        ordering = ['-created_at']