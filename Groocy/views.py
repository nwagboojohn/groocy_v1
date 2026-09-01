import requests, json, random, secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from .models import Product, Order, OrderItem, Profile, Category, DeliveryRating, CourierProfile
from .forms import StudentSignUpForm, ProductForm, CourierSignUpForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .utils import send_groocy_email
from django.utils import timezone
from django.utils.dateformat import time_format
from django.utils.timezone import now
from django.utils.text import slugify
from datetime import timedelta
from django.db.models.functions import TruncDay, TruncWeek, TruncHour, TruncMonth
from django.db import transaction, models
from django.db.models import Sum, F, Count, Q
from decimal import Decimal

# --- STUDENT VIEWS ---  
def signup_view(request):
    if request.method == 'POST':
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            # 1. Save but don't commit to DB yet
            user = form.save(commit=False)
            # 2. Hash the password (CRITICAL STEP)
            user.set_password(form.cleaned_data['password'])
            # 3. Save to DB
            user.save()
            # Send Welcome Email
            try:
                send_groocy_email(
                    user.email,
                    "Welcome to the fast lane 🚀",
                    "emails/welcome_user.html",
                    {'username': user.username}
                )
            except Exception as e:
                print(f"Email Error: {e}")

            # 4. Log the user in immediately
            # login(request, user)
            # 5. Redirect using the NAME from urls.py
            return redirect('login')
        else:
            # If invalid, we re-render the page WITH the form (to show errors)
            return render(request, 'registration/signup.html', {'form': form})
    
    # If GET request
    form = StudentSignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        # Match the 'name' attributes from your HTML exactly
        username = request.POST.get('username')
        password = request.POST.get('password') # Ensure your HTML uses name="password"

        # Check if user exists and password is correct
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Check if this specific user has a registered Customer Profile
            has_customer_profile = Profile.objects.filter(user=user).exists()

            if has_customer_profile:
                # All clear! Log them in and redirect
                login(request, user)
                return redirect('home') 
            else:
                # Authenticated as a user, but NOT a customer (e.g., they are a courier)
                messages.error(request, "This account is not a registered customer account.")
        else:
            # Invalid credentials entirely
            messages.error(request, "Invalid email or password.")

    # If it's a GET request, just show the page
    return render(request, 'registration/login.html')


# Send OTP to Email
def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = User.objects.filter(email=email).first()

        if user:
            # Generate a random 6-digit number
            otp = str(random.randint(100000, 999999))
            
            # Store OTP and Email in session for 5 minutes
            request.session['reset_otp'] = otp
            request.session['reset_email'] = email
            request.session['otp_created_at'] = timezone.now().timestamp()
            
            # Send the OTP via your existing email function
            try:
                send_groocy_email(
                    email,
                    f"{otp} is your Groocy reset code",
                    "emails/otp_email.html",
                    {'otp': otp, 'username': user.username}
                )
                messages.success(request, "OTP sent to email! It expires in 5 minutes.")
                return redirect('password_reset_otp_verify')
            except Exception as e:
                messages.error(request, "Error sending email. Try again.")
        else:
            messages.error(request, "No account found with that email.")
            
    return render(request, 'registration/password_reset.html')

# Verify OTP and Update Password
def password_reset_otp_verify(request):
    if request.method == 'POST':
        input_otp = request.POST.get('otp')
        new_password = request.POST.get('password')
        
        # Get data from session
        session_otp = request.session.get('reset_otp')
        session_email = request.session.get('reset_email')
        otp_time = request.session.get('otp_created_at')

        # Check if OTP exists in session
        if not session_otp or not otp_time:
            messages.error(request, "Session expired. Please request a new code.")
            return redirect('password_reset')

        # 2. Check if 300 seconds have passed
        now = timezone.now().timestamp()
        if now - otp_time > 300:
            # Clean up the expired session data
            del request.session['reset_otp']
            del request.session['reset_email']
            del request.session['otp_created_at']
            messages.error(request, "The code has expired (5 mins). Please try again.")
            return redirect('password_reset')
        
        # Check if OTP is correct
        if input_otp == session_otp:
            user = User.objects.get(email=session_email)
            user.set_password(new_password)
            user.save()
            
            # Success! Clear session
            request.session.flush() 
            messages.success(request, "Password updated! You can now login.")
            return redirect('login')
        else:
            messages.error(request, "Invalid OTP. Please check your email again.")

    return render(request, 'registration/password_reset_otp.html')


