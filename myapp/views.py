from django.shortcuts import render
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
# Create your views here.
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from .models import User, Bus, Book,RouteStop
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import UserLoginForm, UserRegisterForm
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.db import IntegrityError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import BusCompany, BusRoute,Stop
from .forms import BusRouteForm
from myapp.models import BusRoute 
from myapp.forms import BusRouteForm, StopForm
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from myapp.forms import BusRouteForm
from myapp.models import BusRoute, Stop, RouteStop
from django.contrib.auth.decorators import login_required

# OR for custom user models
from django.contrib.auth import get_user_model
User = get_user_model()
def home(request):
    if request.user.is_authenticated:
        return render(request, 'myapp/home.html')
    else:
        return render(request, 'myapp/signin.html')


@login_required(login_url='signin')
def findbus(request):
    context = {}

    if request.method == 'POST':
        source = request.POST.get('source')
        destination = request.POST.get('destination')
        departure_date = request.POST.get('departure_date')

        try:
            # Find routes where both source and destination exist as stops
            routes = BusRoute.objects.filter(
                routestop__stop__name=source
            ).filter(
                routestop__stop__name=destination
            ).distinct()

            # Filter routes where the source appears before the destination in the stop order
            valid_routes = []
            for route in routes:
                # Get route stops ordered by their order
                route_stops = RouteStop.objects.filter(bus_route=route).order_by('order')
                
                # Extract stop names in order
                stop_names = [route_stop.stop.name for route_stop in route_stops]

                if source in stop_names and destination in stop_names:
                    source_index = stop_names.index(source)
                    destination_index = stop_names.index(destination)

                    if source_index < destination_index:  # Ensure source comes before destination
                        valid_routes.append(route)

            # Find buses that use the valid routes and match the departure date
            bus_list = Bus.objects.filter(
                route__in=valid_routes,
                departure_date=departure_date
            )

            if bus_list.exists():
                # Pass the selected source, destination, and date to the template
                return render(request, 'myapp/list.html', {
                    'bus_list': bus_list,
                    'source': source,
                    'destination': destination,
                    'departure_date': departure_date,
                })
            else:
                # No buses found
                context["error"] = "Sorry, no buses available for the selected criteria."

        except Exception as e:
            # Handle any exceptions that occur
            context["error"] = f"An error occurred: {str(e)}"
            import traceback
            traceback.print_exc()

    # For both GET and POST, pass unique sources and destinations for the dropdowns
    # Use the source and destination from BusRoute directly
    context['sources'] = Stop.objects.filter(route_start__isnull=False).values_list('name', flat=True).distinct()
    context['destinations'] = Stop.objects.filter(route_end__isnull=False).values_list('name', flat=True).distinct()

    return render(request, 'myapp/findbus.html', context)

@login_required(login_url='signin')
def bookings(request):
    context = {}
    if request.method == 'POST':
        id_r = request.POST.get('bus_id')
       
        seats_r = int(request.POST.get('no_seats'))
        bus = Bus.objects.get(id=id_r)
        if bus:
            if bus.rem > int(seats_r):
                name_r = bus.bus_name
                cost = int(seats_r) * bus.price
                source_r = bus.source
                dest_r = bus.dest
                num_seats = Decimal(bus.num_seats)
                price_r = bus.price
                date_r = bus.date
                time_r = bus.time
                username_r = request.user.username
                email_r = request.user.email
                userid_r = request.user.id
                rem_r = bus.rem - seats_r
                Bus.objects.filter(id=id_r).update(rem=rem_r)
                book = Book.objects.create(name=username_r, email=email_r, userid=userid_r, bus_name=name_r,
                                           source=source_r, busid=id_r,
                                           dest=dest_r, price=price_r, num_seats=seats_r, date=date_r, time=time_r,
                                           status='BOOKED')
                print('------------book id-----------', book.id)
                # book.save()
                return render(request, 'myapp/bookings.html', locals())
            else:
                context["error"] = "Sorry select fewer number of seats"
                return render(request, 'myapp/findbus.html', context)

    else:
        return render(request, 'myapp/findbus.html')



from django.shortcuts import render
from .models import Book, Bus

