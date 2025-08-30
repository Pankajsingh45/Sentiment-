from flask import Flask, render_template, request, send_file
from textblob import TextBlob
import emoji
import sqlite3
from io import BytesIO
from datetime import datetime

app = Flask(__name__)

# Emoji scores
emoji_sentiment_score = {
    "😊": 1.0, "😄": 0.9, "😁": 0.9, "😂": 0.8,
    "😍": 1.0, "😢": -1.0, "😭": -0.9, "😞": -0.8,
    "😡": -1.0, "😠": -0.9, "😐": 0.0, "👍": 0.7,
    "👎": -0.7, "❤": 1.0, "💔": -1.0, "😃": 0.9,
    "😉": 0.7, "🤔": 0.0, "😤": -0.6, "😎": 0.8
}

# Emoji moods
emoji_mood_map = {
    "😊": "Happy", "😄": "Happy", "😁": "Happy", "😂": "Funny",
    "😍": "Romantic", "❤": "Romantic", "💔": "Heartbroken",
    "😢": "Sad", "😭": "Sad", "😞": "Sad",
    "😡": "Angry", "😠": "Angry", "😐": "Neutral",
    "🤔": "Confused", "😎": "Confident", "👍": "Supportive",
    "👎": "Disappointed", "😤": "Frustrated"
}

def init_db():
    conn = sqlite3.connect('sentiment.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        input TEXT,
        sentiment TEXT,
        polarity REAL,
        emoji_sent REAL,
        final_score REAL,
        timestamp TEXT)''')
    conn.commit()
    conn.close()

def extract_emojis(text):
    return [ch for ch in text if ch in emoji.EMOJI_DATA]

def emoji_score(emojis):
    total, count = 0.0, 0
    for em in emojis:
        if em in emoji_sentiment_score:
            total += emoji_sentiment_score[em]
            count += 1
    return total / count if count > 0 else 0.0

def detect_emotion_from_emoji(emojis):
    for em in emojis:
        if em in emoji_mood_map:
            return emoji_mood_map[em]
    return "Neutral"

def store_to_db(data):
    conn = sqlite3.connect('sentiment.db')
    c = conn.cursor()
    c.execute('INSERT INTO results (input, sentiment, polarity, emoji_sent, final_score, timestamp) VALUES (?, ?, ?, ?, ?, ?)', data)
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = request.form['text']
        blob = TextBlob(text)
        text_score = blob.sentiment.polarity

        emojis = extract_emojis(text)
        emo_score = emoji_score(emojis)
        emotion_label = detect_emotion_from_emoji(emojis)
        final_score = (text_score + emo_score) / 2

        if final_score > 0.1:
            sentiment = f"Positive ({emotion_label})"
            emoji_out = "😊"
        elif final_score < -0.1:
            sentiment = f"Negative ({emotion_label})"
            emoji_out = "😞"
        else:
            sentiment = f"Neutral ({emotion_label})"
            emoji_out = "😐"

        data = (
            text, sentiment, round(text_score, 2),
            round(emo_score, 2), round(final_score, 2),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        store_to_db(data)

        return render_template('result.html',
            text=text, sentiment=sentiment, emoji_out=emoji_out,
            polarity=round(text_score, 2), emo_score=round(emo_score, 2),
            final_score=round(final_score, 2)
        )

    return render_template('index.html')

@app.route('/history')
def history():
    conn = sqlite3.connect('sentiment.db')
    c = conn.cursor()
    c.execute("SELECT input, sentiment, polarity, emoji_sent, final_score, timestamp FROM results ORDER BY id DESC")
    records = c.fetchall()
    conn.close()
    return render_template('history.html', records=records)

@app.route('/download')
def download_csv():
    conn = sqlite3.connect('sentiment.db')
    c = conn.cursor()
    c.execute("SELECT * FROM results")
    rows = c.fetchall()
    conn.close()

    output = "ID,Input,Sentiment,Polarity,Emoji Score,Final Score,Timestamp\n"
    for row in rows:
        output += ",".join(map(str, row)) + "\n"

    mem = BytesIO()
    mem.write(output.encode('utf-8'))
    mem.seek(0)

    return send_file(
        mem,
        mimetype='text/csv',
        download_name='sentiment_data.csv',
        as_attachment=True
    )

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
