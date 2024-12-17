from django.contrib import admin
from .models import *

# Register your models here.


admin.site.register(User)
admin.site.register(Book)
admin.site.register(Stop)
admin.site.register(BusRoute)
admin.site.register(RouteStop)
admin.site.register(Bus)
admin.site.register(BusCompany)




# Create an inline admin for RouteStop
class RouteStopInline(admin.TabularInline):  # You can also use StackedInline if you prefer a different layout
    model = RouteStop
    extra = 1  # Number of empty forms to show by default
    fields = ('stop', 'order')  # Fields to display

# Register the BusRoute admin with the inline
class BusRouteAdmin(admin.ModelAdmin):
    inlines = [RouteStopInline]
    list_display = ('route_name', 'source', 'destination', 'total_distance', 'base_fare_per_km', 'route_type')
