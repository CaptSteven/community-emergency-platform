from django.db import models
from django.contrib.auth.models import User
from requests_app.models import HelpRequest


class VolunteerTask(models.Model):
    STATUS_CHOICES = (
        ('assigned', '已分配'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    )

    help_request = models.OneToOneField(
        HelpRequest,
        on_delete=models.CASCADE,
        related_name='volunteer_task',
        verbose_name='关联求助'
    )

    volunteer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='volunteer_tasks',
        verbose_name='志愿者'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='assigned',
        verbose_name='任务状态'
    )

    feedback = models.TextField(
        blank=True,
        null=True,
        verbose_name='处理反馈'
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='分配时间'
    )

    accepted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='接单时间'
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='完成时间'
    )

    def __str__(self):
        return f'任务 {self.id} - {self.get_status_display()}'

    class Meta:
        verbose_name = '志愿者任务'
        verbose_name_plural = '志愿者任务'
        ordering = ['-assigned_at']


class TaskCancellation(models.Model):
    REASON_CHOICES = (
        ('family', '家庭原因'),
        ('illness', '生病'),
        ('distance', '距离过远'),
        ('work', '工作冲突'),
        ('emergency', '突发状况'),
        ('other', '其他'),
    )

    volunteer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='task_cancellations', verbose_name='志愿者'
    )
    task = models.ForeignKey(
        VolunteerTask, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cancellations', verbose_name='任务'
    )
    help_request = models.ForeignKey(
        HelpRequest, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联求助'
    )
    visit = models.ForeignKey(
        'services.ServiceVisit', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cancellations', verbose_name='上门服务工单'
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='other', verbose_name='取消原因')
    note = models.TextField(blank=True, default='', verbose_name='补充说明')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='取消时间')

    class Meta:
        verbose_name = '任务取消记录'
        verbose_name_plural = '任务取消记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.volunteer_id} 取消任务 {self.task_id} - {self.get_reason_display()}'