@login_required(login_url='signin')
def cancellings(request):
    context = {}
    if request.method == 'POST':
        bus_id = request.POST.get('bus_id')

        # Check if bus_id is empty or not a valid integer
        if not bus_id:
            context["error"] = "Please enter a valid Booking ID"
            return render(request, 'myapp/cancellation.html', context)

        try:
            # Convert bus_id to integer
            bus_id = int(bus_id)

            # Try to find the booking using user_id instead of id
            try:
                booking = Book.objects.get(id=bus_id, user_id=request.user.user_id)

                # Check if booking is already cancelled
                if booking.status == 'CANCELLED':
                    context["error"] = "This booking is already cancelled"
                    return render(request, 'myapp/cancellation.html', context)

                # Update bus availability
                bus = Bus.objects.get(id=booking.bus_id)
                bus.available_seats += booking.num_seats
                bus.save()

                # Cancel the booking
                booking.status = 'CANCELLED'
                booking.save()

                context["success"] = "Booking successfully cancelled"
                return render(request, 'myapp/cancellation.html', context)

            except Book.DoesNotExist:
                context["error"] = "No booking found with this ID for your account"
                return render(request, 'myapp/cancellation.html', context)

        except ValueError:
            context["error"] = "Invalid Booking ID. Please enter a valid number"
            return render(request, 'myapp/cancellation.html', context)

    return render(request, 'myapp/cancellation.html', context)

@login_required(login_url='signin')
def seebookings(request):
    """
    View to display user's current bookings with options to cancel tickets
    """
    user_id = request.user.user_id
    book_list = Book.objects.filter(user_id=user_id, status=Book.BOOKED).select_related('bus')
    
    if book_list.exists():
        context = {
            'book_list': book_list,
        }
        return render(request, 'myapp/bookings.html', context)
    else:
        context = {
            "error": "Sorry, no buses booked",
            "show_find_bus": True  # Add a flag to show a link to find buses
        }
        return render(request, 'myapp/findbus.html', context)



def signup(request):
    context = {}
    if request.method == 'POST':
        name_r = request.POST.get('name')
        email_r = request.POST.get('email')
        password_r = request.POST.get('password')

        # Validate inputs
        if not name_r or not email_r or not password_r:
            context["error"] = "All fields are required."
            return render(request, 'myapp/signup.html', context)
        
        # Check for duplicate username
        if User.objects.filter(username=name_r).exists():
            context["error"] = "Username already exists. Please choose another."
            return render(request, 'myapp/signup.html', context)
        
        # Check for duplicate email (if required)
        if User.objects.filter(email=email_r).exists():
            context["error"] = "Email is already associated with another account."
            return render(request, 'myapp/signup.html', context)
        
        try:
            # Create the user
            user = User.objects.create_user(username=name_r, email=email_r, password=password_r)
            
            # Log in the user
            login(request, user)
            return render(request, 'myapp/thank.html')
        except IntegrityError:
            context["error"] = "An error occurred. Please try again."
            return render(request, 'myapp/signup.html', context)
    else:
        return render(request, 'myapp/signup.html', context)


def signin(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        # Use Django's built-in authentication
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('myapp:dashboard')  # Adjust to your dashboard URL name
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'myapp/signin.html')


def signout(request):
    context = {}
    logout(request)
    context['error'] = "You have been logged out"
    return render(request, 'myapp/signin.html', context)


def success(request):
    context = {}
    context['user'] = request.user
    return render(request, 'myapp/success.html', context)
from django.contrib import messages
from .models import BusCompany, BusRoute, Bus, BusSchedule
from .forms import BusCompanyRegistrationForm, BusRouteForm, BusForm, BusScheduleForm
@login_required
def bus_company_register(request):
    # Find the corresponding custom User instance
    try:
        custom_user = User.objects.get(username=request.user.username)
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('myapp:dashboard')

    if request.method == 'POST':
        form = BusCompanyRegistrationForm(request.POST)
        if form.is_valid():
            # Check if company already exists
            existing_company = BusCompany.objects.filter(user=custom_user).exists()
            if existing_company:
                messages.error(request, "You have already registered a bus company.")
                return redirect('myapp:dashboard')
           
            # Create bus company
            bus_company = form.save(commit=False)
            bus_company.user = custom_user
            bus_company.is_verified = False  # Admin will verify
            bus_company.save()
           
            messages.success(request, "Your company registration is submitted for verification.")
            return redirect('myapp:dashboard')
    else:
        form = BusCompanyRegistrationForm()
    return render(request, 'myapp/register.html', {'form': form})
    
    return render(request, 'myapp/register.html', {'form': form})

