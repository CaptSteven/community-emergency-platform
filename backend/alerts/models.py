from django.db import models
from django.contrib.auth.models import User


class Warning(models.Model):
    WARNING_TYPE_CHOICES = (
        ('rainstorm', '暴雨'),
        ('fire', '火灾'),
        ('power_outage', '停电'),
        ('earthquake', '地震'),
        ('heat', '高温'),
        ('cold_wave', '寒潮'),
        ('flood', '内涝'),
        ('other', '其他'),
    )

    LEVEL_CHOICES = (
        ('blue', '蓝色预警'),
        ('yellow', '黄色预警'),
        ('orange', '橙色预警'),
        ('red', '红色预警'),
    )

    title = models.CharField(
        max_length=100,
        verbose_name='预警标题'
    )

    warning_type = models.CharField(
        max_length=30,
        choices=WARNING_TYPE_CHOICES,
        verbose_name='预警类型'
    )

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        verbose_name='预警等级'
    )

    content = models.TextField(
        verbose_name='预警内容'
    )

    community = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='影响社区'
    )

    publisher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='published_warnings',
        verbose_name='发布人'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='是否生效'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='发布时间'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )

    def __str__(self):
        return f'{self.title} - {self.get_level_display()}'

    class Meta:
        verbose_name = '灾害预警'
        verbose_name_plural = '灾害预警'
        ordering = ['-created_at']