# 🎹 LIED

## Your music, organized. Your technique, mastered.


### What's LIED?

LIED is a simple but powerful **web app for pianists**. Whether you're a student or a pro, it helps you keep your repertoire tidy, analyze your sheet music, and level up your technique with custom exercises — all without needing internet.

It's **free**, **open source**, and runs completely **offline**. So your data stays yours, wherever you practice.


### Why you'll love it

* 🎵 **Keep your music library neat and ready** — no more messy notes or lost scores.
* 🕵️‍♂️ **Understand your music deeply** — automatic analysis of your sheet music.
* 🏃‍♂️ **Practice smarter, not harder** — personalized practice plans that fit your level and schedule.
* 💪 **Get exercises that actually help** — focused on the tricky parts of your pieces.
* ✍️ **Jot down your thoughts** — keep notes and reminders for every piece.
* 🎯 **See your progress** — colorful maps show how far you've come.
* 🎧 **Play along with MIDI files** — practice with backing tracks right in the app.


### Tech behind the scenes

Built with modern web tech so it's smooth and fast:

* Frontend: HTML, Tailwind CSS, Tone.js, MIDI.js, Chart.js
* Backend: Django, SQLite, music21


### Complete installation guide

1. **Clone the repository**:
   ```bash
   git clone git@github.com:YGA-13/LIED.git
   cd LIED
   ```

2. **Set up Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   ```

3. **Prepare database**:
   ```bash
   python manage.py migrate
   python manage.py makemigrations
   ```

4. **Run development server**:
   ```bash
   python manage.py runserver
   ```

Access at: `http://localhost:8000`


### Want to help?

LIED is open source — all contributions are welcome! Have ideas or fixes? Open an issue or send a pull request.


### Get in touch

Yago Garcia Araujo — [yagogarciaraujo@gmail.com](mailto:yagogarciaaraujo@gmail.com)

---

**Make your practice count. Get organized. Nail your technique. LIED is here for you!** 🎹🔥

