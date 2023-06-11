from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string


class ProjectApiKey(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    pub_key = models.CharField(max_length=64, blank=True)
    sec_key = models.CharField(max_length=255, blank=True)
    demo_sec = models.CharField(max_length=255, blank=True)

    # TODO: Update to user cache instead of demo_sec

    def __str__(self):
        return self.user.profile.fullname

    def check_password(self, sec_key):
        return check_password(sec_key, self.sec_key)

    class Meta:
        verbose_name = "Trip API key"


@receiver(post_save, sender=ProjectApiKey)
def create_project_api(sender, instance, created, **kwargs):
    if created:
        # Generate random pub_key and pass
        pub_key = get_random_string(64)
        pass_key = f"{get_random_string(6)}\
.{get_random_string(32)}.{get_random_string(16)}"

        instance.pub_key = pub_key
        instance.sec_key = make_password(pass_key)
        instance.demo_sec = pass_key

        instance.save()
