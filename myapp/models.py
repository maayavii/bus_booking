from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

# User model
class User(AbstractUser):
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, blank=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.email

# BusCompany model
class BusCompany(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=50, unique=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    address = models.TextField()
    website = models.URLField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.company_name

# Stop model
class Stop(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['order']
        verbose_name_plural = "Stops"

    def __str__(self):
        return f"{self.name} (Order: {self.order})"

# BusRoute model
class BusRoute(models.Model):
    company = models.ForeignKey(BusCompany, on_delete=models.CASCADE)
    route_name = models.CharField(max_length=100)
    source = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='route_start')
    destination = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='route_end')
    total_distance = models.DecimalField(max_digits=6, decimal_places=2)
    base_fare_per_km = models.DecimalField(max_digits=5, decimal_places=2)
    route_type = models.CharField(
        max_length=50,
        choices=[('local', 'Local'), ('intercity', 'Intercity'), ('express', 'Express')]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    stops = models.ManyToManyField(Stop, through='RouteStop')

    def __str__(self):
        return f"{self.route_name} ({self.source} to {self.destination})"

# RouteStop model
class RouteStop(models.Model):
    bus_route = models.ForeignKey(BusRoute, on_delete=models.CASCADE)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    order = models.IntegerField()

    def __str__(self):
        return f"{self.stop.name} (Order: {self.order})"

    class Meta:
        unique_together = ('bus_route', 'stop', 'order')
        ordering = ['order']

    def clean(self):
        # Check if 'order' is None or less than 1
        if self.order is None or self.order < 1:
            raise ValidationError("Order must be a positive integer.")

# Bus model
class Bus(models.Model):
    AMENITIES = [
        ('AC', 'Air Conditioned'),
        ('NON_AC', 'Non Air Conditioned'),
        ('SLEEPER', 'Sleeper'),
        ('SEMI_SLEEPER', 'Semi Sleeper'),
        ('WIFI', 'WiFi Available'),
    ]

    route = models.ForeignKey('BusRoute', on_delete=models.CASCADE, related_name='buses')
    bus_number = models.CharField(max_length=20, unique=True)
    bus_model = models.CharField(max_length=50)
    total_seats = models.PositiveIntegerField()
    available_seats = models.PositiveIntegerField(default=0)
    amenities = models.JSONField(default=list)
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    departure_date = models.DateField()
    price_per_seat = models.DecimalField(max_digits=6, decimal_places=2, default=1)

    @property
    def available_seats_list(self):
        booked_seats = Book.objects.filter(bus=self, status=Book.BOOKED).values_list('seat_number', flat=True)
        return [seat for seat in range(1, self.total_seats + 1) if seat not in booked_seats]

    def save(self, *args, **kwargs):
        if not self.pk:  # On creation
            self.available_seats = self.total_seats
        super().save(*args, **kwargs)

    def __str__(self):
        return self.bus_number

# BusSchedule model
class BusSchedule(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=10, choices=[
        ('MONDAY', 'Monday'),
        ('TUESDAY', 'Tuesday'),
        ('WEDNESDAY', 'Wednesday'),
        ('THURSDAY', 'Thursday'),
        ('FRIDAY', 'Friday'),
        ('SATURDAY', 'Saturday'),
        ('SUNDAY', 'Sunday'),
    ])
    departure_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.bus.bus_number} - {self.day_of_week}"

# Book model
class Book(models.Model):
    BOOKED = 'B'
    CANCELLED = 'C'

    TICKET_STATUSES = [
        (BOOKED, 'Booked'),
        (CANCELLED, 'Cancelled'),
    ]

    status = models.CharField(max_length=20, choices=TICKET_STATUSES, default=BOOKED)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings", null=True)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="bookings", null=True)
    source = models.CharField(max_length=30)
    destination = models.CharField(max_length=30)
    price_per_seat = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    num_seats = models.PositiveIntegerField(null=True)
    price = models.DecimalField(decimal_places=2, max_digits=6)
    travel_date = models.DateField(null=True)
    travel_time = models.TimeField(null=True)
    seat_number = models.IntegerField()
    name = models.CharField(max_length=100, default="unknown")
    phone = models.CharField(max_length=15, default="not given")

    def __str__(self):
        return f"{self.user.email} - {self.bus.bus_number} - {self.status}"

    def save(self, *args, **kwargs):
        if self.num_seats and self.bus:
            self.price = self.num_seats * self.bus.price_per_seat
        super().save(*args, **kwargs)

    def cancel_seat(self):
        if self.status == self.BOOKED:
            self.status = self.CANCELLED
            self.bus.available_seats += 1
            self.bus.save()
            self.save()