def logout_view(request):
    if request.user.is_authenticated:
        user_email = request.user.email
        user_name = request.user.username
        
        # Send Email FIRST before destroying the session
        if user_email:
            try:
                send_groocy_email(
                    user_email,
                    "See you soon 👋",
                    "emails/logout_user.html",
                    {'username': user_name}
                )
            except Exception as e:
                print(f"Logout Email Error: {e}")

        logout(request)
        messages.info(request, "You logged out successfully!")
    return redirect('login')

from django.contrib.auth.models import User


def landing(request):
    # Fetch all products for the grid
    products = Product.objects.all()
    return render(request, 'shop/index.html', {'products': products})

@login_required
def home(request):
    if request.user.is_authenticated:
        # REDIRECT LOGIC: Check if this user has an active order
        active_order = Order.objects.filter(
            user=request.user, 
            status__in=['Accepted', 'Packing', 'Transit']
        ).first()

        if active_order:
            return redirect('track_order', ref=active_order.ref)

    # Fetch all products for the grid
    products = Product.objects.all()
    categories = Category.objects.all() # Fetch all dynamic categories

    # Stock alert
    low_stock = Product.objects.filter(instock__range=(1, 9))
    out_of_stock_items = Product.objects.filter(instock=0)

    return render(request, 'shop/home.html', {
        'products': products,
        'categories': categories,
        'low_stock_items': low_stock,
        'low_stock_count': low_stock.count(),
        'out_of_stock_items': out_of_stock_items,
        'out_of_stock_count': out_of_stock_items.count(),
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY
    })


@login_required
def orders_view(request):
    # Show orders belonging only to the logged-in student
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'shop/orders.html', {'orders': orders})

@login_required
def order_detail(request, ref):
    # Fetch the order by its reference, or return a 404 error if not found
    order = get_object_or_404(Order, ref=ref, user=request.user)
    
    # If you have an OrderItem model linked to Order, they will show up here
    return render(request, 'shop/order_detail.html', {'order': order})

@login_required
def profile_view(request):
    # Get all orders for this specific user
    user_orders = Order.objects.filter(user=request.user, verified=True)

    # Calculate total spent (Summing the 'amount' column)
    total_spent = user_orders.aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'orders': user_orders,
        'total_spent': total_spent,
    }
    return render(request, 'shop/profile.html', context)


@login_required
def update_address(request):
    if request.method == "POST":
        address = request.POST.get('address')
        profile, created = Profile.objects.get_or_create(user=request.user)
        profile.address = address
        profile.save()
        return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        # Update User fields
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        # Update Address only if it's in the POST data
        address = request.POST.get('address')
        if address: # Prevents overwriting with None/Empty if only updating username
            profile, created = Profile.objects.get_or_create(user=request.user)
            profile.address = address
            profile.save()
        
        messages.success(request, "Profile updated successfully!")
    return redirect('profile')


@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user

        # Log out the user to cleanly terminate the active session before deletion
        logout(request)
        
        # Optional: Scramble profile data if you need to respect privacy request
        user.username = f"deleted_user_{user.id}"
        user.email = f"deleted_{user.id}@groocy.local"
        user.save()
        
        # Display a status notification on the landing interface
        messages.success(request, "Your account has been deleted successfully.")
        
        # Redirect user back to registration pipeline
        return redirect('/')
    
    return redirect('profile')


@login_required
@require_POST
def delete_courier_account(request):
    user = request.user
    
    # Step 1: Soft-delete the main user profile to instantly block auth access
    user.is_active = False
    user.save()
    
    # Step 2: Update courier-specific flags so they drop from active queues
    if hasattr(user, 'courier_profile'):
        profile = user.courier_profile
        profile.is_available = False
        profile.is_deleted = True
        profile.save()
        
    # Step 3: Clear the user's active session logs
    logout(request)
    
    # Step 4: Show status toast message on landing page
    messages.success(request, "Your account has been deleted successfully.")
    return redirect('/')


