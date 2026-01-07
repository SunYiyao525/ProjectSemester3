import RPi.GPIO as GPIO
import time
import smtplib
from email.message import EmailMessage
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from datetime import datetime, timedelta

# ===================== 1. Hardware Configuration (FC-28 Sensor as per instructor's code) =====================
# GPIO Setup (D0 pin connected to GPIO4, BCM encoding)
channel = 4
GPIO.setmode(GPIO.BCM)
GPIO.setup(channel, GPIO.IN)

# Global Variables: Store historical moisture data (for prediction model)
history_data = []
# Historical dataset file path (reuse 7-day dataset, append real-time data later)
DATA_FILE = "nanjing_soil_data_7days.csv"
# Prediction window: Use previous 3 time points to predict next one
SEQ_LENGTH = 3

# ===================== 2. Email Configuration (SMTP logic as per instructor's code) =====================
# Replace with your sender email, APP password, recipient email
FROM_EMAIL = "your_sender_email@outlook.com"  # e.g., Outlook/QQ email
FROM_EMAIL_PASS = "your_app_password"  # 16-digit APP password created earlier
TO_EMAIL = "your_recipient_email@xxx.com"  # Email to receive notifications
# SMTP server configuration (Outlook as example, replace for other emails)
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587

def send_email(real_time_moisture, prediction_result):
    """Send email with real-time moisture + prediction results"""
    msg = EmailMessage()
    msg['From'] = FROM_EMAIL
    msg['To'] = TO_EMAIL
    msg['Subject'] = "Plant Soil Moisture Alert & Prediction"
    
    # Email content (include real-time status and predictions)
    if GPIO.input(channel):
        status = "ALERT: Soil is DRY! Please water your plant ASAP!"
    else:
        status = "Normal: Soil has enough moisture."
    
    body = f"""
    {status}
    Real-time Soil Moisture: {real_time_moisture:.2f}%
    Prediction for Next 1 Day: {prediction_result['day1']:.2f}%
    Prediction for Next 2 Days: {prediction_result['day2']:.2f}%
    Prediction for Next 3 Days: {prediction_result['day3']:.2f}%
    """
    msg.set_content(body)
    
    # Connect to SMTP server and send email
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Enable TLS encryption
        server.login(FROM_EMAIL, FROM_EMAIL_PASS)
        server.send_message(msg)
        print("Email sent successfully!")
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

# ===================== 3. Prediction Model (Adapt to real-time data update) =====================
def load_and_update_data(real_time_moisture):
    """Load historical data, append real-time data, return processed dataset"""
    # Load previous 7-day historical data
    df = pd.read_csv(DATA_FILE)
    df['date'] = pd.to_datetime(df['date'])
    
    # Generate current timestamp and append real-time moisture data
    # (Fill temperature/rainfall with latest values, add sensors in actual use)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    last_row = df.iloc[-1]  # Get environmental parameters from last row
    new_data = pd.DataFrame({
        'date': [current_time],
        'moisture': [real_time_moisture],
        'temperature': [last_row['temperature']],
        'rainfall': [last_row['rainfall']],
        'light': [last_row['light']],
        'irrigation': [0]  # No irrigation by default
    })
    
    # Append new data to historical dataset and save
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    return df

def build_and_predict_model(df):
    """Train LSTM model with updated dataset, predict moisture for next 3 days"""
    # Data normalization
    scaler = MinMaxScaler(feature_range=(0, 1))
    moisture_scaled = scaler.fit_transform(df[['moisture']])
    
    # Build time sequences (use previous SEQ_LENGTH data to predict next one)
    def create_sequences(data, seq_len):
        X, y = [], []
        for i in range(len(data) - seq_len):
            X.append(data[i:i+seq_len])
            y.append(data[i+seq_len])
        return np.array(X), np.array(y)
    
    X, y = create_sequences(moisture_scaled, SEQ_LENGTH)
    # Adapt LSTM input format (samples, time steps, features)
    X = X.reshape(X.shape[0], X.shape[1], 1)
    
    # Build lightweight LSTM model (adapt to real-time small dataset)
    model = Sequential([
        LSTM(32, activation='relu', input_shape=(SEQ_LENGTH, 1)),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    model.fit(X, y, epochs=5, batch_size=4, verbose=0)  # Fast training
    
    # Predict next 3 days: recursive prediction
    predictions = []
    last_seq = moisture_scaled[-SEQ_LENGTH:]  # Use last SEQ_LENGTH data as initial input
    for _ in range(3):
        next_pred_scaled = model.predict(last_seq.reshape(1, SEQ_LENGTH, 1), verbose=0)
        predictions.append(scaler.inverse_transform(next_pred_scaled)[0][0])
        # Update input sequence (remove oldest, add new prediction)
        last_seq = np.append(last_seq[1:], next_pred_scaled, axis=0)
    
    return {
        'day1': predictions[0],
        'day2': predictions[1],
        'day3': predictions[2]
    }

# ===================== 4. Sensor Callback Function (Detect moisture changes) =====================
def moisture_callback(channel):
    """Triggered on moisture change: read moisture → update model → send email"""
    # Simulate reading analog value (A0 pin of FC-28, replace with ADC module in actual use)
    # Map threshold to percentage (dry: 30-35%, wet: 38-45%)
    if GPIO.input(channel):
        # Dry state: moisture ~30-35%
        real_time_moisture = np.random.uniform(30.0, 35.0)
    else:
        # Wet state: moisture ~38-45%
        real_time_moisture = np.random.uniform(38.0, 45.0)
    
    print(f"\nDetected Moisture Change! Current Humidity: {real_time_moisture:.2f}%")
    
    # Load and update historical data
    df_updated = load_and_update_data(real_time_moisture)
    
    # Predict moisture for next 3 days
    prediction_result = build_and_predict_model(df_updated)
    print(f"Prediction Result: Next 3 Days → {prediction_result}")
    
    # Send email (force send when dry, optional send when wet)
    if GPIO.input(channel):
        send_email(real_time_moisture, prediction_result)
    else:
        # Send status report every 12 hours in wet state (optional)
        current_hour = datetime.now().hour
        if current_hour in [8, 20]:  # Send at 8 AM and 8 PM
            send_email(real_time_moisture, prediction_result)

# ===================== 5. Main Program (Start sensor monitoring + loop) =====================
if __name__ == "__main__":
    try:
        # Register callback for sensor state change (detect high/low level change)
        GPIO.add_event_detect(channel, GPIO.BOTH, bouncetime=3000)  # 3s debounce
        GPIO.add_event_callback(channel, moisture_callback)
        
        print("Soil Moisture Monitoring System Started!")
        print("Waiting for Moisture Changes... (Press Ctrl+C to Exit)")
        
        # Infinite loop to keep program running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting Program...")
    finally:
        # Clean up GPIO resources
        GPIO.cleanup()
