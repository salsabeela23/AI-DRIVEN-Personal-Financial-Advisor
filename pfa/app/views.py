import json
import logging
from gc import get_threshold
import os
import yfinance as yf
from django.http import JsonResponse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from .db.firebase_util import firebase_signin, firebase_signup, add_income_to_firestore, get_user_info, \
    get_user_id_from_email, get_income_data, delete_income_from_firestore, add_expense_to_firestore, get_expense_data, \
    delete_expense_from_firestore, send_overspending_alert
from .db.sqldb import save_firebase_user_to_local_db, get_uid_and_email_by_token
from .models import UserProfile, Recommendation
from .prediction.recommender import AdvancedInvestmentRecommender
import pfa.settings as settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pfa.settings')

# Initialize logging
logger = logging.getLogger(__name__)

from django.shortcuts import render, redirect

print (os.getcwd())

def getStarted(request):
    if request.user.is_authenticated:
        return redirect('dashboard')  # Redirect to the dashboard if the user is authenticated
    return render(request, 'welcome.html')  # Render the welcome page if the user is not authenticated


def signup_view(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]
        display_name = request.POST["display_name"]
        result = firebase_signup(email=email, password=password, display_name=display_name)
        if "error" in result:
            # Render the sign-up page with the error message
            return render(request, "signup.html", {"error": result["error"]})

        # Automatically log in the user after successful sign-up
        # Sign in the user to fetch the token
        login_result = firebase_signup(email=email, password=password, display_name=display_name)
        if "error" in login_result:
            # If login fails after sign-up, redirect to log in with a message
            return redirect("signin")

        # Save user token in session
        request.session["user"] = {
            "idToken": login_result.get('email'),
            "email": email
        }
        save_firebase_user_to_local_db(result.get('idToken'))

        return redirect("dashboard")

    return render(request, "signup.html")


logger.setLevel(logging.INFO)
handler = logging.FileHandler('signin_activity.log')  # Log file where logs will be stored
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def signin_view(request):
    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']
        remember_me = request.POST.get('remember_me', False)  # Check if 'Remember Me' is selected

        try:
            # Log the signin attempt
            logger.info(f"Signin attempt for email: {email}")

            # Try to log the user in with the provided credentials
            result = firebase_signin(email, password)
            print(result)
            save_firebase_user_to_local_db(result.get('idToken'))

            # Check if "Remember Me" was selected
            if remember_me:
                # Set session expiry to a longer period (e.g., 30 days)
                request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days in seconds
                logger.info(f"User {email} selected 'Remember Me' option.")
            else:
                # Session will expire when the user closes the browser
                request.session.set_expiry(0)
                logger.info(f"User {email} did not select 'Remember Me'.")

            # Store the user's ID token in session
            request.session['user'] = result.get('email')
            request.session['is_authenticated'] = True  # Set is_authenticated to True
            logger.info(f"User {email} logged in successfully.")

            # Debugging: Check if session is properly set
            logger.info(f"Session after login: {request.session.items()}")
            print(request.session)

            # Check if the user is authenticated before redirecting
            if request.session.get('is_authenticated', True):
                logger.info("User authenticated. Redirecting to dashboard...")
                return redirect(
                    f'/dashboard/?uid={result.get('localId')}&email={result.get('email')}&display_name={result.get('displayName')}')
            else:
                logger.error("User is not authenticated, cannot redirect to dashboard.")
                return render(request, 'signin.html', {'error': 'Authentication failed'})

        except Exception as e:
            # Log the error
            logger.error(f"Signin attempt failed for email {email}. Error: {str(e)}")

            # Handle any login errors (e.g., wrong credentials)
            return render(request, 'signin.html', {'error': str(e)})

    return render(request, 'signin.html')


# Dashboard
def dashboard(request):
    # Extract user parameters from the query string
    resp = get_uid_and_email_by_token(token=request.session.get('user'))
    print(f"DASHBOARD RESP {resp.get('uid')}")
    user_uid = resp.get('uid')
    user_email = resp.get("email")
    user_display_name = resp.get("display_name", "Guest")

    incomes = get_income_data(user_uid)
    expenses = get_expense_data(user_uid)
    print(f"INCOMES {incomes}")

    total_amount = sum(float(income['amount']) for income in incomes)
    total_expense = sum(float(expense['amount']) for expense in expenses)

    total_amount_after_expense = total_amount - total_expense

    if not request.session.get("user"):
        return redirect("signin")

    # Pass the user details to the dashboard template
    context = {
        "uid": user_uid,
        "email": user_email,
        "display_name": user_display_name,
        "avatar_name": user_display_name.capitalize()[0:1],
        "total_amount": total_amount,
        "total_expenses": total_expense,
        "total_amount_after_expense": total_amount_after_expense,
        "incomes": incomes,
        "expenses": expenses
    }

    return render(request, 'dashboard/dashboard.html', context)