# Function for the Sync View (Django)
def sync_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_cart = data.get('cart', [])
        
        # Convert list to dictionary format for your existing verify_payment logic
        session_cart = {}
        for item in user_cart:
            session_cart[str(item['id'])] = {
                'name': item['name'],
                'price': item['price'],
                'quantity': item['quantity'],
                'image': item.get('image')
            }
        
        request.session['cart'] = session_cart
        request.session.modified = True
        return JsonResponse({'status': 'synced'})


# --- PAYMENT LOGIC ---
@login_required
def verify_payment(request, ref):
    # 1. Duplicate Check
    existing_order = Order.objects.filter(ref=ref).first()
    if existing_order:
        return render(request, 'shop/track_order.html', {'ref': ref, 'order': existing_order})

    url = f"https://api.paystack.co/transaction/verify/{ref}"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get('status') and data.get('data', {}).get('status') == 'success':
            # 1. Get the CURRENT address from the profile to "snapshot" it
            current_address = "No address provided"
            if hasattr(request.user, 'profile') and request.user.profile.address:
                current_address = request.user.profile.address

            amount_paid_kobo = data['data']['amount']
            naira_amount = amount_paid_kobo / 100
            
            # Calculate shipping based on the same logic used in JS
            if naira_amount >= 10000: # Subtotal > 10k
                fee = 500
            elif naira_amount >= 2500: # Subtotal > 2.5k
                fee = 300
            else:
                fee = 200

            # 2. CREATE ORDER ITEMS FIRST
            # Note: Ensure your JS is actually populating the Django session 'cart'
            cart_data = request.session.get('cart', {}) 
            if not cart_data:
                return render(request, 'shop/payment_error.html', {'error_message': 'Your cart session expired.'})
            
            # Create the Order object
            # Wrap database modifications in an atomic transaction
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    address=current_address, # Snapshots the address at time of purchase. This "freezes" the address for this specific order
                    amount=naira_amount,
                    shipping_fee=fee, # Saves the fee separately
                    ref=ref,
                    status='Accepted', 
                    verified=True,
                )

            for item_id, item in cart_data.items():
                # Create the item record
                OrderItem.objects.create(
                    order=order,
                    product_name=item['name'],
                    product_image=item.get('image'),
                    price=item['price'],
                    quantity=item['quantity'],
                    unit_type=item.get('unit_type', 'piece')
                )

                # 3. SUBTRACT STOCK IMMEDIATELY
                # We find the product and subtract the quantity
                Product.objects.filter(name=item['name']).update(instock=F('instock') - item['quantity'])

            # 4. Clear the cart safely inside the transaction block
            request.session['cart'] = {}
            request.session.modified = True 

            # Return success page
            # views.py snippet
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return JsonResponse({'status': 'created', 'ref': ref})
            else:
                return render(request, 'shop/track_order.html', {'order': order})

        else:
            return render(request, 'shop/payment_error.html', {'error_message': str(e)})

    except Exception as e:
        return render(request, 'shop/payment_error.html', {'error_message': str(e)})


# Successful payment redirect
def payment_success_view(request):
    order_ref = request.GET.get('ref')
    order = None

    # Fetch the order if the ref exists
    if order_ref:
        order = get_object_or_404(Order, ref=order_ref)
    
    # CRITICAL: Pass the instance wrapped in a context dictionary
    context = {
        'order': order
    }

    # Pass the order into the template context
    return render(request, 'shop/payment_success.html', context)

# Failed payment redirect
def payment_error_view(request):
    # If the URL is ?error=Order was cancelled, this will display it
    error_messsage = request.GET.get('error', "Something went wrong with your transaction.")
    return render(request, 'shop/payment_error.html', {'error_message': error_messsage})


