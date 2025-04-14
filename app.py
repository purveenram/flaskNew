from flask import Flask, request, jsonify
import face_recognition
import requests
import io
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

NHOST_GRAPHQL_URL = "https://jpglhtcjffhmukchuxjj.hasura.ap-south-1.nhost.run/v1/graphql"
NHOST_STORAGE_URL = "https://jpglhtcjffhmukchuxjj.storage.ap-south-1.nhost.run/v1/files"
NHOST_ADMIN_SECRET = "hGgA8;r;CNg+N(T'%50OHNT7'4Zx(A2F"

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
    print("1")
    response = requests.post(
        NHOST_GRAPHQL_URL,
        json={"query": query},
        headers=headers,
    )
    print("2")
    if response.status_code != 200:
        raise Exception(f"GraphQL error: {response.status_code} - {response.text}")

    data = response.json()
    print(data)
    profiles = data['data']['Profiles']
    print(profiles)
    base_url = "https://jpglhtcjffhmukchuxjj.storage.ap-south-1.nhost.run/v1/files/"
    face_urls = {
    user["user_id"]: base_url + user["face_url"]
    for user in profiles
    if user.get("face_url")
    }
    print(face_urls)
    return face_urls

def fetch_image_from_nhost(face_url):
    response = requests.get(face_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch image: {face_url}")
    return face_recognition.load_image_file(io.BytesIO(response.content))

def match_faces(uploaded_encoding, profiles, threshold=0.6):
    for user_id, face_url in profiles.items():
        try:
            profile_image = fetch_image_from_nhost(face_url)
            encodings = face_recognition.face_encodings(profile_image)
            if not encodings:
                continue
            profile_encoding = encodings[0]
            distance = face_recognition.face_distance([profile_encoding], uploaded_encoding)[0]
            if distance < threshold:
                return user_id
        except Exception as e:
            continue
    return None

def send_notification_to_user(user_id, image_url):
    # You can implement a notification system here
    print(f"Notification sent to user {user_id} for image match: {image_url}")

@app.route("/api/face-match", methods=["POST"])

def face_match():
    data = request.json
    image_url = data.get("image_url")

    if not image_url:
        return jsonify({"error": "Missing imageUrl"}), 400

    try:

        uploaded_image = fetch_image_from_nhost(image_url)

        uploaded_encodings = face_recognition.face_encodings(uploaded_image)

        if not uploaded_encodings:
            return jsonify({"error": "No face found in uploaded image"}), 400
        uploaded_encoding = uploaded_encodings[0]

        profiles = get_all_profile_face_urls()
        print(profiles)
        matched_user = match_faces(uploaded_encoding, profiles)
 
        if matched_user:
            send_notification_to_user(matched_user, image_url)
            return jsonify({"matchFound": True, "matchedUser": matched_user})
        else:
            return jsonify({"matchFound": False})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