@login_required
def bus_company_dashboard(request):
    """
    Dashboard for bus companies to manage their routes, buses, and schedules
    """
    try:
        bus_company = BusCompany.objects.get(user=request.user)
    except BusCompany.DoesNotExist:
        messages.warning(request, "Please register your bus company first.")
        return redirect('myapp/register.html')
    
    routes = BusRoute.objects.filter(company=bus_company)
    buses = Bus.objects.filter(route__company=bus_company)
    
    context = {
        'bus_company': bus_company,
        'routes': routes,
        'buses': buses,
    }
    return render(request, 'myapp/dashboard.html', context)


@login_required
def add_bus_route(request):
    if request.method == 'POST':
        form = BusRouteForm(request.POST, user=request.user)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save the bus route (source, destination, and company are set in the form)
                    bus_route = form.save()

                    # Process dynamic stops
                    stop_names = request.POST.getlist('stops[]stop_name')
                    stop_orders = request.POST.getlist('stops[]order')

                    # Validate stops
                    if len(stop_names) != len(stop_orders):
                        raise ValidationError("Mismatch between stop names and orders")

                    for stop_name, stop_order in zip(stop_names, stop_orders):
                        stop_name = stop_name.strip()
                        stop_order = stop_order.strip()

                        # Skip empty stops
                        if not stop_name or not stop_order:
                            continue

                        # Safely handle stop creation
                        try:
                            stop, _ = Stop.objects.get_or_create(name=stop_name)
                            
                            RouteStop.objects.create(
                                bus_route=bus_route, 
                                stop=stop, 
                                order=int(stop_order)
                            )
                        except Exception as stop_error:
                            messages.error(request, f"Error processing stop {stop_name}: {stop_error}")
                    
                    messages.success(request, f"Bus route '{bus_route.route_name}' added successfully.")
                    return redirect('myapp:dashboard')
            
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        # GET request - initialize the form
        form = BusRouteForm(user=request.user)
    
    # Get all existing stops for autocomplete
    all_stops = Stop.objects.values_list('name', flat=True)
    
    context = {
        'form': form,
        'all_stops': list(all_stops)
    }
    return render(request, 'myapp/add_route.html', context)


@login_required
def add_bus(request):
    """
    View to add a new bus to a route
    """
    try:
        # Check if the user has a bus company
        bus_company = BusCompany.objects.get(user=request.user)
    except BusCompany.DoesNotExist:
        messages.warning(request, "Please register your bus company first.")
        return redirect('register')  # Redirect to the named URL for registration

    # Get routes owned by this company
    routes = BusRoute.objects.filter(company=bus_company)

    if request.method == 'POST':
        form = BusForm(request.POST, routes=routes)
        if form.is_valid():
            form.save()
            messages.success(request, "Bus added successfully.")
            return redirect('myapp:dashboard')  # Redirect to the named URL for the dashboard
    else:
        form = BusForm(routes=routes)

    return render(request, 'myapp/add_bus.html', {'form': form, 'routes': routes})


@login_required
def add_bus_schedule(request, bus_id):
    """
    View to add schedules for a specific bus
    """
    bus = get_object_or_404(Bus, id=bus_id, route__company__user=request.user)
    
    if request.method == 'POST':
        form = BusScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.bus = bus
            schedule.save()
            
            messages.success(request, "Bus schedule added successfully.")
            return redirect('myapp/dashboard.html')
    else:
        form = BusScheduleForm()
    
    return render(request, 'myapp/add_schedule.html', {'form': form, 'bus': bus})



@login_required
def edit_bus_route(request, route_id):
    """
    View to edit an existing bus route
    """
    route = get_object_or_404(BusRoute, id=route_id, company__user=request.user)
    
    if request.method == 'POST':
        form = BusRouteForm(request.POST, instance=route)
        if form.is_valid():
            form.save()
            messages.success(request, "Route updated successfully.")
            return redirect('myapp/dashboard.html')
    else:
        form = BusRouteForm(instance=route)
    
    return render(request, 'myapp/edit_route.html', {'form': form, 'route': route})
@login_required
def dashboard(request):
    """
    View to render the dashboard page for logged-in users.
    """
    return render(request, 'myapp/dashboard.html')

