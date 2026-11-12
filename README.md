# Campus Bites: Python + Firestore

## 1. Create the database (free)
1. Go to console.firebase.google.com > Add project.
2. Build > Firestore Database > Create database > Production mode.
3. Project settings > Service accounts > Generate new private key. This downloads a .json file. Keep it secret.

## 2. Test on your computer
    pip install -r requirements.txt
    set GOOGLE_APPLICATION_CREDENTIALS=path\to\key.json      (Mac/Linux: export ...)
    set ADMIN_PASSWORD=choose-a-password
    python app.py
Open http://localhost:5000 (customers) and http://localhost:5000/admin (you).

## 3. Get the public link (Render.com, free)
1. Upload this folder to a GitHub repository.
2. Render > New > Web Service > connect the repo.
3. Build command: pip install -r requirements.txt
   Start command: gunicorn app:app
4. Environment variables:
   - ADMIN_PASSWORD = your password
   - FIREBASE_KEY_JSON = the full contents of the key .json file
5. Deploy. Your link will look like https://campus-bites.onrender.com
   Share that link with students. You manage orders at <link>/admin.

Free Render apps sleep after inactivity, so the first visit can take about 30 seconds.