@login_required
@transaction.atomic
def create_pod_order(request):
    # 1. Pull cart from session
    cart_data = request.session.get('cart', {})
    if not cart_data:
        return JsonResponse({'success': False, 'error': 'Your cart is empty.'}, status=400)

    # 2. Snapshot Address & Calculate Totals
    # We use the same logic as your verify_payment to keep fees consistent
    current_address = "No address provided"
    if hasattr(request.user, 'profile') and request.user.profile.address:
        current_address = request.user.profile.address

    subtotal = sum(float(item['price']) * int(item['quantity']) for item in cart_data.values())
    
    # Matching your fee logic: >10k=500, >2.5k=300, else 200
    if subtotal >= 10000:
        fee = 500
    elif subtotal >= 2500:
        fee = 300
    else:
        fee = 200

    # 3. Create the Order
    # verified=False because they haven't paid yet
    ref = f"POD-{secrets.token_hex(4).upper()}"
    order = Order.objects.create(
        user=request.user,
        ref=ref,
        address=current_address,
        amount=subtotal,
        shipping_fee=fee,
        payment_method='POD',
        status='Ready',
        verified=False 
    )

    # 4. Create Items & Subtract Stock
    for item_id, item in cart_data.items():
        # Create record
        OrderItem.objects.create(
            order=order,
            product_name=item['name'],
            product_image=item.get('image'),
            price=item['price'],
            quantity=item['quantity']
        )

        # Atomic Stock Update
        Product.objects.filter(name=item['name']).update(
            instock=F('instock') - item['quantity']
        )

    # 5. Cleanup
    request.session['cart'] = {}
    request.session.modified = True

    return JsonResponse({
        'success': True, 
        'ref': ref,
        'message': 'Order placed successfully!'
    })

    
# --- STAFF / ADMIN VIEWS ---

@staff_member_required
def admin_dashboard(request):
    # Capture the requested timeframe, defaulting to last_week
    timeframe = request.GET.get('timeframe', 'last_week')
    now = timezone.now()

    # 1. Base Querysets
    verified_orders = Order.objects.filter(verified=True)
    users = User.objects.filter(is_staff=False)
    categories = Category.objects.all()
    products = Product.objects.all()
    
    # Stock alerts (Unaffected by date filters)
    low_stock = Product.objects.filter(instock__range=(1, 9))
    out_of_stock_items = Product.objects.filter(instock=0)

    # 2. Dynamic Filtering Logic
    # Set default chart groupings for 'last_week'
    chart_trunc = TruncDay('created_at')
    chart_format = '%a'  # e.g., 'Mon', 'Tue'

    if timeframe == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        verified_orders = verified_orders.filter(created_at__gte=start_date)
        users = users.filter(date_joined__gte=start_date)
        # Group chart by hour for today's view
        chart_trunc = TruncHour('created_at')
        chart_format = '%H:00'
        
    elif timeframe == 'last_week':
        start_date = now - timedelta(days=7)
        verified_orders = verified_orders.filter(created_at__gte=start_date)
        users = users.filter(date_joined__gte=start_date)
        
    elif timeframe == 'last_month':
        start_date = now - timedelta(days=30)
        verified_orders = verified_orders.filter(created_at__gte=start_date)
        users = users.filter(date_joined__gte=start_date)
        # Group chart by day, but show date
        chart_trunc = TruncDay('created_at')
        chart_format = '%b %d'  # e.g., 'Jan 05'
        
    elif timeframe == 'last_year':
        start_date = now - timedelta(days=365)
        verified_orders = verified_orders.filter(created_at__gte=start_date)
        users = users.filter(date_joined__gte=start_date)
        # Group chart by month for yearly view
        chart_trunc = TruncMonth('created_at')
        chart_format = '%b %Y'  # e.g., 'Jan 2026'
        
    elif timeframe == 'all':
        # No date filtering applied to querysets
        chart_trunc = TruncMonth('created_at')
        chart_format = '%b %Y'

    # 3. Apply Dynamic Chart Logic
    chart_data = verified_orders.annotate(period=chart_trunc)\
        .values('period').annotate(total=Sum('amount')).order_by('period')

    # 4. Context Payload
    context = {
        'categories': categories,
        'products': products,
        'total_revenue': verified_orders.aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_orders': verified_orders.count(),
        'low_stock_items': low_stock,
        'low_stock_count': low_stock.count(),
        'out_of_stock_items': out_of_stock_items,
        'out_of_stock_count': out_of_stock_items.count(),
        'total_users': users.count(),
        # Format chart labels based on the selected timeframe
        'chart_week_labels': [d['period'].strftime(chart_format) if d['period'] else '' for d in chart_data],
        'chart_week_values': [float(d['total']) for d in chart_data],
    }
    
    return render(request, 'admin/dashboard.html', context)


@staff_member_required
def admin_products(request):
    products = Product.objects.all()
    categories = Category.objects.all()

    # Stock alerts
    low_stock = Product.objects.filter(instock__range=(1, 9))
    out_of_stock_items = Product.objects.filter(instock=0)

    return render(request, 'admin/products.html', {
        'products': products,
        'categories': categories,
        'low_stock_items': low_stock,
        'low_stock_count': low_stock.count(),
        'out_of_stock_items': out_of_stock_items,
        'out_of_stock_count': out_of_stock_items.count(),
    })