# Dashboard
def dashboardHome(request):
    # Extract user parameters from the query string
    user_uid = request.GET.get("uid")
    user_email = request.GET.get("email")
    user_display_name = request.GET.get("display_name", "Guest")

    incomes = get_income_data(user_uid)
    print(f"INCOMES {incomes}")

    # Pass the user details to the dashboard template
    context = {
        "uid": user_uid,
        "email": user_email,
        "display_name": user_display_name,
        "incomes": incomes
    }
    return render(request, 'dashboard/home.html', context)


# Dashboard
def dashboardProfile(request):
    # Extract user parameters from the query string
    user_uid = request.GET.get("uid")
    user_email = request.GET.get("email")
    user_display_name = request.GET.get("display_name", "Guest")

    # Pass the user details to the dashboard template
    context = {
        "uid": user_uid,
        "email": user_email,
        "display_name": user_display_name,
    }
    return render(request, 'dashboard/profile.html', context)


def dashboardTracker(request):
    # Extract user parameters from the query string
    user_uid = request.GET.get("uid")
    user_email = request.GET.get("email")
    user_display_name = request.GET.get("display_name", "Guest")
    incomes = get_income_data(user_uid)
    print(f"INCOMES {incomes}")

    # Pass the user details to the dashboard template
    context = {
        "uid": user_uid,
        "email": user_email,
        "display_name": user_display_name,
        "incomes": incomes
    }

    return render(request, 'dashboard/tracker.html', context)


def dashboardCalculator(request):
    # Extract user parameters from the query string
    user_uid = request.GET.get("uid")
    user_email = request.GET.get("email")
    user_display_name = request.GET.get("display_name", "Guest")

    # Pass the user details to the dashboard template
    context = {
        "uid": user_uid,
        "email": user_email,
        "display_name": user_display_name,
    }
    return render(request, 'dashboard/calculator.html', context)


def dashboardLogout(request):
    # Extract user parameters from the query string
    user_uid = request.GET.get("uid")
    user_email = request.GET.get("email")
    user_display_name = request.GET.get("display_name", "Guest")

    # Pass the user details to the dashboard template
    context = {
        "uid": user_uid,
        "email": user_email,
        "display_name": user_display_name,
    }
    return render(request, 'dashboard/logout.html', context)


def logout_view(request):
    try:
        request.session.flush()  # This will delete the session and logout the user

        # Optionally, you can show a message indicating successful logout
        messages.success(request, "You have been logged out successfully.")

        return redirect('logged_out')  # Redirecting to the signin page (adjust if necessary)
    except Exception as e:
        logger.error(f"Logout attempt failed. Error: {str(e)}")

        messages.error(request, "An error occurred during logout. Please try again.")
        return redirect('home')  # Adjust the redirect as necessary


def logged_out_view(request):
    return render(request, 'dashboard/logged_out.html')


@csrf_exempt
def add_expense(request):
    if request.method == 'POST':
        try:
            # Check if data is JSON or form-encoded
            if request.content_type == 'application/json':
                data = json.loads(request.body)  
            else:
                data = request.POST  

            # Example of accessing specific fields
            income_data = {
                "amount": int(data.get("amount")),
                "type": data.get("type"),
                "comment": data.get("comment"),
                "date": data.get("date"),
            }

            # Pass data to the add_income_to_firestore function
            print(request.session.get('user'))
            user = request.session.get('user')  # Get user from session, handle case if user is not found
            resp = get_uid_and_email_by_token(user)  # Retrieve UID and email using the token
            if resp.get('uid'):
                response, msg = add_expense_to_firestore(income_data, resp.get('uid'))
                if response:
                # Return a success response

                    return redirect(
                        f'/dashboard/?uid={resp.get('uid')}&email={resp.get('email')}&display_name={resp.get('displayName')}')
                else:
                    return JsonResponse({'message':msg})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Invalid HTTP method. Use POST."}, status=405)


@csrf_exempt  # Required for CSRF token handling with POST requests
def delete_expense(request):
    if request.method == 'POST':
        # Get the income ID from the POST data
        expense_id = request.POST.get('expense_id')
        print(f"EXPENSE ID{expense_id}")
        if not expense_id:
            return HttpResponseBadRequest("Expense ID not provided.")

        try:
            # Delete the document from Firestore
            resp = get_uid_and_email_by_token(token=request.session.get('user'))
            delete_expense_from_firestore(uid=resp.get('uid'), expense_id=expense_id)
            if resp.get('uid'):
                return redirect(
                    f'/dashboard/?uid={resp.get('uid')}&email={resp.get('email')}&display_name={resp.get('displayName')}')  # Replace with your desired redirect
        except Exception as e:
            return HttpResponseBadRequest(f"Error deleting income: {e}")
    else:
        return HttpResponseBadRequest("Invalid request method.")


