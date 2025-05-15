from django.db import models

class FuelPrice(models.Model):
    opis_id = models.CharField(max_length=100)
    truckstop_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    rack_id = models.CharField(max_length=100)
    retail_price = models.FloatField()
    lat = models.FloatField()
    lon = models.FloatField()