def admin_couriers(request):
    # 1. Place the line here to filter out soft-deleted couriers
    active_couriers = CourierProfile.objects.filter(is_deleted=False, user__is_active=True)
    
    # Optional: Further filter them, for example, counting who is currently online
    online_count = active_couriers.filter(is_available=True).count()
    
    # 2. Pass it into your context dictionary
    context = {
        'couriers': active_couriers,
        'online_count': online_count
    }
    return render(request, 'admin/admin_couriers.html', context)


@staff_member_required
@require_POST
def edit_product_ajax(request):
    product_id = request.POST.get('product_id')
    name = request.POST.get('name')
    price = request.POST.get('price')
    instock = request.POST.get('instock')
    # Get the Category object by ID from the dropdown
    cat_id = request.POST.get('category')
    # Extract unit_type with 'Piece' as default fallback
    unit_type = request.POST.get('unit_type', 'Piece')
    
    try:
        product = Product.objects.get(id=product_id)
        product.name = name
        product.price = price
        product.instock = instock
        product.unit_type = unit_type
        product.category = get_object_or_404(Category, id=cat_id)
        
        # Handle image if uploaded
        if 'image' in request.FILES:
            product.image = request.FILES['image']
            
        product.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f'{product.name} updated successfully!',
            'new_price': product.price,
            'new_stock': product.instock,
            'new_unit_type': product.unit_type
        })
    except Product.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Product not found'}, status=404)


@staff_member_required
@require_POST
def add_product(request):
    # If using a ProductForm, handle it like this:
    name = request.POST.get('name')
    price = request.POST.get('price')
    instock = request.POST.get('instock')
    category_id = request.POST.get('category') # Grab the category here
    # Extract unit_type with 'Piece' as default fallback
    unit_type = request.POST.get('unit_type', 'Piece')
    image = request.FILES.get('image')

    if name and price and category_id:
        # CRITICAL: Fetch the actual Category object
        category_obj = get_object_or_404(Category, id=category_id)

        new_prod = Product.objects.create(
            name=name, 
            price=price, 
            instock=instock, 
            unit_type=unit_type,
            category=category_obj, # Assign the OBJECT, not the ID string
            image=image
        )
        return JsonResponse({
            'status': 'success', 
            'message': f'{new_prod.name} added to inventory!',
            'unit_type': new_prod.unit_type
        })
    return JsonResponse({'status': 'error', 'message': 'Invalid data'}, status=400)


@staff_member_required
@require_POST
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product_name = product.name
    product.delete()
    return JsonResponse({
        'status': 'success',
        'message': f'{product_name} has been removed.'
    })


# Views for cart home page 
def clear_cart(request): 
    if 'cart' in request.session: 
        del request.session['cart'] 
        request.session.modified = True 
    return redirect('product_list') 


@staff_member_required
@require_POST
def bulk_restock(request):
    for key, value in request.POST.items():
        if key.startswith('stock_'):
            p_id = key.replace('stock_', '')
            Product.objects.filter(id=p_id).update(instock=value)
    return JsonResponse({'success': True})


@staff_member_required
def add_category(request):
    if request.method == "POST":
        name = request.POST.get('cat_name', '').strip()
        if name:
            # Case-insensitive check (covers 'drinks', 'DRINKS', etc.)
            exists = Category.objects.filter(name__iexact=name).exists()

            if exists:
                return JsonResponse({
                    'status': 'exists',
                    'message': f'"{name}" already exists!'
                }, status=400)

            # If it doesn't exist, create it
            category = Category.objects.create(name=name)
            return JsonResponse({
                'status': 'success', 
                'id': category.id, 
                'name': category.name,
                'message': 'Category added successfully!'
            })
    return JsonResponse({'status': 'error', 'message': 'Invalid data'}, status=400)


@staff_member_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    return JsonResponse({'status': 'success'})


