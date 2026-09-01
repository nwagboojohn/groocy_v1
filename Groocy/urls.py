from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Student Side
    path('', views.landing, name='landing'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('home/', views.home, name='home'),
    path('orders/', views.orders_view, name='orders'),
    path('order/<str:ref>/', views.order_detail, name='order_detail'),
    path('profile/', views.profile_view, name='profile'),
    path('update-address/', views.update_address, name='update_address'),
    path('update-profile/', views.update_profile, name='update_profile'),

    # Reset Password Using OTP (One Time Password)
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/verify/', views.password_reset_otp_verify, name='password_reset_otp_verify'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    
    # Admin Suite
    path('groocy-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('groocy-admin/products/', views.admin_products, name='admin_products'), 
    path('groocy-admin/customers/', views.admin_customers, name='admin_customers'),
    path('groocy-admin/couriers/', views.admin_couriers, name='admin_couriers'),
    path('groocy-admin/orders/', views.admin_orders, name='admin_orders'), 
    path('groocy-admin/order-count/', views.admin_order_count, name='admin_order_count'),

    # Admin Logic (AJAX/POST)
    path('groocy-admin/add-product/', views.add_product, name='add_product'),
    path('groocy-admin/edit-product/', views.edit_product_ajax, name='edit_product_ajax'),
    path('groocy-admin/delete-product/<int:pk>/', views.delete_product, name='delete_product'),
    path('edit-product/bulk-restock/', views.bulk_restock, name='bulk_restock'),
    path('groocy-admin/add-category/', views.add_category, name='add_category'),
    path('groocy-admin/delete-category/<int:pk>/', views.delete_category, name='delete_category'),
    path('groocy-admin/customer-profile/<int:user_id>/', views.customer_profile_ajax, name='customer_profile_ajax'),

    # To receive data
    path('sync-cart/', views.sync_cart, name='sync_cart'),

    # Couriers URLS 
    path('courier/signup/', views.courier_signup, name='courier_signup'),
    path('courier/login/', views.courier_login, name='courier_login'),
    path('courier/logout/', views.courier_logout, name='courier_logout'),
    path('courier/dashboard/', views.courier_dashboard, name='courier_dashboard'),
    # url to pull order
    path('courier/api/poll-orders/', views.poll_orders, name='poll_orders'),
    # url for toggle online/offline
    path('courier/api/toggle-status/', views.toggle_status, name='toggle_status'),
    # Courier Tracking url 
    path('courier/track/<str:ref>/', views.courier_track_order, name='courier_track_order'),
    # Courier Cancel Order Url 
    path('courier/api/accept-order/<int:order_id>/', views.accept_order, name='accept_order'),
    # Courier Actions
    path('courier/api/update-stage/<int:order_id>/', views.update_order_stage, name='update_order_stage'),
    path('courier/update-location/', views.update_profile_ajax, name='update_profile_ajax'),
    path('courier/account/delete/', views.delete_courier_account, name='delete_courier_account'),
    
    # Payment Verification
    path('verify-payment/<str:ref>/', views.verify_payment, name='verify_payment'),
    # Url for Successful payment 
    path('payment-success/', views.payment_success_view, name='payment_success'),
    # URL for failed payment 
    path('payment-error/', views.payment_error_view, name='payment_error'),
    # 2. The actual Tracking Page (The user lands here)
    path('track-order/<str:ref>/', views.customer_track_order, name='track_order'),
    # Customer order status api
    path('api/order-status/<int:order_id>/', views.customer_order_status_api, name='customer_order_status_api'),
    # Customer cancel order
    path('api/cancel-order-customer/<str:ref>/', views.cancel_order_customer, name='cancel_order_customer'),
    # Order Tracking Polling (For the JavaScript setInterval)
    path('api/order-status/<str:ref>/', views.get_order_status, name='get_order_status'),
    # Feedback
    path('submit-rating/<str:ref>/', views.submit_rating, name='submit_rating'),
    
]