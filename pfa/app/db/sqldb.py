from ..models import (UserDetails, UserPreference)
from .firebase_util import auth, get_user_info

def save_firebase_user_to_local_db(firebase_uid):
    try:
        # Fetch user details from Firebase
        result = get_user_info(id_token=firebase_uid)
        user_record = result.get('users')
        user_record = user_record[0] if user_record else {}
        display_name = user_record.get('displayName')
        print(f"\nUSER RECORD {user_record}\n")

        # Create or update the user in the database
        user, created = UserDetails.objects.get_or_create(uid=user_record.get('localId'),
                                                          defaults={"email": user_record.get('email'),
                                                                    "display_name": display_name,
                                                                    "id_token": firebase_uid})
        if not created:
            return {'msg': 'error', 'is_success': False}
        return user
    except Exception as e:
        # Handle errors (e.g., user not found)
        print(f"Error saving user: {e}")
        return None


def save_user_preference(uid):
    # Get or create the user preference
    user_preference, created = UserPreference.objects.update_or_create(uid=uid)

    user_preference.uid = uid

    user_preference.save()

    return user_preference


def update_user_display_name(uid, new_display_name):
    user = UserDetails.objects.get(uid=uid)
    user.display_name = new_display_name
    user.save()


def get_uid_by_email(email):
    try:
        user = UserDetails.objects.get(email=email)
        return user.uid  # Return the UID of the user
    except Exception as e:
        return None  # Return None if no user is found with the provided email


def get_uid_and_email_by_token(token):
    try:
        # Retrieve the user from the database using the user ID
        user = UserDetails.objects.get(email=token)
        print(user.uid)
        return {'uid': user.uid, 'email': user.email, 'display_name': user.display_name}  # Return the UID and email
    except Exception as e:
        return {'msg': str(e)}  # Return None if no user is found with the provided ID