@staff_member_required
def admin_customers(request):
    # Fetch all customers and calculate stats
    customers = User.objects.filter(is_staff=False).annotate(
        order_count=Count('order', filter=Q(order__verified=True)), # Use Q for better filtering
        total_spent=Sum('order__amount', filter=Q(order__verified=True))
    ).order_by('-total_spent', '-order_count') # Primary: Cash, Secondary: Frequency
    
    # Ensure total_spent isn't None (happens if no orders exist)
    for c in customers:
        if c.total_spent is None:
            c.total_spent = 0

    return render(request, 'admin/customers.html', {
        'customers': customers,
    })


@staff_member_required
def customer_profile_ajax(request, user_id):
    customer = get_object_or_404(User, id=user_id)
    orders = Order.objects.filter(user=customer).order_by('-created_at')[:10]
    order_data = [{
        'ref': o.ref, 
        'amount': float(o.amount), 
        'date': o.created_at.strftime('%Y-%m-%d')
    } for o in orders]
    
    return JsonResponse({
        'username': customer.username,
        'email': customer.email,
        'joined': customer.date_joined.strftime('%b %Y'),
        'orders': order_data
    })

@login_required
def customer_order_status_api(request, order_id):
    """
    API for the customer page to poll every 5 seconds
    """
    order = get_object_or_404(Order, id=order_id)
    return JsonResponse({
        'status': order.status,
        'cancelled_by': getattr(order, 'cancelled_by', None),
        'courier_name': order.courier.username if order.courier else "Courier",
        'customer_name': order.user.get_full_name() or order.user.username,
        'packing_at': order.packing_at.strftime("%g:%i A") if order.packing_at else None,
        'transit_at': order.transit_at.strftime("%g:%i A") if order.transit_at else None,
        'delivered_at': order.delivered_at.strftime("%g:%i A") if order.delivered_at else None,
    })


@staff_member_required
def admin_orders(request):
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    
    orders = Order.objects.filter(verified=True).order_by('-created_at')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    if search_query:
        orders = orders.filter(ref__icontains=search_query) | orders.filter(user__username__icontains=search_query)
        
    # Calculate the cutoff time (10 minutes ago)
    ten_minutes_ago = timezone.now() - timedelta(minutes=10)
    
    # We add a temporary attribute to each order object
    for o in orders:
        o.is_new = o.created_at >= ten_minutes_ago

    return render(request, 'admin/admin_orders.html', {'orders': orders})


@staff_member_required
def admin_order_count(request):
    count = Order.objects.filter(verified=True).count()
    return JsonResponse({'count': count})


@login_required
def courier_dashboard(request):
    # SECURITY FIX: Block normal customers from accessing this view
    if not hasattr(request.user, 'courier_profile'):
        return redirect('home') # Or return an error page
    
    profile = request.user.courier_profile

    # Base query for location 1
    location_query = models.Q(address__icontains=profile.location_1)
    
    # ONLY add location 2 to the search if it is not empty/None
    if profile.location_2:
        location_query |= models.Q(address__icontains=profile.location_2)

    # Active requests scanning
    relevant_orders = Order.objects.filter(
        status='Accepted', 
        courier__isnull = True, # <== Crucial! This finds unassigned orders
        verified=True
    ).filter(location_query)

    # 1. Fetch all completed (Delivered) and Cancelled orders for this courier
    # Ordered by the most recent ID so new history shows at the top
    order_history = Order.objects.filter(
        courier=request.user,
        status__in=['Delivered', 'Cancelled']
    ).order_by('-id')

    return render(request, 'courier/courier_dashboard.html', {
        'orders': relevant_orders,
        'profile': profile,
        'history': order_history  # Pass history data to the template
    })


def courier_signup(request):
    if request.method == 'POST':
        form = CourierSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Send Welcome Email
            try:
                send_groocy_email(
                    "Ready to Earn? Welcome to the Team! 💰",
                    "emails/welcome_courier.html",
                    {'username': user.username},
                    user.email
                )
            except Exception as e:
                print(f"Signup Email Error: {e}")
                
            return redirect('courier_login')
    else:
        form = CourierSignUpForm()
    return render(request, 'courier/courier_signup.html', {'form': form})


def courier_login(request):
    if request.method == 'POST':
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user is not None:
            # 1. Fixed the typo to match your model's related_name ('courier_profile')
            if hasattr(user, 'courier_profile'):
                # 2. Safety check: Block soft-deleted couriers from accessing the dashboard
                if user.courier_profile.is_deleted:
                    messages.error(request, "This account has been deleted.")
                    return render(request, 'courier/courier_login.html')
                
                login(request, user)
                return redirect('courier_dashboard')
            else:
                messages.error(request, "This account is not registered as a courier.")
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'courier/courier_login.html')


