from django.db import models
from utils.base.fields import TrackingCodeField


class ModelText(models.Model):
    name = models.CharField(max_length=255)


class ModelTrackingCode(models.Model):
    code: str = TrackingCodeField(prefix="TEST", max_length=60)
