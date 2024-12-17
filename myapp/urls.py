from django.urls import path
from . import views

app_name = 'myapp'

from django.urls import path
from . import views

app_name = 'myapp'

urlpatterns = [
    path('', views.home, name="home"),
    path('findbus', views.findbus, name="findbus"),
    path('bookings', views.bookings, name="bookings"),
    path('cancellings', views.cancellings, name="cancellings"),
    path('seebookings', views.seebookings, name="seebookings"),
    path('signup', views.signup, name="signup"),
    path('signin', views.signin, name="signin"),
    path('success', views.success, name="success"),
    path('signout', views.signout, name="signout"),
    path('register/', views.bus_company_register, name='register'),
    path('dashboard/', views.bus_company_dashboard, name='dashboard'),  # Keep only one definition
    path('add_route/', views.add_bus_route, name='add_route'),
    path('add_bus/', views.add_bus, name='add_bus'),
    path('bus/<int:bus_id>/add_schedule/', views.add_bus_schedule, name='add_schedule'),  # Keep this definition for add_schedule
    path('edit_route/<int:route_id>/', views.edit_bus_route, name='edit_route'),
    path('booklists', views.booklist, name="booklists"),
    path('book/<int:bus_id>/', views.book_seats, name='book_seats'),
    path('accounts/login/', views.signin, name='login'),
    path('success/', views.booking_success, name='booking_success'), 
    path('cancel/', views.cancellings, name='cancellings'),
    path('cancellings/', views.cancellings, name='cancellings')

]