def courier_logout(request):
    if request.user.is_authenticated:
        user_email = request.user.email
        user_name = request.user.username
        
        if user_email:
            try:
                send_groocy_email(
                    f"Rider Log Out Notice 🚴!",
                    "emails/logout_courier.html",
                    {'username': user_name},
                    user_email
                )
            except Exception as e:
                print(f"Logout Email Error: {e}")

        logout(request)
        messages.info(request, "Logged out successfully!")
    return redirect('courier_login')


@login_required
def courier_track_order(request, ref):
    order = get_object_or_404(Order.objects.prefetch_related('items'), ref=ref)
    
    # Backend Timer Fix: Calculate exact remaining time
    remaining_time = 900 # Default 15 mins
    if order.accepted_at:
        time_elapsed = (now() - order.accepted_at).total_seconds()
        remaining_time = max(0, int(900 - time_elapsed))

    return render(request, 'courier/courier_tracking.html', {
        'order': order,
        'remaining_time': remaining_time
    })


@login_required
def accept_order(request, order_id):
    """Assigns the courier to the order."""
    if request.method == "POST":
        # Ensure the user is actually a courier
        if not hasattr(request.user, 'courier_profile'):
            return JsonResponse({"status": "error", "message": "Unauthorized access."}, status=403)
        
        order = get_object_or_404(Order, id=order_id)
        
        # Concurrency check: Ensure no one else took it in the last split second
        if order.courier is None and order.status == 'Accepted':
            order.courier = request.user
            order.accepted_at = timezone.now() #  <-- FIX: Save the exact timestamp here!
            order.save()
            return JsonResponse({"status": "success"})
        else:
            return JsonResponse({"status": "error", "message": "Order already taken or expired"})
            

@login_required
def update_profile_ajax(request):
    if request.method == "POST":
        user = request.user

        # 1. SECURITY: Prevent crash if a normal user triggers this
        if not hasattr(user, 'courier_profile'):
            return JsonResponse({"status": "error", "message": "Access Denied: Not a courier profile."})
        
        profile = user.courier_profile
        
        # Update User details
        new_username = request.POST.get('username')
        new_email = request.POST.get('email')
        
        if new_username:
            user.username = new_username
        if new_email:
            user.email = new_email
        user.save()

        # 2. Update Profile locations safely
        loc1 = request.POST.get('loc1')
        loc2 = request.POST.get('loc2', '') # Default to empty string if not provided

        if loc1:
            profile.location_1 = loc1
        profile.location_2 = loc2

        profile.save()
        
        return JsonResponse({
            "status": "success", 
            "username": user.username,
            "email": user.email,
            "loc1": profile.location_1, 
            "loc2": profile.location_2
        })


def poll_orders(request):
    """Fetches new orders in real-time that are less than 120s old, unassigned, and match the courier's zones."""
    try:
        profile = request.user.courier_profile
    except CourierProfile.DoesNotExist:
        return JsonResponse({'orders': []})
    
    if not profile.is_available:
        return JsonResponse({'orders': []})

    # Find orders created in the last 120 seconds that haven't been picked up
    time_threshold = timezone.now() - timedelta(seconds=120)

    # 1. Start with the required location_1 Zone
    location_filter = Q(address__icontains=profile.location_1)

    # 2. Safely layer location_2 only if the courier configured it
    if profile.location_2:
        location_filter |= Q(address__icontains=profile.location_2)

    # 3. Apply the combined query constraints directly to the database layer #todo: Fetch full objects instead of just values to use model methods/properties if needed
    new_orders = Order.objects.filter(
        location_filter,
        status='Accepted',
        courier__isnull=True,
        created_at__gte=time_threshold
    )#.values('id', 'ref', 'address', 'created_at', 'amount')

    orders_list = []
    for o in new_orders:
        # Calculate time left on the server
        time_elapsed = (timezone.now() - o.created_at).total_seconds()
        time_left = max(0, int(120 - time_elapsed))
        
        orders_list.append({
            'id': o.id,
            'ref': o.ref,
            'address': o.address,
            'amount': o.amount,
            'time_left': time_left  # Send pre-calculated time to JS
        })

    return JsonResponse({'orders': orders_list})     