@csrf_exempt
def add_income(request):
    if request.method == 'POST':
        try:
            # Check if data is JSON or form-encoded
            if request.content_type == 'application/json':
                data = json.loads(request.body)  # Parse JSON data
            else:
                data = request.POST  # Use form-encoded data

            # Example of accessing specific fields
            income_data = {
                "amount": int(data.get("amount")),
                "type": data.get("type"),
                "taxable": data.get("tax"),
                "date": data.get("date"),
            }

            # Pass data to the add_income_to_firestore function
            print(request.session.get('user'))
            user = request.session.get('user')  # Get user from session, handle case if user is not found
            resp = get_uid_and_email_by_token(user)  # Retrieve UID and email using the token
            if resp.get('uid'):
                response = add_income_to_firestore(income_data, resp.get('uid'))

            # Return a success response
            return redirect(
                f'/dashboard/?uid={resp.get('uid')}&email={resp.get('email')}&display_name={resp.get('displayName')}')
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Invalid HTTP method. Use POST."}, status=405)


@csrf_exempt  # Required for CSRF token handling with POST requests
def delete_income(request):
    if request.method == 'POST':
        # Get the income ID from the POST data
        income_id = request.POST.get('income_id')
        print(f"INCOME ID{income_id}")
        if not income_id:
            return HttpResponseBadRequest("Income ID not provided.")

        try:
            # Delete the document from Firestore
            resp = get_uid_and_email_by_token(token=request.session.get('user'))
            delete_income_from_firestore(uid=resp.get('uid'), income_id=income_id)
            if resp.get('uid'):
                return redirect(
                    f'/dashboard/?uid={resp.get('uid')}&email={resp.get('email')}&display_name={resp.get('displayName')}')  # Replace with your desired redirect
        except Exception as e:
            return HttpResponseBadRequest(f"Error deleting income: {e}")
    else:
        return HttpResponseBadRequest("Invalid request method.")

@csrf_exempt
def trigger_alert_email(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('data_username')
        email = data.get('data_email')
        print(f'EMAIL RECEPIENT : {email}')
        send_overspending_alert(username=username, to_email=email)
    return JsonResponse({"message": "Alert email sent success."})



def investment_advice(request):
    recommendations = []
    confidence = None
    advice = None

    if request.method == 'POST':
        # Input from user
        total_savings = float(request.POST['total_savings'])
        risk_tolerance = request.POST['risk_tolerance']
        time_horizon = int(request.POST['time_horizon'])
        age = int(request.POST['age'])  # You can add more fields like 'age', 'income', etc.
        income = float(request.POST['income'])
        investment_experience = int(request.POST['investment_experience'])
        financial_knowledge = float(request.POST['financial_knowledge'])

        # Initialize the recommender
        recommender = AdvancedInvestmentRecommender()
        print("ADVICE LOGIC TRIGGERED")
        # Get recommendations
        recommendation_data = recommender.recommend(
            total_savings, risk_tolerance, time_horizon, age, income,
            investment_experience, financial_knowledge
        )

        # Prepare recommendations and detailed advice
        recommendations = [{"type": recommendation_data['recommendation'],
                            "allocation": "50%",
                            "confidence": f"{recommendation_data['confidence']:.2f}%"}]

        advice = recommendation_data['advice']  # Personalized investment advice

        # Save recommendation to the database (Optional, if needed)
        profile = UserProfile.objects.create(
            name="User", email=settings.EMAIL_HOST_USER,  # Replace with actual data
            total_savings=total_savings, risk_tolerance=risk_tolerance,
            time_horizon=time_horizon, age=age, income=income,
            investment_experience=investment_experience,
            financial_knowledge=financial_knowledge
        )

        for rec in recommendations:
            Recommendation.objects.create(
                user=profile,
                investment_type=rec["type"],
                allocation_percentage=rec["allocation"]
            )

    # Return the same page with recommendations and additional investment advice
    return render(request, 'advisor/home.html', {
        "recommendations": recommendations,
        "advice": advice,
        "confidence": confidence
    })


def get_stock_data(request):
    nifty = yf.Ticker("^NSEI").history(period="1d", interval="1m")
    sensex = yf.Ticker("^BSESN").history(period="1d", interval="1m")

    latest_nifty = nifty.iloc[-1]["Close"]
    latest_sensex = sensex.iloc[-1]["Close"]

    data = {
        "nifty": latest_nifty,
        "sensex": latest_sensex
    }
    return JsonResponse(data)
