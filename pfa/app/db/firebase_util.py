import datetime
import os
import uuid
from pathlib import Path

import pyrebase
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

import firebase_admin
from firebase_admin import credentials, messaging
import requests
from django.contrib import messages
from django.core.mail import send_mail

from firebase_admin import credentials, firestore

from ..models import UserDetails
import pfa.settings as appsettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

FIREBASE_SERVICE_ACCOUNT_CRED_PATH = f"{os.getcwd()}\\serviceAccountKey.json"

# Firebase configuration
firebase_config = {
    "apiKey": "AIzaSyDlJxhV9LKU8sbme6endJQhg14ei2CzpZU",
    "authDomain": "personalfinancialadvisor-b9905.firebaseapp.com",
    "projectId": "personalfinancialadvisor-b9905",
    "storageBucket": "personalfinancialadvisor-b9905.firebasestorage.app",
    "messagingSenderId": "177766897264",
    "appId": "1:177766897264:web:1c0430fd7424a80a4f46b5",
    "databaseURL": "https://personalfinancialadvisor-b9905-default-rtdb.asia-southeast1.firebasedatabase.app/",
    "measurementId": "G-4Z4GBL0JLY",
    "serviceAccount": FIREBASE_SERVICE_ACCOUNT_CRED_PATH
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
pyrebase_db = firebase.database()

# Initialize Firebase Admin SDK using the service account credentials
cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_CRED_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()


def firebase_signup(email, password, display_name):
    try:
        user = auth.create_user_with_email_and_password(email, password)
        # data to save
        data = {
            "name": user.get('displayName'),
            "email_id": user.get('email')
        }
        auth.update_profile(id_token=user.get('idToken'), display_name=display_name)
        result = pyrebase_db.child("users").push(data, user.get('localId'))
        return user
    except Exception as e:
        return {"error": str(e)}


def firebase_signin(email, password):
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        return user
    except Exception as e:
        return {"error": str(e)}


def check_if_authenticated(id_token: str):
    print(id_token)
    if id_token:
        try:
            # Verify the token
            user = auth.get_account_info(id_token)
            return True  # User is authenticated
        except Exception as e:
            return False  # Token is invalid or expired
    else:
        return False  # No token found, user is not authenticated


# Adding data to Firestore
def add_income_to_firestore(income_data, uid):
    doc_id = str(uuid.uuid4())
    income_data['id'] = doc_id
    ref = db.collection("users").document(uid).collection("income").document(doc_id)
    if ref.get().exists:
        ref.update(income_data)
    else:
        ref.set(income_data)
    return


def add_expense_to_firestore(expense_data, uid):
    can_add, msg = can_add_expense(uid,expense_data)
    if can_add:
        doc_id = str(uuid.uuid4())
        expense_data['id'] = doc_id
        ref = db.collection("users").document(uid).collection("expense").document(doc_id)
        if ref.get().exists:
            ref.update(expense_data)
            return True, msg
        else:
            ref.set(expense_data)
        return True, msg
    else:
        return False, msg


def delete_expense_from_firestore(uid: str, expense_id: str):
    """
    Deletes an expense document from Firestore.

    :param expense_id: ID of the expense document to delete.
    """
    ref = db.collection("users").document(uid).collection("expense").document(expense_id)
    if ref.get().exists:
        ref.delete()
        return True
    return False  # Expense not found


def get_expenses_from_firestore(uid: str):
    """
    Fetches all expenses from Firestore, ordered by timestamp (latest first).

    :return: List of expenses.
    """
    expenses_ref = db.collection("users").document(uid).collection("expense").order_by(
        "timestamp", direction=firebase.Query.DESCENDING
    ).stream()

    return [{"id": doc.id, **doc.to_dict()} for doc in expenses_ref]


def calculate_total_spent(uid):
    """
    Calculates the total amount spent from all expenses.

    :return: Total spent amount.
    """
    expenses = get_expenses_from_firestore(uid)
    return sum(expense.get("amount", 0) for expense in expenses)


def set_threshold_to_firestore(uid, threshold_amount):
    """
    Sets or updates the spending threshold for a user in Firestore.

    :param uid: Unique user ID.
    :param threshold_amount: Maximum spending limit set by the user.
    """
    ref = db.collection("users").document(uid).collection("settings").document("threshold")
    ref.set({"amount": threshold_amount}, merge=True)  # Merge to avoid overwriting other settings


def get_threshold_from_firestore(uid):
    """
    Retrieves the spending threshold for a user from Firestore.

    :param uid: Unique user ID.
    :return: Threshold amount if set, otherwise None.
    """
    ref = db.collection("users").document(uid).collection("settings").document("threshold")
    doc = ref.get()

    if doc.exists:
        return doc.to_dict().get("amount", None)  # Return threshold value if exists
    return None


def get_uid_by_email(email):
    try:
        user = UserDetails.objects.get(email=email)
        return user.uid  # Return the UID of the user
    except Exception as e:
        return None  # Return None if no user is found with the provided email


def delete_income_from_firestore(uid, income_id):
    """
    Deletes an income document from Firestore using its ID.

    Args:
        income_id (str): The ID of the income document to delete.

    Returns:
        bool: True if the document was deleted successfully, False otherwise.
    """
    try:
        doc_ref = db.collection('users').document(uid).collection('income').document(income_id)
        if doc_ref.get().exists:
            doc_ref.delete()
            return True
        else:
            print(f"Document with ID {income_id} does not exist.")
            return False
    except Exception as e:
        print(f"Error deleting income: {e}")
        return False


def get_user_info(id_token):
    resp = auth.get_account_info(id_token=id_token)
    print(f"USER INFO {resp}")
    return resp


def get_user_id_from_email(email):
    try:
        # Fetch the user record by email
        user = auth.get_user_by_email(email)
        return user.uid  # Return the user ID (uid)
    except Exception as e:
        print(f"Error getting user ID: {e}")
        return None


def get_user_from_token(id_token):
    try:
        # Verify the ID token and decode it
        decoded_token = auth.verify_id_token(id_token)

        # Retrieve UID and email from the decoded token
        uid = decoded_token['uid']
        email = decoded_token['email']

        # Return UID and email
        return {'uid': uid, 'email': email}

    except Exception as e:
        # Other errors (e.g., token expired, network issues)
        raise ValueError(f"Error decoding ID token: {str(e)}") from e


def get_income_data(uid: str):
    # Reference to the collection (replace with your actual Firestore collection name)
    income_ref = db.collection('users').document(uid).collection("income")

    # Fetch all documents in the 'income' collection
    income_docs = income_ref.stream()

    print(income_docs)
    # Prepare list of income data
    income_data = []
    for doc in income_docs:
        income_data.append(doc.to_dict())

    return income_data


def get_expense_data(uid: str):
    # Reference to the collection (replace with your actual Firestore collection name)
    income_ref = db.collection('users').document(uid).collection("expense")

    # Fetch all documents in the 'income' collection
    income_docs = income_ref.stream()

    print(income_docs)
    # Prepare list of income data
    expense_data = []
    for doc in income_docs:
        expense_data.append(doc.to_dict())

    return expense_data


# def send_email(username,_to: str, subject: str = 'Hello from PFA Admin',
#                message: str = 'This is a test email sent from PFA - Personal Financial Advisor Web App.'):
#     recipient_list = [_to]

#     try:
#         # Send email using send_mail function
#         send_mail(subject, message, appsettings.EMAIL_HOST_USER, recipient_list)
#         send_overspending_alert(username=username, to_email=_to)
#         return {'success': True}
#     except Exception as e:
#         print("Error: Exception occurred: " + str(e))
#         return {'success': False, 'error': str(e)}
    


def send_overspending_alert(username, to_email, budget_exceeded_category=None, 
                           recent_transactions=None, budget_exceed_amount=None):
    """
    Sends an overspending alert email to the user.

    Args:
        user: The user object.
        reason: The reason for the overspending alert.
        budget_exceeded_category: The category where the budget was exceeded.
        recent_transactions: A list of recent transactions.
        budget_exceed_amount: The amount by which the budget was exceeded.
    """

    context = {
        'user_name': username,
        'reason': "Overspending Alert",
        'budget_exceeded_category': budget_exceeded_category,
        'recent_transactions': recent_transactions,
        'budget_exceed_amount': budget_exceed_amount,
        'app_name': "Personal Financial Advisor",
        'account_url': f'http://127.0.0.1:8000/dashboard/', 
        'budgeting_tips_url': f'BUDGET TIP', 
        'spending_categories_url': f'',  
        'support_email': appsettings.EMAIL_HOST_USER,
        'support_phone': appsettings.SUPPORT_PHONE_NUMBER,
    }


    subject = 'Overspending Alert!'
    html_message = render_to_string('overspending_alert.html', context)

    send_mail(
        subject,
        '',  # Empty message body, as we're using HTML
        appsettings.EMAIL_HOST_USER,
        [to_email],
        html_message=html_message,
    )

def can_add_expense(uid,expense_data):
    expense_amount = expense_data['amount']
    incomes = get_income_data(uid)
    total_income = sum(float(income['amount']) for income in incomes)

    if total_income == 0:
        return False, f"Your income data is {total_income}. You can't add expense, at the moment."
    elif expense_amount>= total_income:
        return False, "Expense amount is greater that your current income"
    else:
        return True, "Ok ready to add your expense"