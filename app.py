from flask import Flask, request, jsonify
from flask_cors import CORS
from deepface import DeepFace
import requests
import io

app = Flask(__name__)
CORS(app)

NHOST_GRAPHQL_URL = "https://jpglhtcjffhmukchuxjj.hasura.ap-south-1.nhost.run/v1/graphql"
NHOST_STORAGE_URL = "https://jpglhtcjffhmukchuxjj.storage.ap-south-1.nhost.run/v1/files"
NHOST_ADMIN_SECRET = "hGgA8;r;CNg+N(T'%50OHNT7'4Zx(A2F"

# Fetch all profile face image URLs
def get_all_profile_face_urls():
    query = """
    query {
        Profiles {
            user_id,
            face_url
        }
    }
    """
    headers = {
        "Content-Type": "application/json",
        "x-hasura-admin-secret": NHOST_ADMIN_SECRET
    }

    response = requests.post(
        NHOST_GRAPHQL_URL,
        json={"query": query},
        headers=headers,
    )

    if response.status_code != 200:
        raise Exception(f"GraphQL error: {response.status_code} - {response.text}")

    data = response.json()
    profiles = data['data']['Profiles']
    base_url = NHOST_STORAGE_URL + "/"

    face_urls = {
        user["user_id"]: base_url + user["face_url"]
        for user in profiles
        if user.get("face_url")
    }
    return face_urls

# Fetch image from a URL as BytesIO (for DeepFace)
def fetch_image_from_nhost(face_url):
    response = requests.get(face_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch image: {face_url}")
    return io.BytesIO(response.content)

# Match faces using DeepFace (Facenet model)
def match_faces_deepface(uploaded_image, profiles, model_name='Facenet', threshold=0.6):
    for user_id, face_url in profiles.items():
        try:
            profile_image = fetch_image_from_nhost(face_url)

            result = DeepFace.verify(
                img1_path=uploaded_image,
                img2_path=profile_image,
                model_name=model_name,
                enforce_detection=False
            )

            if result["verified"] and result["distance"] < threshold:
                return user_id
        except Exception as e:
            print(f"Error comparing with {user_id}: {e}")
            continue
    return None

def send_notification_to_user(user_id, image_url):
    print(f"Notification sent to user {user_id} for image match: {image_url}")

@app.route("/api/face-match", methods=["POST"])
def face_match():
    data = request.json
    image_url = data.get("image_url")

    if not image_url:
        return jsonify({"error": "Missing imageUrl"}), 400

    try:
        uploaded_image = fetch_image_from_nhost(image_url)
        profiles = get_all_profile_face_urls()
        matched_user = match_faces_deepface(uploaded_image, profiles)

        if matched_user:
            send_notification_to_user(matched_user, image_url)
            return jsonify({"matchFound": True, "matchedUser": matched_user})
        else:
            return jsonify({"matchFound": False})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