from django.shortcuts import render
from .models import Book

@login_required(login_url='signin')
def booklist(request):
    """
    View to display the list of buses booked by the user.
    """
    user_id = request.user.user_id  # Use the custom user_id field
    book_list = Book.objects.filter(user_id=user_id)  # Filter using the user_id

    if book_list.exists():
        return render(request, 'myapp/booklist.html', {'book_list': book_list})
    else:
        context = {"error": "Sorry, no buses booked."}
        return render(request, 'myapp/findbus.html', context)
    
@login_required(login_url='signin')
def book_seats(request, bus_id):
    try:
        bus = Bus.objects.get(id=bus_id)
    except Bus.DoesNotExist:
        messages.error(request, "Bus not found.")
        return redirect('some_error_page')

    # Get list of all seat numbers
    all_seats = list(range(1, bus.total_seats + 1))

    # Get booked seats
    booked_seats = Book.objects.filter(bus=bus, status=Book.BOOKED).values_list('seat_number', flat=True)

    # Calculate available seats by excluding booked ones
    available_seats = [seat for seat in all_seats if seat not in booked_seats]

    if request.method == 'POST':
        # Process form submission
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        pickup = request.POST.get('pickup')
        drop_location = request.POST.get('drop')

        # Get selected seats from the form
        selected_seats = request.POST.getlist('seats')

        # Check if selected seats are available
        for seat in selected_seats:
            seat = int(seat)
            if seat in booked_seats:
                # If seat is already booked, handle cancellation
                existing_booking = Book.objects.filter(bus=bus, seat_number=seat, status=Book.BOOKED).first()
                if existing_booking and existing_booking.user == request.user:
                    # If booked by the same user, cancel the booking
                    existing_booking.status = Book.CANCELLED
                    existing_booking.save()

                    # Increase the available seats
                    bus.available_seats += 1
                    bus.save()

                    messages.info(request, f"Seat {seat} booking has been canceled.")
                else:
                    messages.error(request, f"Seat {seat} has already been booked by another user.")
                    return render(request, 'myapp/book_seats.html', {
                        'bus': bus,
                        'available_seats': available_seats,
                        'booked_seats': booked_seats,
                        'seats': list(range(1, bus.total_seats + 1))
                    })
            elif seat not in available_seats:
                messages.error(request, f"Seat {seat} is no longer available.")
                return render(request, 'myapp/book_seats.html', {
                    'bus': bus,
                    'available_seats': available_seats,
                    'booked_seats': booked_seats,
                    'seats': list(range(1, bus.total_seats + 1))
                })

        # Calculate the total price based on number of seats
        total_price_per_seat = bus.route.base_fare_per_km * bus.route.total_distance
        total_price = total_price_per_seat * len(selected_seats)

        # Create the bookings
        try:
            bookings = []
            for seat in selected_seats:
                seat = int(seat)
                booking = Book.objects.create(
                    user=request.user,
                    bus=bus,
                    source=bus.route.source,
                    destination=bus.route.destination,
                    seat_number=seat,
                    status=Book.BOOKED,
                    num_seats=len(selected_seats),
                    price=total_price_per_seat,
                    travel_date=bus.departure_date,
                    travel_time=bus.departure_time,
                    name=name,
                    phone=phone
                )
                bookings.append(booking)

            # Update available seats after booking
            bus.available_seats = bus.total_seats - len(bookings)
            bus.save()

            messages.success(request, f"Successfully booked {len(bookings)} seat(s).")
            return redirect('myapp:booklists')

        except Exception as e:
            # Rollback if an error occurs
            for booking in bookings:
                booking.delete()
            messages.error(request, f"Booking failed: {str(e)}")
            return render(request, 'myapp/book_seats.html', {
                'bus': bus,
                'available_seats': available_seats,
                'booked_seats': booked_seats,
                'seats': list(range(1, bus.total_seats + 1))
            })

    # Render the booking page with the available and booked seats
    return render(request, 'myapp/book_seats.html', {
        'bus': bus,
        'available_seats': available_seats,
        'booked_seats': booked_seats,
        'seats': list(range(1, bus.total_seats + 1)),
        'booked_seats_list': booked_seats  # Pass booked seats to the template
    })


from django.shortcuts import render

def booking_success(request):
    return render(request, 'booking_success')