@login_required
def update_order_stage(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id)
        data = json.loads(request.body)
        new_stage = data.get('stage')
        
        # Map frontend stages to backend timestamps
        if new_stage == 'Packing':
            order.packing_at = timezone.now()
            order.status = 'Packing'
        elif new_stage == 'Delivering': # Match this to your frontend 'data-stage'
            order.transit_at = timezone.now()
            order.status = 'Transit'
        elif new_stage == 'Delivered':
            order.delivered_at = timezone.now()
            order.status = 'Delivered'
            
            # 3. Currency Fix: Assuming shipping_fee is in kobo, convert to Naira
            # Commission calculation
            # Ensure shipping_fee is Decimal or float
            fee = Decimal(str(order.shipping_fee))
            commission = fee * Decimal('0.05') # 5%
            
            courier_profile = order.courier.courier_profile
            courier_profile.balance += commission
            courier_profile.save()

            # Trigger Email
            try:
                send_groocy_email(
                    order.user.email,
                    f"Groocy Order Delivered: {order.ref}",
                    "emails/order_confirmation.html",
                    {
                        'user': order.user,
                        'order': order,
                        'items': order.items.all(),
                        'amount_naira': order.amount
                    }
                )
            except Exception as e:
                print(f"Email error: {e}")

        elif new_stage == 'Cancelled':
            order.status = 'Cancelled'
            order.cancelled_by = 'Courier'  # <--- Track who did it

        order.save()
        return JsonResponse({'success': True, 'stage': order.status})
        

@login_required
def customer_track_order(request, ref):
    order = get_object_or_404(Order, ref=ref)
    
    # Sync timer for customer as well
    remaining_time = 900 
    if order.accepted_at:
        time_elapsed = (now() - order.accepted_at).total_seconds()
        remaining_time = max(0, int(900 - time_elapsed))

    return render(request, 'shop/track_order.html', {
        'order': order,
        'remaining_time': remaining_time
    })


def cancel_order_customer(request, ref):
    order = get_object_or_404(Order, ref=ref)
    
    if request.method == "POST":
        # Check if courier is already in transit
        if order.status == 'In Transit' or order.transit_at is not None:
            penalty = 200
            order.amount += penalty
            # Optionally log this to a 'Penalty' table for accounting
        
        order.status = 'Cancelled'
        order.cancelled_by = 'Customer'  # <--- Track who did it
        order.save()
        
        return JsonResponse({"success": True})

def toggle_status(request):
    if request.method == 'POST':
        profile = request.user.profile
        data = json.loads(request.body)
        profile.is_available = data.get('is_available', False)
        profile.save()
        return JsonResponse({'status': 'success', 'is_available': profile.is_available})


@login_required
def submit_rating(request, ref):
    if request.method == "POST":
        order = get_object_or_404(Order, ref=ref)
        text = request.POST.get('experience')
        DeliveryRating.objects.create(order=order, rating_text=text)
        return JsonResponse({'status': 'ok'})

def get_order_status(request, ref):
    """API endpoint for the tracking page to check for status changes"""
    order = get_object_or_404(Order, ref=ref)
    
    # Helper function to convert UTC to local time and format it like "g:i A"
    def format_local_time(dt):
        if dt:
            # Converts to local time, then formats exactly like the HTML template
            return time_format(timezone.localtime(dt), "g:i A")
        return None
    
    data = {
        'status': order.status,
        'packing_at': timezone.localtime(order.packing_at).strftime('%I:%M %p').lstrip('0') if order.packing_at else None,
        'transit_at': timezone.localtime(order.transit_at).strftime('%I:%M %p').lstrip('0') if order.transit_at else None,
        'delivered_at': timezone.localtime(order.delivered_at).strftime('%I:%M %p').lstrip('0') if order.delivered_at else None,

        # --- ENSURE THESE VALUES ARE SENT ON CANCELLATION ---
        'cancelled_by': getattr(order, 'cancelled_by', None), # Should save either 'Customer' or 'Courier'
        'customer_name': order.user.username if order.user else "Customer",
        'courier_name': order.courier.username if order.courier else None, # Return None on home when no courier is assigned  
    }
    return JsonResponse(data)



